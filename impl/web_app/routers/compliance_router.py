"""
Compliance Router

FastAPI router for compliance rules and evaluation endpoints.
Provides REST API for managing rules, evaluating contracts, and viewing results.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
from src.services.compliance_rules_service import ComplianceRulesService
from src.services.evaluation_job_service import EvaluationJobService
from src.services.compliance_evaluation_service import ComplianceEvaluationService
from src.services.rule_set_service import RuleSetService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/compliance",
    tags=["compliance"]
)


# ============================================================================
# Pydantic Models for Request/Response Validation
# ============================================================================

class RuleCreate(BaseModel):
    """Request model for creating a compliance rule."""
    name: str = Field(..., min_length=1, description="Short descriptive name")
    description: str = Field(..., min_length=1, description="Natural language rule description")
    severity: str = Field(..., pattern="^(critical|high|medium|low)$", description="Rule severity")
    category: str = Field(..., min_length=1, description="Rule category")
    active: bool = Field(default=True, description="Whether rule is active")
    created_by: str = Field(default="system", description="User who created the rule")
    rule_set_ids: List[str] = Field(default_factory=list, description="List of rule set IDs this rule belongs to")


class RuleUpdate(BaseModel):
    """Request model for updating a compliance rule."""
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    severity: Optional[str] = Field(None, pattern="^(critical|high|medium|low)$")
    category: Optional[str] = Field(None, min_length=1)
    active: Optional[bool] = None
    rule_set_ids: Optional[List[str]] = None


class RuleResponse(BaseModel):
    """Response model for a compliance rule."""
    id: str
    name: str
    description: str
    severity: str
    category: str
    active: bool
    rule_set_ids: List[str] = Field(default_factory=list)
    created_date: str
    updated_date: str
    created_by: str


class EvaluateContractRequest(BaseModel):
    """Request model for evaluating a contract."""
    contract_id: str = Field(..., description="Contract ID")
    contract_text: Optional[str] = Field(None, description="Full contract text (optional, fetched from Contracts collection if not provided)")
    rule_set_id: Optional[str] = Field(None, description="Rule set ID to use (optional, overrides rule_ids if provided)")
    rule_ids: Optional[List[str]] = Field(None, description="Specific rule IDs (optional, defaults to all active)")
    async_mode: bool = Field(default=True, description="Run as async job")


class EvaluateRuleRequest(BaseModel):
    """Request model for evaluating a rule against contracts."""
    contract_ids: Optional[List[str]] = Field(None, description="Specific contract IDs (optional, defaults to all)")
    async_mode: bool = Field(default=True, description="Run as async job")


class BatchEvaluateRequest(BaseModel):
    """Request model for batch evaluation."""
    contract_ids: List[str] = Field(..., description="List of contract IDs")
    rule_ids: List[str] = Field(..., description="List of rule IDs")
    async_mode: bool = Field(default=True, description="Run as async job")


class CategoryCreate(BaseModel):
    """Request model for creating a category."""
    name: str = Field(..., pattern="^[a-z0-9_-]+$", description="Internal category name")
    display_name: str = Field(..., min_length=1, description="Human-readable name")
    description: Optional[str] = Field(None, description="Category description")


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_services():
    """
    Initialize and return all required services.
    This is a dependency that will be injected into endpoints.
    """
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()
    cosmos_service.set_db(ConfigService.graph_source_db())

    ai_service = AiService()
    await ai_service.initialize()

    rules_service = ComplianceRulesService(cosmos_service)
    job_service = EvaluationJobService(cosmos_service)
    evaluation_service = ComplianceEvaluationService(
        cosmos_service,
        rules_service,
        job_service,
        ai_service
    )

    rule_set_service = RuleSetService()
    await rule_set_service.initialize()

    return {
        "rules": rules_service,
        "evaluation": evaluation_service,
        "jobs": job_service,
        "rule_sets": rule_set_service
    }


async def sync_rule_set_membership(
    rule_id: str,
    new_rule_set_ids: List[str],
    old_rule_set_ids: List[str],
    rule_set_service: RuleSetService
):
    """
    Synchronize rule set membership when a rule's rule_set_ids change.

    Updates the rule_ids arrays in rule set documents to maintain bidirectional consistency.

    Args:
        rule_id: The rule ID
        new_rule_set_ids: New list of rule set IDs
        old_rule_set_ids: Previous list of rule set IDs
        rule_set_service: RuleSetService instance
    """
    # Find rule sets to add to (in new but not in old)
    rule_sets_to_add = set(new_rule_set_ids) - set(old_rule_set_ids)

    # Find rule sets to remove from (in old but not in new)
    rule_sets_to_remove = set(old_rule_set_ids) - set(new_rule_set_ids)

    # Add rule to new rule sets
    for rule_set_id in rule_sets_to_add:
        try:
            await rule_set_service.add_rules_to_set(rule_set_id, [rule_id])
        except Exception as e:
            logger.warning(f"Failed to add rule {rule_id} to rule set {rule_set_id}: {e}")

    # Remove rule from old rule sets
    for rule_set_id in rule_sets_to_remove:
        try:
            await rule_set_service.remove_rules_from_set(rule_set_id, [rule_id])
        except Exception as e:
            logger.warning(f"Failed to remove rule {rule_id} from rule set {rule_set_id}: {e}")


# ============================================================================
# Rules Endpoints
# ============================================================================

@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(
    active_only: bool = Query(default=True, description="Filter active rules only"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    services: dict = Depends(get_services)
):
    """
    List all compliance rules with optional filtering.

    - **active_only**: If true, return only active rules
    - **category**: Filter by specific category
    - **severity**: Filter by severity level (critical, high, medium, low)
    """
    try:
        rules = await services["rules"].list_rules(
            active_only=active_only,
            category=category,
            severity=severity
        )
        return [rule.to_dict() for rule in rules]

    except Exception as e:
        logger.error(f"Failed to list rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    services: dict = Depends(get_services)
):
    """Get a specific compliance rule by ID."""
    try:
        rule = await services["rules"].get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

        return rule.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", response_model=RuleResponse, status_code=201)
async def create_rule(
    rule_data: RuleCreate,
    services: dict = Depends(get_services)
):
    """
    Create a new compliance rule.

    - **name**: Short descriptive name
    - **description**: Natural language rule description
    - **severity**: critical, high, medium, or low
    - **category**: Rule category
    - **active**: Whether rule should be evaluated (default: true)
    - **rule_set_ids**: Optional list of rule set IDs this rule belongs to
    """
    try:
        rule = await services["rules"].create_rule(rule_data.model_dump())

        # Sync rule set membership if rule_set_ids provided
        if rule.rule_set_ids:
            await sync_rule_set_membership(
                rule.id,
                rule.rule_set_ids,
                [],  # No old rule sets for new rule
                services["rule_sets"]
            )

        return rule.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", response_model=dict)
async def update_rule(
    rule_id: str,
    updates: RuleUpdate,
    services: dict = Depends(get_services)
):
    """
    Update a compliance rule.

    Returns the updated rule and count of stale evaluations that need re-running.
    """
    try:
        # Filter out None values
        update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

        if not update_dict:
            raise HTTPException(status_code=400, detail="No updates provided")

        # Get old rule for rule set comparison
        old_rule = await services["rules"].get_rule(rule_id)
        if not old_rule:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

        # Update the rule
        rule = await services["rules"].update_rule(rule_id, update_dict)

        # Sync rule set membership if rule_set_ids changed
        if "rule_set_ids" in update_dict:
            await sync_rule_set_membership(
                rule.id,
                rule.rule_set_ids,
                old_rule.rule_set_ids,
                services["rule_sets"]
            )

        stale_count = await services["rules"].get_stale_count_for_rule(rule_id)

        return {
            "rule": rule.to_dict(),
            "stale_count": stale_count,
            "message": f"Rule updated. {stale_count} contracts have stale evaluations." if stale_count > 0 else "Rule updated successfully."
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    services: dict = Depends(get_services)
):
    """
    Delete a compliance rule.

    Note: Associated evaluation results are preserved for historical tracking.
    The rule will be removed from all rule sets it belongs to.
    """
    try:
        # Get rule to find its rule sets before deletion
        rule = await services["rules"].get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")

        # Remove rule from all rule sets it belongs to
        if rule.rule_set_ids:
            await sync_rule_set_membership(
                rule.id,
                [],  # No new rule sets
                rule.rule_set_ids,  # Remove from all current rule sets
                services["rule_sets"]
            )

        # Delete the rule
        success = await services["rules"].delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete rule")

        return {
            "success": True,
            "message": "Rule deleted. Associated results archived."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Evaluation Endpoints
# ============================================================================

@router.post("/evaluate/contract/{contract_id}")
async def evaluate_contract(
    contract_id: str,
    request: EvaluateContractRequest,
    services: dict = Depends(get_services)
):
    """
    Evaluate a contract against compliance rules.

    - **contract_id**: Contract ID (from path)
    - **contract_text**: Optional full contract text (if not provided, fetched from Contracts collection)
    - **rule_ids**: Optional list of specific rule IDs (defaults to all active rules)
    - **async_mode**: Run as async job (default: true)

    Returns job ID if async, or results if synchronous.
    """
    try:
        # Get contract text - either from request or fetch from Contracts collection
        contract_text = request.contract_text
        if not contract_text:
            # Fetch from Contracts collection
            cosmos_service = services["evaluation"].cosmos_service
            cosmos_service.set_container("contracts")

            # Partition key for contracts collection is "contracts"
            contract_doc = await cosmos_service.point_read(contract_id, "contracts")
            if not contract_doc:
                raise HTTPException(status_code=404, detail=f"Contract not found: {contract_id}")

            # Get contract_text from contract document
            contract_text = contract_doc.get("contract_text")
            if not contract_text:
                raise HTTPException(status_code=400, detail=f"Contract {contract_id} does not have contract_text field")

        # Get rules to evaluate
        # Priority: rule_set_id > rule_ids > all active rules
        if request.rule_set_id:
            # Get rules from the specified rule set
            rules = await services["rules"].get_rules_by_rule_set(request.rule_set_id, active_only=True)
            if not rules:
                raise HTTPException(status_code=404, detail=f"No active rules found in rule set {request.rule_set_id}")
        elif request.rule_ids:
            # Get specific rules by ID
            rules = []
            for rule_id in request.rule_ids:
                rule = await services["rules"].get_rule(rule_id)
                if rule:
                    rules.append(rule)
        else:
            # Default to all active rules
            rules = None

        # Evaluate
        result = await services["evaluation"].evaluate_contract(
            contract_id=contract_id,
            contract_text=contract_text,
            rules=rules,
            create_job=request.async_mode
        )

        if request.async_mode:
            return {
                "job_id": result["job_id"],
                "status": "pending",
                "message": f"Evaluation started for contract {contract_id}"
            }
        else:
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evaluate contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/rule/{rule_id}")
async def evaluate_rule(
    rule_id: str,
    request: EvaluateRuleRequest,
    services: dict = Depends(get_services)
):
    """
    Evaluate a rule against multiple contracts.

    - **rule_id**: Rule ID (from path)
    - **contract_ids**: Optional list of contract IDs (defaults to all contracts)
    - **async_mode**: Run as async job (default: true)
    """
    try:
        result = await services["evaluation"].evaluate_rule_against_contracts(
            rule_id=rule_id,
            contract_ids=request.contract_ids
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to evaluate rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reevaluate/stale/{rule_id}")
async def reevaluate_stale(
    rule_id: str,
    async_mode: bool = Query(default=True, description="Run as async job"),
    services: dict = Depends(get_services)
):
    """
    Re-evaluate contracts with stale results for a specific rule.

    Stale results are those evaluated before the rule was last updated.
    """
    try:
        # Get stale count
        stale_count = await services["rules"].get_stale_count_for_rule(rule_id)

        if stale_count == 0:
            return {
                "job_id": None,
                "message": "No stale evaluations found for this rule"
            }

        # TODO: Implement re-evaluation logic
        # For now, just return the count
        return {
            "job_id": None,
            "stale_count": stale_count,
            "message": f"Re-evaluation of {stale_count} contracts not yet implemented"
        }

    except Exception as e:
        logger.error(f"Failed to reevaluate stale for rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate/batch")
async def batch_evaluate(
    request: BatchEvaluateRequest,
    services: dict = Depends(get_services)
):
    """
    Evaluate multiple contracts against multiple rules.

    - **contract_ids**: List of contract IDs
    - **rule_ids**: List of rule IDs
    - **async_mode**: Run as async job (default: true)
    """
    try:
        # TODO: Implement batch evaluation
        return {
            "job_id": None,
            "message": "Batch evaluation not yet implemented"
        }

    except Exception as e:
        logger.error(f"Failed to batch evaluate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Results Endpoints
# ============================================================================

@router.get("/results")
async def get_all_results(
    result_filter: Optional[str] = Query(default=None, pattern="^(pass|fail|partial|not_applicable)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    services: dict = Depends(get_services)
):
    """
    Get all compliance evaluation results across all contracts and rules.

    - **result_filter**: Filter by result type (pass, fail, partial, not_applicable)
    - **limit**: Maximum number of results to return (1-1000, default: 100)

    Returns list of all compliance results.
    """
    try:
        results = await services["evaluation"].get_all_results(
            result_filter=result_filter,
            limit=limit
        )
        return results

    except Exception as e:
        logger.error(f"Failed to get all results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/contract/{contract_id}")
async def get_contract_results(
    contract_id: str,
    include_stale: bool = Query(default=False, description="Include stale results"),
    services: dict = Depends(get_services)
):
    """
    Get all compliance evaluation results for a contract.

    Returns results and summary statistics (pass/fail/partial counts).
    """
    try:
        result = await services["evaluation"].get_results_for_contract(contract_id)
        return result

    except Exception as e:
        logger.error(f"Failed to get results for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/rule/{rule_id}")
async def get_rule_results(
    rule_id: str,
    result_filter: Optional[str] = Query(default=None, pattern="^(pass|fail|partial|not_applicable)$"),
    include_stale: bool = Query(default=False, description="Include stale results"),
    services: dict = Depends(get_services)
):
    """
    Get all compliance evaluation results for a rule.

    - **result_filter**: Filter by result type (pass, fail, partial, not_applicable)
    - **include_stale**: Include results evaluated before rule was updated

    Returns results and summary statistics.
    """
    try:
        result = await services["evaluation"].get_results_for_rule(
            rule_id=rule_id,
            result_filter=result_filter
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get results for rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_compliance_summary(
    services: dict = Depends(get_services)
):
    """
    Get compliance dashboard summary.

    Returns:
    - Total rules (active and inactive)
    - Total contracts evaluated
    - Overall pass rate
    - Per-rule statistics (pass/fail counts, pass rate, stale count)
    """
    try:
        summary = await services["evaluation"].get_compliance_summary()
        return summary

    except Exception as e:
        logger.error(f"Failed to get compliance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stale-rules")
async def get_stale_rules(
    services: dict = Depends(get_services)
):
    """
    Get all rules that have stale evaluation results.

    Returns list of rules with stale counts for dashboard notification.
    """
    try:
        stale_rules = await services["rules"].get_rules_with_stale_results()
        return {
            "stale_rules": stale_rules,
            "total_stale_rules": len(stale_rules)
        }

    except Exception as e:
        logger.error(f"Failed to get stale rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Job Tracking Endpoints
# ============================================================================

@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    services: dict = Depends(get_services)
):
    """Get status and details of an evaluation job."""
    try:
        job = await services["jobs"].get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        return job.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    services: dict = Depends(get_services)
):
    """Cancel a running evaluation job."""
    try:
        job = await services["jobs"].cancel_job(job_id)
        return {
            "success": True,
            "message": "Job cancelled",
            "job": job.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(default=None, pattern="^(pending|in_progress|completed|failed|cancelled)$"),
    job_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    services: dict = Depends(get_services)
):
    """
    List evaluation jobs with optional filtering.

    - **status**: Filter by job status
    - **job_type**: Filter by job type
    - **limit**: Maximum number of jobs to return (1-100)
    """
    try:
        jobs = await services["jobs"].list_jobs(
            status=status,
            job_type=job_type,
            limit=limit
        )
        return {
            "jobs": [job.to_dict() for job in jobs],
            "total": len(jobs)
        }

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Category Endpoints
# ============================================================================

@router.get("/categories")
async def get_categories(
    services: dict = Depends(get_services)
):
    """
    Get all compliance rule categories with rule counts.

    Returns both predefined and user-defined categories.
    """
    try:
        categories = await services["rules"].get_all_categories()
        return {
            "categories": categories,
            "total": len(categories)
        }

    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories", status_code=201)
async def create_category(
    category_data: CategoryCreate,
    services: dict = Depends(get_services)
):
    """
    Validate and create a custom category.

    - **name**: Internal category name (lowercase, underscores/hyphens only)
    - **display_name**: Human-readable name
    - **description**: Optional description

    Note: Categories are derived from rules, not stored separately.
    This endpoint validates the category name format.
    """
    try:
        category = await services["rules"].create_category(
            name=category_data.name,
            display_name=category_data.display_name,
            description=category_data.description
        )
        return category.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        raise HTTPException(status_code=500, detail=str(e))
