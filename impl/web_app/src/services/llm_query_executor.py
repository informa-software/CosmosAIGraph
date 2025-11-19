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
            # Normalize entities and inject into query
            normalized_plan = await self._normalize_entities(llm_plan)

            # Validate query before execution
            is_valid, validation_msg = self._validate_query(normalized_plan)
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
            if normalized_plan.query_type == "SQL":
                result = await self._execute_sql(normalized_plan, timeout)
            elif normalized_plan.query_type == "SPARQL":
                result = await self._execute_sparql(normalized_plan, timeout)
            else:
                logger.error(f"Unknown query type: {normalized_plan.query_type}")
                return ExecutionResult(
                    success=False,
                    documents=[],
                    ru_cost=0.0,
                    execution_time_ms=0.0,
                    error_message=f"Unknown query type: {normalized_plan.query_type}",
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

        # Always log the full SQL query
        logger.warning(f"[SQL QUERY] {llm_plan.query_text}")

        # Determine collection from execution plan
        collection = llm_plan.execution_plan.get("collection", "contracts")
        if isinstance(collection, list):
            collection = collection[0]  # Use first collection

        # CRITICAL: Prevent querying entity collections for contract data
        # Entity collections should only be used for ENTITY_FIRST and ENTITY_AGGREGATION strategies
        entity_collections = ["contractor_parties", "contracting_parties", "governing_law_states", "contract_types", "clause_types"]
        valid_entity_strategies = ["ENTITY_AGGREGATION", "ENTITY_FIRST"]

        if collection in entity_collections and llm_plan.strategy not in valid_entity_strategies:
            logger.error(f"[SQL QUERY] LLM attempted to query entity collection '{collection}' with strategy '{llm_plan.strategy}' - correcting to 'contracts'")
            logger.error(f"[SQL QUERY] Original query: {llm_plan.query_text}")
            collection = "contracts"
        elif collection in entity_collections and llm_plan.strategy in valid_entity_strategies:
            logger.info(f"[SQL QUERY] Querying entity collection '{collection}' with valid strategy '{llm_plan.strategy}'")

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

        # Always log the full SPARQL query
        logger.warning(f"[SPARQL QUERY] {llm_plan.query_text}")

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

    async def _normalize_entities(self, llm_plan: LLMQueryPlan) -> LLMQueryPlan:
        """
        Normalize entities using ContractEntitiesService and replace placeholders.

        Args:
            llm_plan: Original plan with entity placeholders

        Returns:
            Updated plan with normalized values in query
        """
        from src.services.contract_entities_service import ContractEntitiesService

        # Debug logging - use WARNING level to ensure visibility
        logger.warning(f"[NORMALIZATION] Starting - entities dict: {llm_plan.entities}")
        logger.warning(f"[NORMALIZATION] Original query: {llm_plan.query_text}")

        # If no entities to normalize, return original plan
        if not llm_plan.entities:
            logger.warning("[NORMALIZATION] No entities found in LLM plan - skipping normalization")
            return llm_plan

        # Initialize ContractEntitiesService if needed
        if not ContractEntitiesService.static_initialized:
            await ContractEntitiesService.initialize()

        entities = llm_plan.entities
        query_text = llm_plan.query_text
        normalized_mapping = {}

        for placeholder, entity_info in entities.items():
            raw_value = entity_info["raw_value"]
            entity_type = entity_info["entity_type"]

            # Use fuzzy matching to find entity
            matches = ContractEntitiesService.identify_entities_in_text(raw_value)

            # Get entity collection name with proper pluralization
            # contracting_party → contracting_parties, contractor_party → contractor_parties
            if entity_type.endswith("y") and not entity_type.endswith("ay") and not entity_type.endswith("ey") and not entity_type.endswith("oy") and not entity_type.endswith("uy"):
                entity_collection = entity_type[:-1] + "ies"
            elif entity_type.endswith("s"):
                entity_collection = entity_type
            else:
                entity_collection = entity_type + "s"

            # Debug: Get ALL entity comparisons (even below threshold) from debug_all_scores
            all_debug_scores = matches.get("debug_all_scores", [])

            # Filter for the entity type we're looking for
            relevant_scores = [m for m in all_debug_scores if m.get("type") == entity_type.rstrip('s') or m.get("match_type") == "exact_normalized"]

            # Sort by confidence to see best matches first
            relevant_scores.sort(key=lambda m: m.get("confidence", 0), reverse=True)

            logger.warning(f"[NORMALIZATION] Entity lookup for '{raw_value}' in collection '{entity_collection}':")
            logger.warning(f"[NORMALIZATION] - Total entities compared: {len(relevant_scores)}")
            logger.warning(f"[NORMALIZATION] - Matches above threshold (0.85): {len(matches.get(entity_collection, []))}")
            logger.warning(f"[NORMALIZATION] - Matches below threshold: {len(relevant_scores) - len(matches.get(entity_collection, []))}")

            # Log top candidates for debugging (even if below threshold)
            if relevant_scores:
                logger.warning(f"[NORMALIZATION] Top matches (showing all scores, threshold=0.85):")
                for i, candidate in enumerate(relevant_scores[:10]):  # Show top 10 candidates
                    conf = candidate.get('confidence', 0)
                    orig = candidate.get('original_score', conf)
                    tokens = candidate.get('has_all_tokens', 'N/A')
                    threshold_marker = "✓" if conf >= 0.85 else "✗"
                    logger.warning(f"[NORMALIZATION]   {threshold_marker} {i+1}. '{candidate.get('normalized_name')}' | display: '{candidate.get('display_name')}' | conf: {conf:.3f} (orig: {orig:.3f}) | all_tokens: {tokens}")
            else:
                logger.warning(f"[NORMALIZATION]   No entities found in database for comparison")

            # Use the matches that passed the threshold
            all_candidates = matches.get(entity_collection, []) + [m for m in matches.get("fuzzy_matches", []) if m.get("type") == entity_type.rstrip('s')]

            if matches.get(entity_collection) and len(matches[entity_collection]) > 0:
                # Use best match from fuzzy matching - this is from the DATABASE
                # Sort by confidence first, then by length (prefer longer matches)
                sorted_matches = sorted(
                    matches[entity_collection],
                    key=lambda m: (m["confidence"], len(m["normalized_name"])),
                    reverse=True
                )
                normalized_value = sorted_matches[0]["normalized_name"]
                confidence = sorted_matches[0]["confidence"]
                logger.warning(f"[NORMALIZATION] Fuzzy matched '{raw_value}' → '{normalized_value}' (confidence: {confidence:.2f})")
                normalized_mapping[placeholder] = {
                    "raw_value": raw_value,
                    "normalized_value": normalized_value,
                    "method": "fuzzy_match",
                    "confidence": confidence
                }
            else:
                # NO MATCH FOUND in database - check fuzzy_matches for lower confidence matches
                fuzzy_matches = matches.get("fuzzy_matches", [])
                best_fuzzy = [m for m in fuzzy_matches if m.get("type") == entity_type.rstrip('s')]

                if best_fuzzy:
                    # Found a match below 85% threshold - use it but log warning
                    best_match = best_fuzzy[0]
                    normalized_value = best_match["normalized_name"]
                    confidence = best_match["confidence"]
                    logger.warning(f"[NORMALIZATION] LOW CONFIDENCE match for '{raw_value}' → '{normalized_value}' (confidence: {confidence:.2f}, below 0.85 threshold)")
                    logger.warning("[NORMALIZATION] Query may return unexpected results. Consider using the exact entity name from the database.")
                    normalized_mapping[placeholder] = {
                        "raw_value": raw_value,
                        "normalized_value": normalized_value,
                        "method": "low_confidence_match",
                        "confidence": confidence
                    }
                else:
                    # No match at all - entity doesn't exist in database
                    # Use the best match from debug_all_scores even if below threshold
                    if relevant_scores:
                        best_match = relevant_scores[0]
                        normalized_value = best_match["normalized_name"]
                        confidence = best_match.get("confidence", 0.0)
                        logger.error(f"[NORMALIZATION] No matches above threshold for '{raw_value}'")
                        logger.error(f"[NORMALIZATION] Using best available match: '{normalized_value}' (confidence: {confidence:.3f})")
                        logger.error("[NORMALIZATION] Query may return unexpected results due to low confidence match.")
                        normalized_mapping[placeholder] = {
                            "raw_value": raw_value,
                            "normalized_value": normalized_value,
                            "method": "best_available_below_threshold",
                            "confidence": confidence
                        }
                    else:
                        # Truly no matches found - this should rarely happen
                        logger.error(f"[NORMALIZATION] CRITICAL: No entities found in database for '{raw_value}'")
                        logger.error(f"[NORMALIZATION] Cannot normalize entity. Query will fail.")
                        # Don't generate a fake normalized value - use the raw value and let the query fail
                        normalized_mapping[placeholder] = {
                            "raw_value": raw_value,
                            "normalized_value": raw_value,  # Use raw value as-is
                            "method": "no_match_found",
                            "confidence": 0.0
                        }

            # Replace placeholder in query (handle both :placeholder and 'placeholder' formats)
            query_text = query_text.replace(f":{placeholder}", f"'{normalized_value}'")

        logger.warning(f"[NORMALIZATION] Complete: {len(normalized_mapping)} entities processed")
        logger.warning(f"[NORMALIZATION] Normalized query: {query_text}")

        # Return updated plan with normalized query
        return LLMQueryPlan(
            strategy=llm_plan.strategy,
            fallback_strategy=llm_plan.fallback_strategy,
            query_type=llm_plan.query_type,
            query_text=query_text,  # Updated with normalized values
            execution_plan={**llm_plan.execution_plan, "normalized_entities": normalized_mapping},
            confidence=llm_plan.confidence,
            reasoning=llm_plan.reasoning,
            result_format=llm_plan.result_format,
            entities=llm_plan.entities,  # Keep original for trace
            raw_response=llm_plan.raw_response
        )
