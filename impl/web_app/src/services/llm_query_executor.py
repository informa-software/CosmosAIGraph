"""
LLM Query Executor

Executes LLM-generated query plans with proper validation and error handling.
Routes queries to appropriate services based on query type (SQL, SPARQL, etc.).
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.services.llm_query_planner import LLMQueryPlan
from src.services.sql_validator import SQLValidator
from src.services.sparql_validator import SPARQLValidator

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing an LLM query plan."""
    success: bool
    documents: List[Dict]
    ru_cost: float
    execution_time_ms: float
    error_message: Optional[str] = None
    executed_query: Optional[str] = None
    fallback_used: bool = False


class LLMQueryExecutor:
    """
    Executes LLM-generated query plans.

    Validates queries before execution and handles errors with proper fallback.
    Routes queries to appropriate services based on type (SQL, SPARQL).
    """

    def __init__(self, cosmos_service=None, ontology_service=None):
        """
        Initialize executor with required services.

        Args:
            cosmos_service: CosmosNoSQLService for SQL queries
            ontology_service: OntologyService for SPARQL queries
        """
        self.cosmos_service = cosmos_service
        self.ontology_service = ontology_service
        self.sql_validator = SQLValidator()
        self.sparql_validator = SPARQLValidator()

    async def execute_plan(self, llm_plan: LLMQueryPlan, strategy: str = "db",
                     timeout: float = 10.0) -> ExecutionResult:
        """
        Execute an LLM query plan.

        Args:
            llm_plan: LLM-generated query plan
            strategy: Rule-based strategy for fallback context
            timeout: Query timeout in seconds

        Returns:
            ExecutionResult with documents and metadata
        """
        import time
        start_time = time.time()

        try:
            # Validate query before execution
            is_valid, validation_msg = self._validate_query(llm_plan)
            if not is_valid:
                logger.warning(f"LLM query validation failed: {validation_msg}")
                return ExecutionResult(
                    success=False,
                    documents=[],
                    ru_cost=0.0,
                    execution_time_ms=0.0,
                    error_message=f"Validation failed: {validation_msg}",
                    fallback_used=True
                )

            # Route based on query type
            if llm_plan.query_type == "SQL":
                result = await self._execute_sql(llm_plan, timeout)
            elif llm_plan.query_type == "SPARQL":
                result = await self._execute_sparql(llm_plan, timeout)
            else:
                logger.error(f"Unknown query type: {llm_plan.query_type}")
                return ExecutionResult(
                    success=False,
                    documents=[],
                    ru_cost=0.0,
                    execution_time_ms=0.0,
                    error_message=f"Unknown query type: {llm_plan.query_type}",
                    fallback_used=True
                )

            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms

            logger.info(f"LLM query executed successfully: {len(result.documents)} docs, "
                       f"{result.ru_cost:.1f} RUs, {execution_time_ms:.0f}ms")

            return result

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"LLM query execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                documents=[],
                ru_cost=0.0,
                execution_time_ms=execution_time_ms,
                error_message=str(e),
                fallback_used=True
            )

    def _validate_query(self, llm_plan: LLMQueryPlan) -> Tuple[bool, str]:
        """
        Validate LLM query before execution.

        Args:
            llm_plan: LLM query plan to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check confidence threshold
        if llm_plan.confidence < 0.5:
            return False, f"Low confidence: {llm_plan.confidence:.2f}"

        # Validate query syntax based on type
        if llm_plan.query_type == "SQL":
            is_valid, msg = self.sql_validator.validate(llm_plan.query_text)
            if not is_valid:
                return False, f"SQL validation failed: {msg}"

        elif llm_plan.query_type == "SPARQL":
            is_valid, msg = self.sparql_validator.validate(llm_plan.query_text)
            if not is_valid:
                return False, f"SPARQL validation failed: {msg}"

        # Validate strategy is known
        known_strategies = ["ENTITY_FIRST", "CONTRACT_DIRECT", "ENTITY_AGGREGATION",
                           "GRAPH_TRAVERSAL", "VECTOR_SEARCH"]
        if llm_plan.strategy not in known_strategies:
            return False, f"Unknown strategy: {llm_plan.strategy}"

        return True, "Valid"

    async def _execute_sql(self, llm_plan: LLMQueryPlan, timeout: float) -> ExecutionResult:
        """
        Execute SQL query using CosmosDB service.

        Args:
            llm_plan: LLM query plan with SQL query
            timeout: Query timeout in seconds

        Returns:
            ExecutionResult with query results
        """
        if not self.cosmos_service:
            raise ValueError("CosmosDB service not configured")

        logger.info(f"Executing LLM SQL query: {llm_plan.query_text[:100]}...")

        # Determine collection from execution plan
        collection = llm_plan.execution_plan.get("collection", "contracts")
        if isinstance(collection, list):
            collection = collection[0]  # Use first collection

        # Execute SQL query
        try:
            # Set the container before querying
            self.cosmos_service.set_container(collection)

            # Execute query with correct parameters
            documents = await self.cosmos_service.query_items(
                sql=llm_plan.query_text,
                cross_partition=True
            )

            # Get RU cost from last request charge (it's a method, must call it)
            ru_cost = self.cosmos_service.last_request_charge()

            return ExecutionResult(
                success=True,
                documents=documents,
                ru_cost=ru_cost,
                execution_time_ms=0.0,  # Will be set by caller
                executed_query=llm_plan.query_text,
                fallback_used=False
            )

        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            raise

    async def _execute_sparql(self, llm_plan: LLMQueryPlan, timeout: float) -> ExecutionResult:
        """
        Execute SPARQL query using Ontology service.

        Args:
            llm_plan: LLM query plan with SPARQL query
            timeout: Query timeout in seconds

        Returns:
            ExecutionResult with query results
        """
        if not self.ontology_service:
            raise ValueError("Ontology service not configured")

        logger.info(f"Executing LLM SPARQL query: {llm_plan.query_text[:100]}...")

        try:
            # Execute SPARQL query via OntologyService
            results = self.ontology_service.sparql_query(llm_plan.query_text)

            # Convert SPARQL results to document format
            documents = []
            if results and 'results' in results and 'bindings' in results['results']:
                for binding in results['results']['bindings']:
                    # Convert SPARQL binding to document dict
                    doc = {}
                    for var, value in binding.items():
                        doc[var] = value.get('value', '')
                    documents.append(doc)

            # Estimate RU cost for SPARQL (graph queries typically cost more)
            estimated_ru_cost = llm_plan.execution_plan.get("estimated_ru_cost", 10.0)

            return ExecutionResult(
                success=True,
                documents=documents,
                ru_cost=estimated_ru_cost,
                execution_time_ms=0.0,  # Will be set by caller
                executed_query=llm_plan.query_text,
                fallback_used=False
            )

        except Exception as e:
            logger.error(f"SPARQL execution failed: {str(e)}")
            raise
