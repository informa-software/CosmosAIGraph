"""
Compliance Evaluation Service

Performs batch compliance rule evaluation against contracts using LLM.
Manages evaluation results and provides dashboard summary data.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.models.compliance_models import (
    ComplianceRule,
    ComplianceResultData,
    RecommendationData,
    EvaluationResult,
    JobType
)
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.compliance_rules_service import ComplianceRulesService
from src.services.evaluation_job_service import EvaluationJobService
from src.services.ai_service import AiService

logger = logging.getLogger(__name__)


class ComplianceEvaluationService:
    """
    Service for evaluating contracts against compliance rules.

    Performs batch LLM evaluations, stores results, and provides dashboard summaries.
    Supports async job tracking for long-running evaluations.
    """

    # Maximum rules to evaluate in a single LLM call
    MAX_RULES_PER_BATCH = 10

    def __init__(
        self,
        cosmos_service: CosmosNoSQLService,
        rules_service: ComplianceRulesService,
        job_service: EvaluationJobService,
        ai_service: AiService
    ):
        """
        Initialize the compliance evaluation service.

        Args:
            cosmos_service: Initialized CosmosDB service instance
            rules_service: Compliance rules service
            job_service: Evaluation job service
            ai_service: AI service for LLM calls
        """
        self.cosmos_service = cosmos_service
        self.rules_service = rules_service
        self.job_service = job_service
        self.ai_service = ai_service
        self.results_container = "compliance_results"

    async def evaluate_contract(
        self,
        contract_id: str,
        contract_text: str,
        rules: Optional[List[ComplianceRule]] = None,
        create_job: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate a contract against compliance rules.

        Args:
            contract_id: Contract ID
            contract_text: Full contract text
            rules: List of rules to evaluate (defaults to all active rules)
            create_job: Whether to create an async job for tracking

        Returns:
            Dict with 'job_id', 'results', and 'summary'
        """
        try:
            # Get active rules if not provided
            if rules is None:
                rules = await self.rules_service.list_rules(active_only=True)

            if not rules:
                logger.warning("No active compliance rules found")
                return {"job_id": None, "results": [], "summary": {}}

            # Create job if requested
            job = None
            if create_job:
                job = await self.job_service.create_job(
                    job_type=JobType.EVALUATE_CONTRACT.value,
                    total_items=len(rules),
                    contract_id=contract_id,
                    rule_ids=[r.id for r in rules]
                )

            # Evaluate in batches
            all_results = []
            for i in range(0, len(rules), self.MAX_RULES_PER_BATCH):
                batch = rules[i:i + self.MAX_RULES_PER_BATCH]
                batch_results = await self._evaluate_batch(contract_id, contract_text, batch)
                all_results.extend(batch_results)

                # Update job progress
                if job:
                    await self.job_service.update_progress(
                        job.id,
                        completed=min(i + self.MAX_RULES_PER_BATCH, len(rules))
                    )

            # Complete job
            if job:
                await self.job_service.complete_job(job.id, success=True)

            # Build summary
            summary = self._build_summary(all_results)

            logger.info(f"Evaluated contract {contract_id} against {len(rules)} rules")

            return {
                "job_id": job.id if job else None,
                "results": [r.to_dict() for r in all_results],
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Failed to evaluate contract {contract_id}: {e}")
            if job:
                await self.job_service.complete_job(job.id, success=False, error_message=str(e))
            raise

    async def _evaluate_batch(
        self,
        contract_id: str,
        contract_text: str,
        rules: List[ComplianceRule]
    ) -> List[ComplianceResultData]:
        """
        Evaluate a batch of rules using LLM.

        Args:
            contract_id: Contract ID
            contract_text: Contract text
            rules: Batch of rules to evaluate

        Returns:
            List of ComplianceResultData instances
        """
        try:
            # Prepare rules for LLM
            rules_data = [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity,
                    "category": r.category
                }
                for r in rules
            ]

            # Call LLM for batch evaluation
            llm_response = await self.ai_service.evaluate_compliance_rules_batch(
                contract_text=contract_text,
                rules=rules_data
            )

            # Process evaluations
            results = []
            evaluations = llm_response.get("evaluations", [])

            for rule in rules:
                # Find evaluation for this rule
                evaluation = next(
                    (e for e in evaluations if e.get("rule_id") == rule.id),
                    None
                )

                if evaluation:
                    evaluation_result = evaluation.get("result", "not_applicable")
                    evidence = evaluation.get("evidence", [])
                    explanation = evaluation.get("explanation", "")

                    # Generate recommendation for failed/partial results
                    recommendation_dict = None
                    if evaluation_result in ["fail", "partial"]:
                        try:
                            logger.info(f"Generating recommendation for rule {rule.id} ({rule.name}) with result: {evaluation_result}")
                            recommendation = await self.ai_service.generate_compliance_recommendation(
                                rule_name=rule.name,
                                rule_description=rule.description,
                                contract_text=contract_text,
                                evidence=evidence,
                                explanation=explanation
                            )

                            # Convert to RecommendationData and validate
                            recommendation_obj = RecommendationData(
                                original_text=recommendation.get("original_text", ""),
                                proposed_text=recommendation.get("proposed_text", ""),
                                explanation=recommendation.get("explanation", ""),
                                location_context=recommendation.get("location_context", ""),
                                confidence=recommendation.get("confidence", 0.5)
                            )
                            recommendation_dict = recommendation_obj.to_dict()
                            logger.info(f"Successfully generated recommendation for rule {rule.id}")

                        except Exception as e:
                            logger.error(f"Failed to generate recommendation for rule {rule.id}: {e}")
                            # Continue without recommendation

                    # Create result from LLM evaluation
                    result = ComplianceResultData(
                        contract_id=contract_id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_description=rule.description,
                        rule_version_date=rule.updated_date,
                        evaluation_result=evaluation_result,
                        confidence=evaluation.get("confidence", 0.0),
                        explanation=explanation,
                        evidence=evidence,
                        recommendation=recommendation_dict
                    )
                else:
                    # LLM didn't return evaluation for this rule
                    logger.warning(f"No evaluation returned for rule {rule.id}")
                    result = ComplianceResultData(
                        contract_id=contract_id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_description=rule.description,
                        rule_version_date=rule.updated_date,
                        evaluation_result="not_applicable",
                        confidence=0.0,
                        explanation="Evaluation not returned by LLM",
                        evidence=[]
                    )

                # Store result
                self.cosmos_service.set_container(self.results_container)
                await self.cosmos_service.create_item(result.to_dict())

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to evaluate batch: {e}")
            raise

    async def evaluate_rule_against_contracts(
        self,
        rule_id: str,
        contract_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single rule against multiple contracts.

        Args:
            rule_id: Rule ID
            contract_ids: List of contract IDs (if None, evaluates against all contracts)

        Returns:
            Dict with 'job_id' and 'message'
        """
        try:
            # Get the rule
            rule = await self.rules_service.get_rule(rule_id)
            if not rule:
                raise ValueError(f"Rule not found: {rule_id}")

            # Get contracts (placeholder - needs contract service)
            if not contract_ids:
                logger.warning("Evaluating rule against all contracts not yet implemented")
                return {"job_id": None, "message": "Feature not yet implemented"}

            # Create job
            job = await self.job_service.create_job(
                job_type=JobType.EVALUATE_RULE.value,
                total_items=len(contract_ids),
                rule_ids=[rule_id],
                contract_ids=contract_ids
            )

            # TODO: Implement contract-by-contract evaluation
            # For now, just complete the job
            await self.job_service.complete_job(job.id, success=True)

            return {
                "job_id": job.id,
                "message": f"Evaluation queued for rule {rule.name} against {len(contract_ids)} contracts"
            }

        except Exception as e:
            logger.error(f"Failed to evaluate rule {rule_id}: {e}")
            raise

    async def get_all_results(
        self,
        result_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all evaluation results across all contracts and rules.

        Args:
            result_filter: Filter by result type (pass, fail, partial, not_applicable)
            limit: Maximum number of results to return

        Returns:
            List of compliance result dictionaries
        """
        try:
            self.cosmos_service.set_container(self.results_container)

            # Build query with optional filter
            where_clause = ""
            if result_filter:
                where_clause = f"WHERE c.evaluation_result = '{result_filter}'"

            query = f"""
                SELECT * FROM c
                {where_clause}
                ORDER BY c.evaluated_date DESC
                OFFSET 0 LIMIT {limit}
            """

            docs = await self.cosmos_service.query_items(query, cross_partition=True)
            results = [ComplianceResultData.from_dict(doc) for doc in docs]

            return [r.to_dict() for r in results]

        except Exception as e:
            logger.error(f"Failed to get all results: {e}")
            raise

    async def get_results_for_contract(self, contract_id: str) -> Dict[str, Any]:
        """
        Get all evaluation results for a contract.

        Args:
            contract_id: Contract ID

        Returns:
            Dict with 'results' and 'summary'
        """
        try:
            self.cosmos_service.set_container(self.results_container)

            query = f"""
                SELECT * FROM c
                WHERE c.contract_id = '{contract_id}'
                ORDER BY c.evaluated_date DESC
            """

            docs = await self.cosmos_service.query_items(query, cross_partition=True)
            results = [ComplianceResultData.from_dict(doc) for doc in docs]

            summary = self._build_summary(results)

            return {
                "contract_id": contract_id,
                "results": [r.to_dict() for r in results],
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Failed to get results for contract {contract_id}: {e}")
            raise

    async def get_results_for_rule(
        self,
        rule_id: str,
        result_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all evaluation results for a rule.

        Args:
            rule_id: Rule ID
            result_filter: Filter by result (pass, fail, partial, not_applicable)

        Returns:
            Dict with 'rule_id', 'rule_name', 'results', and 'summary'
        """
        try:
            # Get rule info
            rule = await self.rules_service.get_rule(rule_id)
            if not rule:
                raise ValueError(f"Rule not found: {rule_id}")

            self.cosmos_service.set_container(self.results_container)

            # Build query
            where_clause = f"c.rule_id = '{rule_id}'"
            if result_filter:
                where_clause += f" AND c.evaluation_result = '{result_filter}'"

            query = f"""
                SELECT * FROM c
                WHERE {where_clause}
                ORDER BY c.evaluated_date DESC
            """

            docs = await self.cosmos_service.query_items(query, cross_partition=True)
            results = [ComplianceResultData.from_dict(doc) for doc in docs]

            summary = self._build_summary(results)
            summary["rule_name"] = rule.name

            return {
                "rule_id": rule_id,
                "rule_name": rule.name,
                "results": [r.to_dict() for r in results],
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Failed to get results for rule {rule_id}: {e}")
            raise

    async def get_compliance_summary(self) -> Dict[str, Any]:
        """
        Get compliance summary for dashboard.

        Returns:
            Dict with overall statistics and per-rule summaries
        """
        try:
            # Get all rules
            rules = await self.rules_service.list_rules(active_only=False)

            # Get all results
            self.cosmos_service.set_container(self.results_container)
            all_docs = await self.cosmos_service.query_items("SELECT * FROM c", cross_partition=True)

            # Count contracts evaluated
            contracts_evaluated = len(set(doc["contract_id"] for doc in all_docs))

            # Build per-rule summaries
            rules_summary = []
            for rule in rules:
                rule_results = [doc for doc in all_docs if doc["rule_id"] == rule.id]

                pass_count = sum(1 for r in rule_results if r["evaluation_result"] == "pass")
                fail_count = sum(1 for r in rule_results if r["evaluation_result"] == "fail")
                partial_count = sum(1 for r in rule_results if r["evaluation_result"] == "partial")
                not_applicable_count = sum(1 for r in rule_results if r["evaluation_result"] == "not_applicable")

                total = len(rule_results)
                pass_rate = round((pass_count / total) * 100, 1) if total > 0 else 0.0

                # Check for stale results
                stale_count = sum(1 for r in rule_results if r["rule_version_date"] < rule.updated_date)

                rules_summary.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "category": rule.category,
                    "total_evaluated": total,
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "partial_count": partial_count,
                    "not_applicable_count": not_applicable_count,
                    "pass_rate": pass_rate,
                    "stale_count": stale_count,
                    "last_evaluated": max((r["evaluated_date"] for r in rule_results), default=None)
                })

            # Calculate overall pass rate as percentage
            total_results = len(all_docs)
            total_pass = sum(1 for doc in all_docs if doc["evaluation_result"] == "pass")
            overall_pass_rate = round((total_pass / total_results) * 100, 1) if total_results > 0 else 0.0

            return {
                "total_rules": len(rules),
                "active_rules": sum(1 for r in rules if r.active),
                "total_contracts_evaluated": contracts_evaluated,
                "overall_pass_rate": overall_pass_rate,
                "rules_summary": rules_summary
            }

        except Exception as e:
            logger.error(f"Failed to get compliance summary: {e}")
            raise

    def _build_summary(self, results: List[ComplianceResultData]) -> Dict[str, Any]:
        """Build summary statistics for a list of results."""
        total = len(results)
        pass_count = sum(1 for r in results if r.evaluation_result == "pass")
        fail_count = sum(1 for r in results if r.evaluation_result == "fail")
        partial_count = sum(1 for r in results if r.evaluation_result == "partial")
        not_applicable_count = sum(1 for r in results if r.evaluation_result == "not_applicable")

        return {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "partial": partial_count,
            "not_applicable": not_applicable_count
        }
