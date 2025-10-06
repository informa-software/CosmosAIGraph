import asyncio
import logging
import re
from typing import Dict, Optional, List

from src.services.ai_service import AiService
from src.services.contract_entities_service import ContractEntitiesService
from src.services.config_service import ConfigService
from src.services.query_optimizer import QueryOptimizer, QueryStrategy
from src.services.llm_query_planner import LLMQueryPlanner, LLMQueryPlan
from src.services.sql_validator import SQLValidator
from src.services.sparql_validator import SPARQLValidator

# Contract-specific strategy builder that determines the intent of user queries
# related to contracts and identifies the appropriate data retrieval strategy.
#
# This extends the base StrategyBuilder concept for contract-specific queries.
#
# TODO: Implement more sophisticated matching algorithms:
# - Use NER (Named Entity Recognition) for better entity extraction
# - Implement semantic similarity for query understanding
# - Add query pattern templates for common contract queries
# - Consider using a small classification model for intent detection
#
# David Ambrose & Chris Joakim, Microsoft, 2025


class ContractStrategyBuilder:
    """
    Determines the strategy for contract-related queries by analyzing
    natural language and identifying contract entities.
    """
    
    def __init__(self, ai_svc: AiService):
        self.ai_svc = ai_svc

        # LLM query planner for parallel analysis (Phase 1)
        self.llm_planner: Optional[LLMQueryPlanner] = None
        self.sql_validator = SQLValidator()
        self.sparql_validator = SPARQLValidator()

        # Check if LLM strategy is enabled
        self.use_llm_strategy = ConfigService.envvar("CAIG_USE_LLM_STRATEGY", "false").lower() == "true"

        # Check execution mode: comparison_only (Phase 1/2), execution (Phase 3), a_b_test
        self.llm_execution_mode = ConfigService.envvar("CAIG_LLM_EXECUTION_MODE", "comparison_only").lower()

        # Validate execution mode
        valid_modes = ["comparison_only", "execution", "a_b_test"]
        if self.llm_execution_mode not in valid_modes:
            logging.warning(f"Invalid CAIG_LLM_EXECUTION_MODE: {self.llm_execution_mode}. Using 'comparison_only'.")
            self.llm_execution_mode = "comparison_only"

        if self.use_llm_strategy:
            try:
                self.llm_planner = LLMQueryPlanner()
                if self.llm_execution_mode == "comparison_only":
                    logging.info("LLM query planning enabled for parallel analysis (comparison only)")
                elif self.llm_execution_mode == "execution":
                    logging.info("LLM query EXECUTION enabled - using LLM-generated queries")
                elif self.llm_execution_mode == "a_b_test":
                    logging.info("LLM A/B testing enabled - 50/50 split between LLM and rule-based")
            except Exception as e:
                logging.warning(f"Failed to initialize LLM query planner: {e}. Using rule-based only.")
                self.use_llm_strategy = False
                self.llm_execution_mode = "comparison_only"
    
    def determine(self, natural_language: str) -> Dict:
        """
        Determine the strategy for retrieving contract data based on the query.
        Returns a strategy dictionary with identified entities and approach.

        Phase 1: Runs LLM planning in parallel with rule-based approach for comparison.
        The rule-based path still executes queries; LLM results are logged for analysis.
        """
        strategy = {
            "natural_language": natural_language,
            "strategy": "",  # db, vector, or graph
            "entities": {},  # Identified contract entities
            "negations": {},  # Negated entities (e.g., "NOT Alabama")
            "algorithm": "",  # How the strategy was determined
            "confidence": 0.0,
            "name": "",  # For compatibility with existing code
            "llm_plan": None  # LLM query plan (if enabled)
        }

        # Run LLM planning in parallel (Phase 1 - comparison only, no execution)
        if self.use_llm_strategy and self.llm_planner:
            try:
                llm_plan = self.llm_planner.plan_query(natural_language, timeout=10.0)

                # Validate generated query
                is_valid_query, validation_msg = self._validate_llm_query(llm_plan)

                if is_valid_query:
                    strategy["llm_plan"] = {
                        "strategy": llm_plan.strategy,
                        "fallback_strategy": llm_plan.fallback_strategy,
                        "query_type": llm_plan.query_type,
                        "query_text": llm_plan.query_text,
                        "execution_plan": llm_plan.execution_plan,
                        "confidence": llm_plan.confidence,
                        "reasoning": llm_plan.reasoning,
                        "validation_status": "valid"
                    }
                    logging.info(f"LLM Plan: strategy={llm_plan.strategy}, "
                               f"query_type={llm_plan.query_type}, "
                               f"confidence={llm_plan.confidence:.2f}")
                else:
                    strategy["llm_plan"] = {
                        "validation_status": "invalid",
                        "validation_error": validation_msg
                    }
                    logging.warning(f"LLM query validation failed: {validation_msg}")

            except Exception as e:
                logging.error(f"LLM query planning failed: {e}")
                strategy["llm_plan"] = {
                    "validation_status": "error",
                    "error": str(e)
                }

        # FIRST: Detect negation patterns before entity extraction
        self.detect_negation_patterns(strategy)

        # SECOND: Identify contract entities in the query (after negation detection)
        entities = ContractEntitiesService.identify_entities_in_text(natural_language)
        strategy["entities"] = entities

        # THIRD: Remove negated entities from positive entities
        # (If "Alabama" is in negations, remove it from positive entities)
        self._remove_negated_from_positive_entities(strategy)

        # Add graph metadata to entities
        strategy["entities"] = self.enhance_entities_for_graph(strategy["entities"])
        
        # Log identified entities for debugging
        if entities:
            logging.info(f"ContractStrategyBuilder - identified entities: {entities}")
        
        # SECOND: Check for simple known patterns
        self.check_for_contract_patterns(strategy)
        if strategy.get("strategy"):
            logging.info(f"ContractStrategyBuilder - pattern match: {strategy}")
            
            # If graph strategy, enhance with graph-specific metadata
            if strategy["strategy"] == "graph":
                self.enhance_for_graph_strategy(strategy)
            
            # Add strategy-specific configuration before returning
            self.add_strategy_configuration(strategy)
            
            return strategy
        
        # THIRD: Determine strategy based on identified entities and query type
        self.determine_strategy_from_entities(strategy)
        
        # FOURTH: If no clear strategy yet, use AI to classify
        if not strategy.get("strategy"):
            self.use_ai_classification(strategy)
        
        # FINALLY: Add strategy-specific configuration
        self.add_strategy_configuration(strategy)

        # Log LLM vs rule-based comparison (Phase 1 - analysis only)
        if self.use_llm_strategy:
            self._log_llm_comparison(strategy)

        return strategy

    def detect_negation_patterns(self, strategy: Dict):
        """
        Detect negation patterns in the query text.

        Handles patterns like:
        - "not governed by Alabama"
        - "excluding California"
        - "except for Florida"
        - "other than Texas"
        - "without Washington"

        Stores negated entities separately from positive entities.
        """
        nl = strategy["natural_language"].lower()

        # Negation patterns with their preceding words
        negation_patterns = [
            (r'(?:not|n\'t)\s+(?:governed\s+by|with|from|in)\s+(\w+(?:\s+\w+)*)', 'governing_law_states'),
            (r'(?:excluding|except\s+for|other\s+than|without)\s+(\w+(?:\s+\w+)*)', None),  # General
            (r'(?:not|exclude)\s+(\w+(?:\s+\w+)*?)(?:\s+contracts?|\s*$)', None),  # "not Alabama" or "exclude Alabama"
        ]

        negations = {
            "contractor_parties": [],
            "contracting_parties": [],
            "governing_law_states": [],
            "contract_types": []
        }

        for pattern, entity_type_hint in negation_patterns:
            matches = re.finditer(pattern, nl, re.IGNORECASE)
            for match in matches:
                negated_value = match.group(1).strip()

                # Try to identify which entity type this is
                entity_type = self._identify_negated_entity_type(negated_value, entity_type_hint)

                if entity_type and negated_value:
                    # Normalize the value
                    normalized_value = self._normalize_entity_value(negated_value)

                    negations[entity_type].append({
                        "normalized_name": normalized_value,
                        "display_name": negated_value,
                        "confidence": 0.9,
                        "match_type": "negation_pattern"
                    })

                    logging.info(f"Detected negation: NOT {entity_type} = {negated_value}")

        strategy["negations"] = negations

    def _identify_negated_entity_type(self, value: str, hint: Optional[str] = None) -> Optional[str]:
        """
        Identify what type of entity is being negated.
        """
        # If we have a hint from the pattern, use it
        if hint:
            return hint

        value_lower = value.lower()

        # Check if it's a known governing law state
        if ContractEntitiesService.static_governing_law_states:
            if any(value_lower in state_name.lower() or state_name.lower() in value_lower
                   for state_name in ContractEntitiesService.static_governing_law_states.keys()):
                return "governing_law_states"

        # Check if it's a known contract type
        if ContractEntitiesService.static_contract_types:
            if any(value_lower in ct.lower() or ct.lower() in value_lower
                   for ct in ContractEntitiesService.static_contract_types.keys()):
                return "contract_types"

        # Check if it's a known contractor/contracting party
        if ContractEntitiesService.static_contractor_parties:
            if any(value_lower in company.lower() or company.lower() in value_lower
                   for company in ContractEntitiesService.static_contractor_parties.keys()):
                return "contractor_parties"

        if ContractEntitiesService.static_contracting_parties:
            if any(value_lower in company.lower() or company.lower() in value_lower
                   for company in ContractEntitiesService.static_contracting_parties.keys()):
                return "contracting_parties"

        # Default to governing_law_states for state names (common case)
        us_states = ['alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
                     'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
                     'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
                     'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
                     'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
                     'new hampshire', 'new jersey', 'new mexico', 'new york',
                     'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
                     'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
                     'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
                     'west virginia', 'wisconsin', 'wyoming']

        if value_lower in us_states:
            return "governing_law_states"

        return None

    def _normalize_entity_value(self, value: str) -> str:
        """Normalize entity value for storage/comparison"""
        return value.lower().replace(' ', '_').replace('-', '_')

    def _remove_negated_from_positive_entities(self, strategy: Dict):
        """
        Remove entities that appear in negations from the positive entities list.

        If "Alabama" is detected as both a positive entity and a negation,
        keep it only in negations (remove from positive entities).
        """
        negations = strategy.get("negations", {})
        entities = strategy.get("entities", {})

        # Build set of normalized negated values for quick lookup
        negated_values = set()
        for entity_type, negated_list in negations.items():
            for negated_entity in negated_list:
                negated_values.add(negated_entity.get("normalized_name"))

        # Remove negated entities from positive entities
        for entity_type in ["contractor_parties", "contracting_parties", "governing_law_states", "contract_types"]:
            if entity_type in entities and entities[entity_type]:
                # Filter out entities that are in the negations set
                original_count = len(entities[entity_type])
                entities[entity_type] = [
                    entity for entity in entities[entity_type]
                    if entity.get("normalized_name") not in negated_values
                ]
                removed_count = original_count - len(entities[entity_type])
                if removed_count > 0:
                    logging.info(f"Removed {removed_count} negated entities from positive {entity_type}")

    def check_for_contract_patterns(self, strategy: Dict):
        """
        Check for common contract query patterns.
        
        TODO: Expand with more sophisticated pattern matching:
        - Regular expressions for contract numbers/IDs
        - Date range patterns
        - Value/amount patterns
        - Legal clause references
        """
        nl = strategy["natural_language"].lower()
        
        # Check for specific contract ID pattern first
        contract_id_pattern = r'contract_[a-f0-9]{32}'
        contract_id_match = re.search(contract_id_pattern, nl)
        if contract_id_match:
            contract_id = contract_id_match.group()
            strategy["strategy"] = "db"
            strategy["algorithm"] = "contract_id_lookup"
            strategy["confidence"] = 1.0
            strategy["contract_id"] = contract_id
            logging.info(f"ContractStrategyBuilder - found contract ID: {contract_id}")
            return
        
        # Database lookup patterns
        db_patterns = [
            "find contract",
            "lookup contract",
            "get contract",
            "show contract",
            "retrieve contract",
            "contract details",
            "contract information",
            "specific contract"
        ]
        
        for pattern in db_patterns:
            if pattern in nl:
                strategy["strategy"] = "db"
                strategy["algorithm"] = "pattern_match"
                strategy["confidence"] = 0.9
                return
        
        # Graph traversal patterns (relationships)
        graph_patterns = [
            "contracts between",
            "relationship",
            "all contracts with",
            "contracts involving",
            "connected to",
            "contracts related",
            "contracts governed by",
            "performed by",
            "initiated by"
        ]
        
        for pattern in graph_patterns:
            if pattern in nl:
                strategy["strategy"] = "graph"
                strategy["algorithm"] = "pattern_match"
                strategy["confidence"] = 0.85
                return
        
        # Vector search patterns (similarity, open-ended)
        vector_patterns = [
            "similar to",
            "contracts like",
            "find similar",
            "contracts about",
            "relevant contracts",
            "search for",
            "contracts containing",
            "contracts mentioning"
        ]
        
        for pattern in vector_patterns:
            if pattern in nl:
                strategy["strategy"] = "vector"
                strategy["algorithm"] = "pattern_match"
                strategy["confidence"] = 0.85
                return
    
    def determine_strategy_from_entities(self, strategy: Dict):
        """
        Determine strategy based on identified entities.
        
        TODO: Enhance with:
        - Entity relationship analysis
        - Multi-entity query optimization
        - Confidence scoring based on entity match quality
        """
        entities = strategy.get("entities", {})
        nl = strategy["natural_language"].lower()
        
        # Count how many entity types were found
        entity_count = sum([
            len(entities.get("contractor_parties", [])),
            len(entities.get("contracting_parties", [])),
            len(entities.get("governing_law_States", [])),
            len(entities.get("contract_types", []))
        ])
        
        # Strong entity matches suggest database or graph queries
        if entity_count > 0:
            # Check if asking for relationships between entities
            if any(word in nl for word in ["between", "with", "involving", "related"]):
                strategy["strategy"] = "graph"
                strategy["algorithm"] = "entity_relationship"
                strategy["confidence"] = 0.8
            # Check if asking for specific contract lookup
            elif any(word in nl for word in ["find", "get", "show", "retrieve", "lookup"]):
                strategy["strategy"] = "db"
                strategy["algorithm"] = "entity_lookup"
                strategy["confidence"] = 0.85
            # Default to graph for entity queries (can traverse relationships)
            else:
                strategy["strategy"] = "graph"
                strategy["algorithm"] = "entity_graph"
                strategy["confidence"] = 0.75
        
        # Check for fuzzy matches that might need vector search
        fuzzy_matches = entities.get("fuzzy_matches", [])
        if fuzzy_matches and not strategy.get("strategy"):
            # Lower confidence fuzzy matches might benefit from vector search
            avg_confidence = sum(m["confidence"] for m in fuzzy_matches) / len(fuzzy_matches)
            if avg_confidence < 0.9:
                strategy["strategy"] = "vector"
                strategy["algorithm"] = "fuzzy_entity"
                strategy["confidence"] = avg_confidence
    
    def use_ai_classification(self, strategy: Dict):
        """
        Use AI to classify the query strategy when patterns don't match.
        
        TODO: Consider:
        - Fine-tuning a small classifier model
        - Caching AI classifications for similar queries
        - Learning from user feedback on strategy effectiveness
        """
        try:
            nl = strategy["natural_language"]
            
            system_prompt = """You are helping determine the best data source for contract queries.
            There are 3 sources:
            - 'db': Direct database lookup for specific contracts or entities
            - 'vector': Similarity search for finding related or similar contracts
            - 'graph': Relationship traversal for connected entities and contracts
            
            Classify the query with one word: db, vector, or graph.
            
            Use 'db' for: specific contract lookups, known entity searches
            Use 'vector' for: similarity searches, content-based queries, open-ended questions
            Use 'graph' for: relationship queries, multi-entity connections, contract networks"""
            
            response = self.ai_svc.get_completion(nl, system_prompt)
            
            # Normalize the response
            if response:
                response_lower = response.strip().lower()
                if "db" in response_lower or "database" in response_lower:
                    strategy["strategy"] = "db"
                elif "graph" in response_lower:
                    strategy["strategy"] = "graph"
                elif "vector" in response_lower:
                    strategy["strategy"] = "vector"
                else:
                    # Default to vector for unknown responses
                    strategy["strategy"] = "vector"
                
                strategy["algorithm"] = "ai_classification"
                strategy["confidence"] = 0.7
            else:
                # Fallback to vector search
                strategy["strategy"] = "vector"
                strategy["algorithm"] = "fallback"
                strategy["confidence"] = 0.5
                
        except Exception as e:
            logging.error(f"Error in AI classification: {str(e)}")
            # Fallback to vector search
            strategy["strategy"] = "vector"
            strategy["algorithm"] = "error_fallback"
            strategy["confidence"] = 0.5
    
    def enhance_for_graph_strategy(self, strategy: Dict):
        """
        Add graph-specific configuration when graph strategy is selected.
        """
        entities = strategy.get("entities", {})
        nl = strategy["natural_language"].lower()
        
        strategy["graph_config"] = {
            "entities_for_sparql": self.prepare_entities_for_sparql(entities),
            "relationship_type": self.identify_relationship_type(nl),
            "sparql_hints": self.generate_sparql_hints(nl, entities)
        }

    def enhance_entities_for_graph(self, entities: Dict) -> Dict:
        """
        Add graph-specific metadata to entities for SPARQL generation.
        """
        enhanced = {}
        
        for entity_type, entity_list in entities.items():
            enhanced[entity_type] = []
            for entity in entity_list:
                enhanced_entity = entity.copy()
                
                # Add RDF URI for the entity
                enhanced_entity['uri'] = self.generate_entity_uri(entity_type, entity.get('normalized_name', ''))
                
                # Add SPARQL variable name
                enhanced_entity['sparql_var'] = self.generate_sparql_variable(entity_type)
                
                # Add RDF predicates this entity can use
                enhanced_entity['predicates'] = self.get_entity_predicates(entity_type)
                
                enhanced[entity_type].append(enhanced_entity)
        
        return enhanced

    def generate_entity_uri(self, entity_type: str, normalized_name: str) -> str:
        """
        Generate RDF URI for an entity.
        """
        base_uri = "http://cosmosdb.com/caig#"
        type_map = {
            'contractor_parties': 'ContractorParty',
            'contracting_parties': 'ContractingParty',
            'governing_law_States': 'GoverningLawState',
            'contract_types': 'contract_type'
        }
 
        entity_path = type_map.get(entity_type, entity_type)
        return f"{base_uri}/{entity_path}/{normalized_name}"

    def generate_sparql_variable(self, entity_type: str) -> str:
        """
        Generate SPARQL variable name for entity type.
        """
        var_map = {
            'contractor_parties': '?contractorParty',
            'contracting_parties': '?contractingParty',
            'governing_law_states': '?governingLawState',
            'contract_types': '?contractType'
        }
        return var_map.get(entity_type, '?entity')

    def get_entity_predicates(self, entity_type: str) -> List[str]:
        """
        Get RDF predicates relevant for this entity type.
        """
        predicates = {
            'contractor_parties': [
                'performsWork',
                'hasContract',
                'providesService',
                'isContractorFor'
            ],
            'contracting_parties': [
                'initiatesContract',
                'hasContractor',
                'purchasesService',
                'isClientFor'
            ],
            'governing_law_States': [
                'governs',
                'hasJurisdiction',
                'appliesTo'
            ],
            'contract_types': [
                'hasType',
                'categorizes',
                'defines'
            ]
        }
        return predicates.get(entity_type, [])

    def generate_sparql_hints(self, natural_language: str, entities: Dict) -> Dict:
        """
        Generate hints to help AI create better SPARQL queries.
        """
        nl_lower = natural_language.lower()
        hints = {
            "use_relationships": True,
            "traverse_depth": 1,
            "include_clauses": False,
            "include_chunks": False,
            "aggregation_needed": False,
            "order_by": None,
            "limit": 10
        }
        
        # Determine traversal depth
        if "all" in nl_lower or "network" in nl_lower:
            hints["traverse_depth"] = 2
        
        # Check if clauses are needed
        if any(word in nl_lower for word in ["clause", "term", "provision", "section"]):
            hints["include_clauses"] = True
        
        # Check if aggregation is needed
        if any(word in nl_lower for word in ["count", "total", "sum", "average", "how many"]):
            hints["aggregation_needed"] = True
            
        # Check for ordering
        if "latest" in nl_lower or "recent" in nl_lower:
            hints["order_by"] = "effective_date DESC"
        elif "oldest" in nl_lower:
            hints["order_by"] = "effective_date ASC"
        elif "highest value" in nl_lower:
            hints["order_by"] = "contract_value DESC"
            
        # Include example SPARQL patterns
        hints["example_patterns"] = self.get_relevant_sparql_patterns(entities)
        
        return hints

    def get_relevant_sparql_patterns(self, entities: Dict) -> List[str]:
        """
        Provide example SPARQL patterns based on entities found.
        """
        patterns = []
        
        if entities.get("contracting_parties") and entities.get("contractor_parties"):
            patterns.append("""
        # Pattern for contracts between two parties
        ?contract a :Contract ;
                  :hasContractingParty ?contractingParty ;
                  :hasContractorParty ?contractorParty .
        FILTER(?contractingParty = <URI_HERE>)
        FILTER(?contractorParty = <URI_HERE>)
        """)
        
        if entities.get("governing_law_States"):
            patterns.append("""
        # Pattern for contracts governed by specific law
        ?contract a :Contract ;
                  :governedBy ?governingLawState .
        FILTER(?governingLawState = <URI_HERE>)
        """)
        
        return patterns

    def prepare_entities_for_sparql(self, entities: Dict) -> List[Dict]:
        """
        Prepare entities for SPARQL query generation.
        """
        sparql_entities = []
        
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                sparql_entities.append({
                    "type": entity_type,
                    "value": entity.get("normalized_name", ""),
                    "uri": entity.get("uri", ""),
                    "variable": entity.get("sparql_var", ""),
                    "display_name": entity.get("display_name", "")
                })
        
        return sparql_entities

    def identify_relationship_type(self, text: str) -> str:
        """
        Identify the type of relationship being queried.
        """
        text_lower = text.lower()
        
        if "between" in text_lower:
            return "between"
        elif "with" in text_lower:
            return "with"
        elif "involving" in text_lower:
            return "involving"
        elif "governed by" in text_lower:
            return "governed_by"
        elif "performed by" in text_lower:
            return "performed_by"
        elif "initiated by" in text_lower:
            return "initiated_by"
        else:
            return "related_to"

    def add_strategy_configuration(self, strategy: Dict):
        """
        Add strategy-specific configuration based on the selected strategy.
        Enhanced with QueryOptimizer for optimal collection selection.
        """
        # Use QueryOptimizer to determine optimal path
        optimizer = QueryOptimizer(strategy)
        optimal_path = optimizer.determine_optimal_path()
        
        # Add optimizer recommendations to strategy
        strategy["optimal_path"] = optimal_path
        strategy["query_selectivity"] = optimizer.get_estimated_selectivity()
        strategy["index_recommendations"] = optimizer.recommend_indexes()
        
        if strategy["strategy"] == "db":
            # Check for contract ID first
            if "contract_id" in strategy:
                strategy["db_config"] = {
                    "contract_id": strategy["contract_id"],
                    "container": "contracts",
                    "field": "id"
                }
                strategy["name"] = strategy["contract_id"]  # For compatibility
                strategy["primary_entity"] = None  # No entity for ID lookup
            else:
                # Add database-specific config for entity-based queries
                entities = strategy.get("entities", {})
                primary_entity = self.select_primary_entity(entities)
                
                if primary_entity:
                    strategy["primary_entity"] = primary_entity
                    strategy["name"] = primary_entity.get("display_name", "")  # For backward compatibility
                
                # Enhanced db_config with optimizer insights
                strategy["db_config"] = {
                    "primary_entity": primary_entity,
                    "container": optimal_path.get("collection", "contracts"),
                    "field": self.get_field_name(primary_entity.get("type")) if primary_entity else None,
                    "query_strategy": optimal_path.get("strategy", QueryStrategy.CONTRACT_DIRECT).value,
                    "entity_info": optimal_path.get("entity_info"),
                    "filter": optimal_path.get("filter", {})
                }
            
            # Check if we need chunks
            nl = strategy["natural_language"].lower()
            if any(word in nl for word in ["detail", "full", "complete", "text"]):
                strategy["query_config"] = {
                    "chunk_retrieval": True,
                    "containers": ["contracts", "contract_chunks"]
                }
        
        elif strategy["strategy"] == "vector":
            # Add vector-specific config
            strategy["vector_config"] = {
                "container": "contract_chunks",
                "entity_filters": self.get_entity_filters(strategy.get("entities", {}))
            }
        
        # Graph config already added in enhance_for_graph_strategy

    def select_primary_entity(self, entities: Dict) -> Dict:
        """
        Select the primary entity from identified entities based on confidence.
        """
        primary = None
        max_confidence = 0
        
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                confidence = entity.get("confidence", 0)
                if confidence > max_confidence:
                    max_confidence = confidence
                    primary = {
                        "type": entity_type,
                        "value": entity.get("normalized_name"),
                        "display_name": entity.get("display_name"),
                        "confidence": confidence
                    }
        
        return primary

    def get_field_name(self, entity_type: str) -> str:
        """
        Get the document field name for an entity type.
        """
        field_map = {
            'contractor_parties': 'contractor_party',
            'contracting_parties': 'contracting_party',
            'governing_law_States': 'governing_law_state',
            'contract_types': 'contract_type'
        }
        return field_map.get(entity_type, 'entity')

    def get_entity_filters(self, entities: Dict) -> Dict:
        """
        Get entity filters for vector search.
        """
        filters = {}
        
        for entity_type, entity_list in entities.items():
            if entity_list:
                field = self.get_field_name(entity_type)
                # Use the first entity of each type as filter
                filters[field] = entity_list[0].get("normalized_name")
        
        return filters

    @classmethod
    def is_contract_query(cls, natural_language: str) -> bool:
        """
        Determine if a query is contract-related.
        
        TODO: Enhance with:
        - Machine learning classification
        - Context from conversation history
        - Domain-specific keyword expansion
        """
        contract_keywords = [
            "contract", "agreement", "contractor", "contracting",
            "party", "parties", "clause", "governing law",
            "effective date", "expiration", "terminate", "termination",
            "obligation", "liability", "indemnif", "warranty",
            "msa", "sow", "nda", "master service", "statement of work"
        ]
        
        nl_lower = natural_language.lower()
        return any(keyword in nl_lower for keyword in contract_keywords)

    def _validate_llm_query(self, llm_plan: LLMQueryPlan) -> tuple[bool, str]:
        """
        Validate LLM-generated query for syntax and safety.

        Args:
            llm_plan: LLM query plan to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not llm_plan.query_text:
            return False, "Empty query text"

        # Validate based on query type
        if llm_plan.query_type == "SQL":
            is_valid, msg = self.sql_validator.validate(llm_plan.query_text)
            if not is_valid:
                return False, f"SQL validation failed: {msg}"

        elif llm_plan.query_type == "SPARQL":
            is_valid, msg = self.sparql_validator.validate(llm_plan.query_text)
            if not is_valid:
                return False, f"SPARQL validation failed: {msg}"

        else:
            return False, f"Unknown query type: {llm_plan.query_type}"

        # Validate strategy is known
        valid_strategies = ['ENTITY_FIRST', 'CONTRACT_DIRECT', 'ENTITY_AGGREGATION',
                           'GRAPH_TRAVERSAL', 'VECTOR_SEARCH']
        if llm_plan.strategy not in valid_strategies:
            return False, f"Invalid strategy: {llm_plan.strategy}"

        # Validate confidence threshold
        if llm_plan.confidence < 0.5:
            return False, f"Low confidence: {llm_plan.confidence:.2f} < 0.5"

        return True, "Valid"

    def _log_llm_comparison(self, strategy: Dict):
        """
        Log comparison between LLM and rule-based strategies for analysis.

        Args:
            strategy: Strategy dict with both rule-based and LLM plans
        """
        if not strategy.get("llm_plan"):
            return

        llm_plan = strategy["llm_plan"]

        if llm_plan.get("validation_status") != "valid":
            logging.info(f"LLM plan not valid for comparison: {llm_plan.get('validation_status')}")
            return

        # Map rule-based strategy to LLM strategy names
        rule_based_strategy = strategy.get("strategy", "unknown")
        llm_strategy = llm_plan.get("strategy", "unknown")

        # Log comparison
        strategies_match = (rule_based_strategy == "db" and llm_strategy == "CONTRACT_DIRECT") or \
                          (rule_based_strategy == "graph" and llm_strategy == "GRAPH_TRAVERSAL") or \
                          (rule_based_strategy == "vector" and llm_strategy == "VECTOR_SEARCH")

        logging.info(f"Strategy Comparison - Rule-Based: {rule_based_strategy}, "
                    f"LLM: {llm_strategy}, Match: {strategies_match}, "
                    f"LLM Confidence: {llm_plan.get('confidence', 0):.2f}")

        if not strategies_match:
            logging.info(f"Strategy Mismatch - LLM Reasoning: {llm_plan.get('reasoning', 'N/A')}")