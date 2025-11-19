import asyncio
import json
import logging

import httpx
from typing import Optional

from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.contract_strategy_builder import ContractStrategyBuilder
from src.services.ontology_service import OntologyService
from src.services.query_optimizer import QueryOptimizer, QueryStrategy
from src.services.query_execution_tracker import QueryExecutionTracker, ExecutionStatus
from src.services.rag_data_result import RAGDataResult
from src.util.cosmos_doc_filter import CosmosDocFilter
from src.util.sparql_query_response import SparqlQueryResponse
from src.util.fs import FS

# Instances of this class are used to identify and retrieve contextual data
# in OmniRAG pattern. The data will be read from one or more of the following:
# 1) Directly from Cosmos DB documents
# 2) From in-memory graph
# 3) From Cosmos DB documents identified per a vector search to Cosmos DB
#
# Chris Joakim & Aleksey Savateyev, Microsoft, 2025


class RAGDataService:

    def __init__(self, ai_svc: AiService, nosql_svc: CosmosNoSQLService, ontology_svc=None):
        try:
            self.ai_svc = ai_svc
            self.nosql_svc = nosql_svc
            self.ontology_svc = ontology_svc

            # web service authentication with shared secrets
            websvc_auth_header = ConfigService.websvc_auth_header()
            websvc_auth_value = ConfigService.websvc_auth_value()
            self.websvc_headers = dict()
            self.websvc_headers["Content-Type"] = "application/json"
            self.websvc_headers[websvc_auth_header] = websvc_auth_value
            logging.debug(
                "RAGDataService websvc_headers: {}".format(
                    json.dumps(self.websvc_headers, sort_keys=False)
                )
            )
        except Exception as e:
            logging.critical("Exception in RagDataService#__init__: {}".format(str(e)))

    async def get_rag_data(self, user_text, max_doc_count=10, strategy_override: Optional[str] = None,
                          enable_tracking: bool = True) -> RAGDataResult:
        """
        Return a RAGDataResult object which contains an array of documents to
        be used as a system prompt of a completion call to Azure OpenAI.
        In this OmniRAG implementation, the RAG data will be read,
        per the given user_text, from one of the following:
        1) Directly from Cosmos DB documents
        2) From in-memory graph
        3) From Cosmos DB documents identified per a vector search to Cosmos DB
        """
        rdr = RAGDataResult()
        rdr.set_user_text(user_text)
        rdr.set_attr("max_doc_count", max_doc_count)

        # Use contract strategy builder for all queries
        sb = ContractStrategyBuilder(self.ai_svc)
        strategy_obj = sb.determine(user_text)
        # honor explicit user choice when provided and valid; still use name/context from builder
        valid_choices = {"db", "vector", "graph"}
        strategy = strategy_obj["strategy"]
        if strategy_override and strategy_override in valid_choices:
            strategy = strategy_override
        rdr.add_strategy(strategy)
        rdr.set_context(strategy_obj["name"])

        # Initialize execution tracker if enabled
        if enable_tracking:
            # Get LLM plan from strategy dict (if available from Phase 1)
            llm_plan = strategy_obj.get("llm_plan") if isinstance(strategy_obj, dict) else None
            tracker = QueryExecutionTracker(user_text, strategy, llm_plan)
            rdr.set_execution_tracker(tracker)

        if strategy == "db":
            name = strategy_obj.get("name", "")
            rdr.set_attr("name", name)
            await self.get_database_rag_data(user_text, strategy_obj, rdr, max_doc_count)
            if rdr.has_no_docs():
                rdr.add_strategy("vector")
                await self.get_vector_rag_data(user_text, rdr, max_doc_count)

        elif strategy == "graph":
            await self.get_graph_rag_data(user_text, strategy_obj, rdr, max_doc_count)
            if rdr.has_no_docs():
                rdr.add_strategy("vector")
                await self.get_vector_rag_data(user_text, rdr, max_doc_count)
        else:
            await self.get_vector_rag_data(user_text, rdr, max_doc_count)

        rdr.finish()
        return rdr

    async def get_database_rag_data(
        self, user_text: str, strategy_obj: dict, rdr: RAGDataResult, max_doc_count=10
    ) -> None:
        rag_docs_list = list()
        try:
            logging.warning(
                f"RagDataService#get_database_rag_data, user_text: {user_text}, strategy: {strategy_obj}"
            )
            
            self.nosql_svc.set_db(ConfigService.graph_source_db())

            # Get execution tracker
            tracker = rdr.get_execution_tracker()

            # Check if we should use LLM execution (Phase 3)
            llm_plan = strategy_obj.get("llm_plan")
            llm_execution_mode = ConfigService.envvar("CAIG_LLM_EXECUTION_MODE", "comparison_only").lower()

            should_use_llm = False

            # PRIORITY 1: Use LLM when strategy was overridden due to mismatch
            if (strategy_obj.get("algorithm") == "llm_override" and
                llm_plan and llm_plan.get("validation_status") == "valid"):
                should_use_llm = True
                logging.info("Using LLM execution due to strategy mismatch override")

            # PRIORITY 2: Check execution mode settings
            elif llm_plan and llm_execution_mode == "execution":
                # Always use LLM in execution mode (if valid)
                should_use_llm = (llm_plan.get("validation_status") == "valid" and
                                 llm_plan.get("confidence", 0.0) >= 0.5)
            elif llm_plan and llm_execution_mode == "a_b_test":
                # A/B testing: randomly choose LLM or rule-based
                import random
                should_use_llm = (random.random() < 0.5 and
                                 llm_plan.get("validation_status") == "valid" and
                                 llm_plan.get("confidence", 0.0) >= 0.5)

            # Execute LLM-generated query if enabled and valid
            if should_use_llm:
                try:
                    logging.info(f"Using LLM execution path (mode: {llm_execution_mode})")
                    rag_docs_list = await self._execute_llm_query(llm_plan, max_doc_count, tracker, rdr)

                    # If LLM execution succeeded, add docs and return
                    if rag_docs_list is not None:
                        logging.info(f"LLM execution returned {len(rag_docs_list)} documents")
                        for doc in rag_docs_list[:max_doc_count]:
                            doc_copy = dict(doc)
                            doc_copy.pop("embedding", None)
                            rdr.add_doc(doc_copy)
                        return
                    else:
                        logging.warning("LLM execution returned None, falling back to rule-based")

                except Exception as e:
                    logging.warning(f"LLM execution failed: {str(e)}, falling back to rule-based")
                    if tracker:
                        tracker.fallback_count += 1

            # Check if we have optimal path from QueryOptimizer (rule-based)
            optimal_path = strategy_obj.get("optimal_path")

            if optimal_path:
                logging.info(f"Using optimized query path: {optimal_path.get('strategy')}, {optimal_path.get('explanation')}")

                # Handle different query strategies
                if optimal_path.get("strategy") == QueryStrategy.ENTITY_FIRST:
                    # Query entity collection first, then get contracts
                    rag_docs_list = await self._handle_entity_first_query(optimal_path, max_doc_count, tracker)

                elif optimal_path.get("strategy") == QueryStrategy.ENTITY_AGGREGATION:
                    # Get aggregated data from entity collection
                    aggregate_result = await self._handle_aggregation_query(optimal_path, tracker)
                    if aggregate_result:
                        rag_docs_list = [aggregate_result]

                elif optimal_path.get("strategy") == QueryStrategy.CONTRACT_DIRECT:
                    # Direct query on contracts with filters
                    filter_dict = optimal_path.get("filter", {})
                    if filter_dict and tracker:
                        step = tracker.start_step(
                            "Direct Contract Query",
                            "CONTRACT_DIRECT",
                            "contracts"
                        )
                        try:
                            # Build SQL query for tracking
                            where_clauses = [f"c.{field} = '{value}'" for field, value in filter_dict.items()]
                            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                            sql_query = f"SELECT TOP {max_doc_count} * FROM c WHERE {where_clause}"

                            rag_docs_list = await self.nosql_svc.query_contracts_with_filter(
                                filter_dict, max_doc_count
                            )
                            tracker.complete_step(
                                step, ExecutionStatus.SUCCESS,
                                ru_cost=5.0, docs_found=len(rag_docs_list),
                                metadata={'filter': filter_dict, 'sql': sql_query}
                            )
                        except Exception as e:
                            if tracker:
                                tracker.complete_step(step, ExecutionStatus.FAILED, error=str(e))
                            raise
                    elif filter_dict:
                        rag_docs_list = await self.nosql_svc.query_contracts_with_filter(
                            filter_dict, max_doc_count
                        )

                # If optimal path handled the query, add docs and return
                if rag_docs_list:
                    for doc in rag_docs_list[:max_doc_count]:
                        doc_copy = dict(doc)
                        doc_copy.pop("embedding", None)
                        rdr.add_doc(doc_copy)
                    return
            
            # Check if we have a specific contract ID
            if "contract_id" in strategy_obj:
                contract_id = strategy_obj["contract_id"]
                logging.info(f"Querying for specific contract ID: {contract_id}")
                
                # Query for specific contract
                rag_docs_list = await self.nosql_svc.get_documents_by_entity(
                    entity_type="contract_id",
                    entity_values=[contract_id],
                    container_name="contracts"
                )
                
                # If we need chunks too
                if strategy_obj.get("query_config", {}).get("chunk_retrieval"):
                    # Get chunk IDs from parent documents
                    chunk_ids = []
                    for doc in rag_docs_list:
                        chunk_ids.extend(doc.get("chunk_ids", []))
                    
                    if chunk_ids:
                        # Retrieve chunks
                        self.nosql_svc.set_container("contract_chunks")
                        chunks = await self.nosql_svc.get_documents_by_ids(chunk_ids[:max_doc_count])
                        rag_docs_list.extend(chunks)
            
            # Check if we have entity information
            elif "primary_entity" in strategy_obj:
                entity = strategy_obj["primary_entity"]
                entity_type = entity.get("type")
                entity_value = entity.get("value")
                
                # Use the new entity-aware method
                rag_docs_list = await self.nosql_svc.get_documents_by_entity(
                    entity_type=entity_type,
                    entity_values=[entity_value],
                    container_name="contracts"
                )
                
                # If we need chunks too
                if strategy_obj.get("query_config", {}).get("chunk_retrieval"):
                    # Get chunk IDs from parent documents
                    chunk_ids = []
                    for doc in rag_docs_list:
                        chunk_ids.extend(doc.get("chunk_ids", []))
                    
                    if chunk_ids:
                        # Retrieve chunks
                        self.nosql_svc.set_container("contract_chunks")
                        chunks = await self.nosql_svc.get_documents_by_ids(chunk_ids[:max_doc_count])
                        rag_docs_list.extend(chunks)
            
            elif "name" in strategy_obj:
                # Fallback to old library behavior for backward compatibility
                name = strategy_obj["name"]
                logging.info(f"Using legacy library lookup for name: {name}")
                self.nosql_svc.set_container(ConfigService.graph_vector_container())
                rag_docs_list = await self.nosql_svc.get_documents_by_name([name])
            
            else:
                # No entity or name detected, fallback to vector search
                logging.warning("No entity detected, falling back to vector search")
                rdr.add_strategy("vector")
                return  # Let vector search handle it
            
            # Add documents to result
            for doc in rag_docs_list[:max_doc_count]:
                doc_copy = dict(doc)  # shallow copy
                doc_copy.pop("embedding", None)
                rdr.add_doc(doc_copy)
                
        except Exception as e:
            logging.critical(
                f"Exception in RagDataService#get_database_rag_data: {str(e)}"
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def filtered_cosmosdb_lib_doc(self, cosmos_db_doc):
        """
        Reduce the given Cosmos DB document to only the pertinent attributes,
        and truncate those if they're long.
        """
        cdf = CosmosDocFilter(cosmos_db_doc)
        return cdf.filter_for_rag_data()

    async def get_vector_rag_data(
        self, user_text, rdr: RAGDataResult = None, max_doc_count=10
    ) -> None:
        from src.services.query_execution_tracker import ExecutionStatus
        tracker = rdr.get_execution_tracker() if rdr else None
        step = None

        try:
            logging.warning(
                "RagDataService#get_vector_rag_data, user_text: {}".format(user_text)
            )

            # Determine if this is a fallback
            is_fallback = tracker and tracker.fallback_count > 0 if tracker else False

            # Track vector search step
            if tracker:
                step = tracker.start_step(
                    "Vector Search (RRF)",
                    "VECTOR_SEARCH",
                    ConfigService.graph_vector_container(),
                    is_fallback=is_fallback
                )

            # Generate embedding
            create_embedding_response = self.ai_svc.generate_embeddings(user_text)
            embedding = create_embedding_response.data[0].embedding

            # Set database and container
            self.nosql_svc.set_db(ConfigService.graph_source_db())
            #Use the new GRAPH_VECTOR_CONTAINER for Contract related Vector Searches
            # To Do - When doing Clause Searches, we should use the CLAUSE Vector Container
            self.nosql_svc.set_container(ConfigService.graph_vector_container())

            # Perform vector search
            vs_result = await self.nosql_svc.vector_search(
                embedding_value=embedding, search_text=user_text, search_method="rrf", embedding_attr="embedding", limit=max_doc_count
            )

            # Get RU cost from last operation
            ru_cost = self.nosql_svc.last_request_charge()

            # Deduplicate by filename, keeping document with highest similarity (lowest VectorDistance)
            # VectorDistance returns lower values for more similar documents
            filename_map = {}
            for vs_doc in vs_result:
                doc_copy = dict(vs_doc)  # shallow copy
                doc_copy.pop("embedding", None)

                # Keep similarity_score if present (don't pop it)
                filename = doc_copy.get('filename', doc_copy.get('id'))
                similarity = doc_copy.get('similarity_score', float('inf'))

                # Keep document with lowest VectorDistance (highest similarity)
                if filename not in filename_map or similarity < filename_map[filename].get('similarity_score', float('inf')):
                    filename_map[filename] = doc_copy

            # Add deduplicated documents to result
            for doc in filename_map.values():
                rdr.add_doc(doc)

            # Complete tracking step
            if tracker and step:
                tracker.complete_step(
                    step,
                    ExecutionStatus.SUCCESS,
                    ru_cost=ru_cost,
                    docs_found=len(filename_map),
                    metadata={
                        'method': 'RRF (Reciprocal Rank Fusion)',
                        'search_text': user_text[:100],
                        'embedding_dims': len(embedding),
                        'is_fallback': is_fallback,
                        'original_results': len(vs_result),
                        'deduplicated_results': len(filename_map)
                    }
                )

            logging.info(f"Vector search completed: {len(vs_result)} documents → {len(filename_map)} after deduplication, {ru_cost:.1f} RUs")

        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_vector_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

            if tracker and step:
                tracker.complete_step(
                    step,
                    ExecutionStatus.FAILED,
                    error=str(e)
                )

    async def get_graph_rag_data(
        self, user_text, strategy_obj: dict, rdr: RAGDataResult, max_doc_count=10
    ) -> None:
        tracker = rdr.get_execution_tracker()
        step = None
        try:
            logging.warning(
                "RagDataService#get_graph_rag_data, user_text: {}".format(user_text)
            )

            # Track SPARQL generation
            if tracker:
                step = tracker.start_step(
                    "SPARQL Query Generation & Execution",
                    "GRAPH_TRAVERSAL",
                    "graph"
                )

            # first generate and execute the SPARQL query vs the in-memory RDF graph
            info = dict()
            info["natural_language"] = user_text
            info["owl"] = OntologyService().get_owl_content()

            # Extract and include normalized entities for accurate SPARQL generation
            entities = strategy_obj.get("entities", {})
            if entities:
                entity_hints = []
                for entity_type, entity_list in entities.items():
                    if entity_type in ["contractor_parties", "contracting_parties", "governing_law_states", "contract_types"]:
                        for entity in entity_list:
                            normalized_name = entity.get("normalized_name", "")
                            display_name = entity.get("display_name", "")
                            confidence = entity.get("confidence", 0.0)
                            if normalized_name and confidence >= 0.85:
                                # Use normalized name for database accuracy
                                entity_hints.append(f"{entity_type}: '{normalized_name}' (original: '{display_name}')")

                if entity_hints:
                    info["normalized_entities"] = " | ".join(entity_hints)
                    logging.info(f"Adding normalized entities to SPARQL generation: {info['normalized_entities']}")

            # Include negation information if available to help SPARQL generation
            negations = strategy_obj.get("negations", {})
            if any(negations.values()):
                negation_hints = []
                for entity_type, negated_entities in negations.items():
                    for entity in negated_entities:
                        negation_hints.append(f"EXCLUDE {entity_type}: {entity.get('display_name')}")
                info["negations"] = " | ".join(negation_hints)
                logging.info(f"Adding negation hints to SPARQL generation: {info['negations']}")

            # Note: negations are now appended to user_prompt in ai_service.py for better context

            sparql = self.ai_svc.generate_sparql_from_user_prompt(info)["sparql"]
            rdr.set_sparql(sparql)
            logging.warning("get_graph_rag_data - sparql:\n{}".format(sparql))

            # HTTP POST to the graph microservice to execute the generated SPARQL query
            sqr: SparqlQueryResponse = await self.post_sparql_to_graph_microsvc(sparql)
            FS.write_json(
                sqr.response_obj,
                "tmp/get_graph_rag_data_get_graph_rag_data_response_obj.json",
            )

            docs_found = 0
            for doc in sqr.binding_values():
                doc_copy = dict(doc)  # shallow copy
                doc_copy.pop("embedding", None)
                rdr.add_doc(doc_copy)
                docs_found += 1

            # Track success
            if tracker and step:
                tracker.complete_step(
                    step, ExecutionStatus.SUCCESS,
                    ru_cost=10.0, docs_found=docs_found,
                    metadata={'sparql': sparql}
                )
            FS.write_json(rdr.get_data(), "tmp/rdr.json")
        except Exception as e:
            # Track failure
            if tracker and step:
                tracker.complete_step(step, ExecutionStatus.FAILED, error=str(e))
            logging.critical(
                "Exception in RagDataService#get_graph_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    # ========== private methods below ==========

    async def post_sparql_to_graph_microsvc(self, sparql: str) -> list:
        """
        Execute a HTTP POST to the graph microservice with the given SPARQL query.
        Return a list of dicts.
        """
        sqr = None
        try:
            url = self.graph_microsvc_sparql_query_url()
            postdata = dict()
            postdata["sparql"] = sparql
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    url,
                    headers=self.websvc_headers,
                    content=json.dumps(postdata),
                    timeout=30.0,
                )
                sqr = SparqlQueryResponse(r)
                sqr.parse()
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        return sqr

    def graph_microsvc_sparql_query_url(self):
        return "{}:{}/sparql_query".format(
            ConfigService.graph_service_url(), ConfigService.graph_service_port()
        )

    async def _execute_llm_query(self, llm_plan: dict, max_count: int, tracker=None, rdr=None) -> Optional[list]:
        """
        Execute LLM-generated query plan.

        Args:
            llm_plan: LLM query plan dict with query_text, query_type, etc.
            max_count: Maximum number of documents to return
            tracker: Execution tracker for logging
            rdr: RAGDataResult for strategy tracking

        Returns:
            List of documents or None if execution failed
        """
        from src.services.llm_query_planner import LLMQueryPlan
        from src.services.llm_query_executor import LLMQueryExecutor
        from src.services.query_execution_tracker import ExecutionStatus
        import time

        try:
            # Convert dict back to LLMQueryPlan object
            plan_obj = LLMQueryPlan(
                strategy=llm_plan.get("strategy"),
                fallback_strategy=llm_plan.get("fallback_strategy", "VECTOR_SEARCH"),
                query_type=llm_plan.get("query_type"),
                query_text=llm_plan.get("query_text"),
                execution_plan=llm_plan.get("execution_plan", {}),
                confidence=llm_plan.get("confidence", 0.0),
                reasoning=llm_plan.get("reasoning", ""),
                result_format=llm_plan.get("result_format", "list_summary"),
                entities=llm_plan.get("entities", {}),
                raw_response={}
            )

            # Create executor with services
            executor = LLMQueryExecutor(
                cosmos_service=self.nosql_svc,
                ontology_service=self.ontology_svc
            )

            # Track LLM execution step
            step = None
            if tracker:
                step = tracker.start_step(
                    f"LLM {plan_obj.query_type} Query",
                    plan_obj.strategy,
                    plan_obj.execution_plan.get("collection", "contracts")
                )

            # Execute the query
            result = await executor.execute_plan(plan_obj)

            # Complete tracking step
            if tracker and step:
                if result.success:
                    tracker.complete_step(
                        step,
                        ExecutionStatus.SUCCESS,
                        ru_cost=result.ru_cost,
                        docs_found=len(result.documents),
                        metadata={
                            'query_type': plan_obj.query_type,
                            'query': result.executed_query,
                            'confidence': plan_obj.confidence,
                            'reasoning': plan_obj.reasoning if plan_obj.reasoning else ""
                        }
                    )
                else:
                    tracker.complete_step(
                        step,
                        ExecutionStatus.FAILED,
                        error=result.error_message
                    )

            # Update strategy and result_format in rdr
            if rdr and result.success:
                strategy_map = {
                    "ENTITY_FIRST": "db",
                    "CONTRACT_DIRECT": "db",
                    "ENTITY_AGGREGATION": "db",
                    "GRAPH_TRAVERSAL": "graph",
                    "VECTOR_SEARCH": "vector"
                }
                mapped_strategy = strategy_map.get(plan_obj.strategy, "db")
                rdr.add_strategy(mapped_strategy)
                # Set result format from LLM plan
                rdr.set_result_format(plan_obj.result_format)

            # Return documents if successful
            if result.success:
                logging.info(f"LLM execution succeeded: {len(result.documents)} docs, "
                           f"{result.ru_cost:.1f} RUs")

                # CRITICAL: Handle ENTITY_FIRST strategy - need to extract contract IDs and batch retrieve
                if plan_obj.strategy == "ENTITY_FIRST" and len(result.documents) > 0:
                    logging.info("LLM used ENTITY_FIRST strategy - performing Step 2: batch contract retrieval")

                    # Update Step 1 metadata to show entity document was retrieved
                    if tracker and step:
                        tracker.update_step_metadata(
                            step,
                            {
                                'query_type': plan_obj.query_type,
                                'query': result.executed_query,
                                'confidence': plan_obj.confidence,
                                'reasoning': plan_obj.reasoning if plan_obj.reasoning else "",
                                'entity_retrieved': True,
                                'entity_id': result.documents[0].get('id')
                            }
                        )

                    # The result contains entity document(s) with "contracts" array
                    entity_doc = result.documents[0]  # Should be single entity document
                    contract_ids = entity_doc.get("contracts", [])

                    if not contract_ids:
                        logging.warning(f"Entity document has no contracts: {entity_doc.get('id')}")
                        return []

                    # Track Step 2: Batch Contract Retrieval
                    step2 = None
                    if tracker:
                        # Generate the batch read SQL for display
                        id_list = ', '.join([f"'{cid}'" for cid in contract_ids[:5]])
                        ellipsis = '...' if len(contract_ids) > 5 else ''
                        batch_sql = f"SELECT * FROM c WHERE c.id IN ({id_list}{ellipsis})"
                        step2 = tracker.start_step(
                            "Batch Contract Retrieval",
                            "ENTITY_FIRST",
                            "contracts"
                        )

                    # Batch retrieve actual contracts (use max_count parameter, not max_doc_count)
                    contracts = await self.nosql_svc.batch_get_contracts(contract_ids, max_count)

                    if tracker and step2:
                        tracker.complete_step(
                            step2, ExecutionStatus.SUCCESS,
                            ru_cost=len(contracts) * 1.0,
                            docs_found=len(contracts),
                            metadata={
                                'method': 'Batch Point Read',
                                'entity': entity_doc.get('normalized_name'),
                                'total_ids': len(contract_ids),
                                'retrieved': len(contracts),
                                'queries_executed': len(contracts),  # One point read per contract
                                'query_pattern': f"Point read by ID (executed {len(contracts)} times)"
                            }
                        )

                    logging.info(f"ENTITY_FIRST Step 2 complete: retrieved {len(contracts)} contracts from {len(contract_ids)} IDs")
                    return contracts

                # For other strategies, return documents as-is
                return result.documents
            else:
                logging.warning(f"LLM execution failed: {result.error_message}")
                return None

        except Exception as e:
            logging.error(f"Error executing LLM query: {str(e)}")
            if tracker and step:
                tracker.complete_step(step, ExecutionStatus.FAILED, error=str(e))
            return None

    async def _handle_entity_first_query(self, optimal_path: dict, max_count: int, tracker=None) -> list:
        """Handle entity-first query strategy"""
        try:
            entity_info = optimal_path.get("entity_info", {})
            collection = optimal_path.get("collection")

            if not entity_info or not collection:
                return []

            # Track Step 1: Entity Collection Query
            step1 = None
            entity_sql = None
            if tracker:
                step1 = tracker.start_step(
                    "Entity Collection Query",
                    "ENTITY_FIRST",
                    collection
                )
                # Build SQL for tracking
                entity_sql = f"SELECT * FROM c WHERE c.normalized_name = '{entity_info.get('value')}'"

            # Get entity document
            entity_doc = await self.nosql_svc.get_entity_document(
                collection, entity_info.get("value")
            )

            if not entity_doc:
                logging.warning(f"Entity not found: {entity_info}")
                if tracker and step1:
                    tracker.complete_step(
                        step1, ExecutionStatus.FAILED,
                        ru_cost=1.0, docs_found=0,
                        error="Entity not found",
                        metadata={'key': entity_info.get("value"), 'sql': entity_sql}
                    )
                return []

            # Get contract IDs from entity
            contract_ids = entity_doc.get("contracts", [])

            if tracker and step1:
                tracker.complete_step(
                    step1, ExecutionStatus.SUCCESS,
                    ru_cost=1.0, docs_found=1,
                    metadata={
                        'key': entity_info.get("value"),
                        'contract_count': len(contract_ids),
                        'sql': entity_sql
                    }
                )

            if not contract_ids:
                logging.info(f"No contracts found for entity: {entity_info.get('display_name')}")
                return []

            # Track Step 2: Batch Contract Retrieval
            step2 = None
            if tracker:
                step2 = tracker.start_step(
                    "Batch Contract Retrieval",
                    "ENTITY_FIRST",
                    "contracts"
                )

            # Batch retrieve contracts
            contracts = await self.nosql_svc.batch_get_contracts(contract_ids, max_count)

            if tracker and step2:
                tracker.complete_step(
                    step2, ExecutionStatus.SUCCESS,
                    ru_cost=len(contracts) * 1.0,
                    docs_found=len(contracts),
                    metadata={'method': 'Batch Read', 'ids': contract_ids[:5]}
                )

            logging.info(f"Entity-first query returned {len(contracts)} contracts")
            return contracts

        except Exception as e:
            logging.error(f"Error in entity-first query: {str(e)}")
            if tracker and step1:
                tracker.complete_step(step1, ExecutionStatus.FAILED, error=str(e))
            return []
    
    async def _handle_aggregation_query(self, optimal_path: dict, tracker=None) -> dict:
        """Handle aggregation query using entity statistics"""
        step = None
        try:
            entity_info = optimal_path.get("entity_info", {})
            collection = optimal_path.get("collection")
            agg_type = optimal_path.get("aggregation_type", "count")

            if not entity_info or not collection:
                return {}

            # Track aggregation query
            if tracker:
                step = tracker.start_step(
                    "Entity Aggregate Query",
                    "ENTITY_AGGREGATION",
                    collection
                )

            # Get aggregated statistics
            result = await self.nosql_svc.get_entity_aggregates(
                collection, entity_info.get("value"), agg_type
            )

            # Format as document for RAG
            if result:
                formatted = {
                    "id": f"aggregate_{entity_info.get('value')}",
                    "type": "aggregation",
                    "entity": entity_info.get("display_name"),
                    "aggregation_type": agg_type,
                    "value": result.get("value"),
                    "explanation": f"{entity_info.get('display_name')} has {result.get('value')} contracts"
                    if agg_type == "count" else
                    f"Total value for {entity_info.get('display_name')}: ${result.get('value'):,.2f}"
                }

                if tracker and step:
                    tracker.complete_step(
                        step, ExecutionStatus.SUCCESS,
                        ru_cost=1.0, docs_found=1,
                        metadata={
                            'key': entity_info.get("value"),
                            'aggregation': agg_type,
                            'value': result.get("value")
                        }
                    )

                return formatted

            if tracker and step:
                tracker.complete_step(
                    step, ExecutionStatus.FAILED,
                    ru_cost=1.0, docs_found=0,
                    error="No aggregates found"
                )

            return {}

        except Exception as e:
            logging.error(f"Error in aggregation query: {str(e)}")
            if tracker and step:
                tracker.complete_step(step, ExecutionStatus.FAILED, error=str(e))
            return {}

    # def _parse_sparql_rag_query_results(self, sparql_query_results):
    #     libtype_name_pairs = list()
    #     try:
    #         result_rows = sparql_query_results["results"]["results"]
    #         logging.warning(
    #             "sparql rag query result_rows count: {}".format(len(result_rows))
    #         )
    #         for result in result_rows:
    #             attr_key = sorted(result.keys())[0]
    #             value = result[attr_key]
    #             tokens = value.split("/")
    #             if len(tokens) == 0:
    #                 libtype_name = value
    #             else:
    #                 last_idx = len(tokens) - 1
    #                 libtype_name = tokens[last_idx]
    #             pair = libtype_name.split("_")
    #             if len(pair) == 2:
    #                 libtype_name_pairs.append(pair)
    #             else:
    #                 libtype_name_pairs.append(["pypi", libtype_name])
    #     except Exception as e:
    #         logging.critical(
    #             "Exception in RagDataService#_parse_sparql_rag_query_results: {}".format(
    #                 str(e)
    #             )
    #         )
    #         logging.exception(e, stack_info=True, exc_info=True)
    #     return libtype_name_pairs
