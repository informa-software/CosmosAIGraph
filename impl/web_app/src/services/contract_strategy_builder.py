import asyncio
import logging
from typing import Dict, Optional, List

from src.services.ai_service import AiService
from src.services.contract_entities_service import ContractEntitiesService
from src.services.config_service import ConfigService

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
    
    def determine(self, natural_language: str) -> Dict:
        """
        Determine the strategy for retrieving contract data based on the query.
        Returns a strategy dictionary with identified entities and approach.
        """
        strategy = {
            "natural_language": natural_language,
            "strategy": "",  # db, vector, or graph
            "entities": {},  # Identified contract entities
            "algorithm": "",  # How the strategy was determined
            "confidence": 0.0,
            "name": ""  # For compatibility with existing code
        }
        
        # FIRST: Identify contract entities in the query (before pattern checking)
        entities = ContractEntitiesService.identify_entities_in_text(natural_language)
        strategy["entities"] = entities
        
        # Add graph metadata to entities
        strategy["entities"] = self.enhance_entities_for_graph(entities)
        
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
        
        return strategy
    
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
            len(entities.get("governing_laws", [])),
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
        base_uri = "http://cosmosdb.com/contract"
        type_map = {
            'contractor_parties': 'contractor_party',
            'contracting_parties': 'contracting_party',
            'governing_laws': 'governing_law',
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
            'governing_laws': '?governingLaw',
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
            'governing_laws': [
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
        
        if entities.get("governing_laws"):
            patterns.append("""
        # Pattern for contracts governed by specific law
        ?contract a :Contract ;
                  :governedBy ?governingLaw .
        FILTER(?governingLaw = <URI_HERE>)
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
        """
        if strategy["strategy"] == "db":
            # Add database-specific config
            entities = strategy.get("entities", {})
            primary_entity = self.select_primary_entity(entities)
            
            if primary_entity:
                strategy["primary_entity"] = primary_entity
                strategy["name"] = primary_entity.get("display_name", "")  # For backward compatibility
            
            strategy["db_config"] = {
                "primary_entity": primary_entity,
                "container": "contracts",
                "field": self.get_field_name(primary_entity.get("type")) if primary_entity else None
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
            'governing_laws': 'governing_law',
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