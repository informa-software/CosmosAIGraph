"""
Rule Sets Router

FastAPI router for compliance rule set management endpoints.
Provides REST API for CRUD operations on rule sets and rule assignments.

Author: Aleksey Savateyev, Microsoft, 2025
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Query, Path

from src.services.rule_set_service import RuleSetService
from src.models.rule_set_models import (
    RuleSet,
    RuleSetCreate,
    RuleSetUpdate,
    RuleSetListResponse,
    RuleSetWithRuleCount,
    AddRulesToSetRequest,
    RemoveRulesFromSetRequest,
    CloneRuleSetRequest
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/rule_sets",
    tags=["rule-sets"]
)


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_rule_set_service():
    """Initialize and return rule set service."""
    service = RuleSetService()
    await service.initialize()
    try:
        yield service
    finally:
        await service.close()


# ============================================================================
# Rule Set CRUD Endpoints
# ============================================================================

@router.post("", response_model=RuleSet, status_code=201)
async def create_rule_set(rule_set_data: RuleSetCreate):
    """
    Create a new rule set.

    - **name**: Unique name for the rule set
    - **description**: Detailed description (optional)
    - **suggested_contract_types**: Array of contract types this set is designed for (optional)
    - **rule_ids**: Initial rules to include (optional)
    - **is_active**: Whether the rule set is active (default: true)
    """
    service = RuleSetService()
    await service.initialize()

    try:
        rule_set = await service.create_rule_set(rule_set_data, created_by="api_user")
        return rule_set
    except Exception as e:
        logger.error(f"Error creating rule set: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create rule set: {str(e)}")
    finally:
        await service.close()


@router.get("", response_model=RuleSetListResponse)
async def list_rule_sets(
    include_inactive: bool = Query(False, description="Include inactive rule sets")
):
    """
    List all rule sets.

    - **include_inactive**: Set to true to include inactive rule sets
    """
    service = RuleSetService()
    await service.initialize()

    try:
        response = await service.list_rule_sets(include_inactive)
        return response
    except Exception as e:
        logger.error(f"Error listing rule sets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list rule sets: {str(e)}")
    finally:
        await service.close()


@router.get("/with-counts", response_model=List[RuleSetWithRuleCount])
async def list_rule_sets_with_counts(
    include_inactive: bool = Query(False, description="Include inactive rule sets")
):
    """
    List all rule sets with rule counts.

    Returns rule sets with an additional `rule_count` field showing
    the number of rules in each set.
    """
    service = RuleSetService()
    await service.initialize()

    try:
        rule_sets = await service.get_rule_sets_with_counts(include_inactive)
        return rule_sets
    except Exception as e:
        logger.error(f"Error listing rule sets with counts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list rule sets: {str(e)}")
    finally:
        await service.close()


@router.get("/{rule_set_id}", response_model=RuleSet)
async def get_rule_set(
    rule_set_id: str = Path(..., description="Rule set ID")
):
    """
    Get a specific rule set by ID.

    - **rule_set_id**: The unique identifier for the rule set
    """
    service = RuleSetService()
    await service.initialize()

    try:
        rule_set = await service.get_rule_set(rule_set_id)
        if not rule_set:
            raise HTTPException(status_code=404, detail=f"Rule set {rule_set_id} not found")
        return rule_set
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rule set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve rule set: {str(e)}")
    finally:
        await service.close()


@router.put("/{rule_set_id}", response_model=RuleSet)
async def update_rule_set(
    rule_set_id: str,
    updates: RuleSetUpdate
):
    """
    Update an existing rule set.

    Only provided fields will be updated. Fields not included in the request
    will remain unchanged.

    - **name**: New name for the rule set
    - **description**: New description
    - **suggested_contract_types**: Updated contract types
    - **is_active**: Active status
    """
    service = RuleSetService()
    await service.initialize()

    try:
        updated = await service.update_rule_set(rule_set_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Rule set {rule_set_id} not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update rule set: {str(e)}")
    finally:
        await service.close()


@router.delete("/{rule_set_id}", status_code=204)
async def delete_rule_set(
    rule_set_id: str = Path(..., description="Rule set ID")
):
    """
    Delete a rule set.

    This will permanently delete the rule set. Rules themselves are not deleted,
    only the rule set container.

    - **rule_set_id**: The unique identifier for the rule set to delete
    """
    service = RuleSetService()
    await service.initialize()

    try:
        success = await service.delete_rule_set(rule_set_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Rule set {rule_set_id} not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete rule set: {str(e)}")
    finally:
        await service.close()


# ============================================================================
# Rule Assignment Endpoints
# ============================================================================

@router.get("/{rule_set_id}/rules", response_model=List[str])
async def get_rules_in_set(
    rule_set_id: str = Path(..., description="Rule set ID")
):
    """
    Get all rule IDs in a rule set.

    Returns an array of rule IDs that are members of this set.
    """
    service = RuleSetService()
    await service.initialize()

    try:
        rule_ids = await service.get_rules_in_set(rule_set_id)
        return rule_ids
    except Exception as e:
        logger.error(f"Error getting rules in set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")
    finally:
        await service.close()


@router.post("/{rule_set_id}/rules", response_model=RuleSet)
async def add_rules_to_set(
    rule_set_id: str,
    request: AddRulesToSetRequest
):
    """
    Add rules to a rule set.

    Adds the specified rules to the rule set. Duplicates are automatically ignored.

    - **rule_ids**: Array of rule IDs to add to the set
    """
    service = RuleSetService()
    await service.initialize()

    try:
        updated = await service.add_rules_to_set(rule_set_id, request.rule_ids)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Rule set {rule_set_id} not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding rules to set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add rules: {str(e)}")
    finally:
        await service.close()


@router.delete("/{rule_set_id}/rules", response_model=RuleSet)
async def remove_rules_from_set(
    rule_set_id: str,
    request: RemoveRulesFromSetRequest
):
    """
    Remove rules from a rule set.

    Removes the specified rules from the rule set. Non-existent rule IDs are ignored.

    - **rule_ids**: Array of rule IDs to remove from the set
    """
    service = RuleSetService()
    await service.initialize()

    try:
        updated = await service.remove_rules_from_set(rule_set_id, request.rule_ids)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Rule set {rule_set_id} not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing rules from set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove rules: {str(e)}")
    finally:
        await service.close()


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.post("/{rule_set_id}/clone", response_model=RuleSet, status_code=201)
async def clone_rule_set(
    rule_set_id: str,
    request: CloneRuleSetRequest
):
    """
    Clone an existing rule set.

    Creates a copy of the rule set with a new name. Optionally includes
    all the rules from the original set.

    - **new_name**: Name for the cloned rule set
    - **clone_rules**: Whether to copy the rule IDs (default: true)
    """
    service = RuleSetService()
    await service.initialize()

    try:
        cloned = await service.clone_rule_set(
            rule_set_id,
            request.new_name,
            request.clone_rules,
            created_by="api_user"
        )
        if not cloned:
            raise HTTPException(status_code=404, detail=f"Rule set {rule_set_id} not found")
        return cloned
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning rule set {rule_set_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clone rule set: {str(e)}")
    finally:
        await service.close()
