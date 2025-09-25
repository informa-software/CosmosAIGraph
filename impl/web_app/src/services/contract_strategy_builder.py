import asyncio
import logging
from typing import Dict, Optional

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
            "confidence": 0.0
        }
        
        # First, check for simple known patterns
        self.check_for_contract_patterns(strategy)
        if strategy.get("strategy"):
            logging.info(f"ContractStrategyBuilder - pattern match: {strategy}")
            return strategy
        
        # Identify contract entities in the query
        entities = ContractEntitiesService.identify_entities_in_text(natural_language)
        strategy["entities"] = entities
        
        # Determine strategy based on identified entities and query type
        self.determine_strategy_from_entities(strategy)
        
        # If no clear strategy yet, use AI to classify
        if not strategy.get("strategy"):
            self.use_ai_classification(strategy)
        
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