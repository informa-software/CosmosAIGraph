import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum


class QueryStrategy(Enum):
    """Enumeration of query strategies"""
    ENTITY_FIRST = "entity_first"  # Query entity collection first, then get contracts
    CONTRACT_DIRECT = "contract_direct"  # Query contracts collection directly
    ENTITY_AGGREGATION = "entity_aggregation"  # Use entity collection for aggregates
    GRAPH_TRAVERSAL = "graph_traversal"  # Use graph for relationship queries


class QueryOptimizer:
    """
    Determines the optimal data retrieval path for contract queries
    by analyzing query patterns, entity selectivity, and collection characteristics.
    """
    
    # Collection schema definitions
    COLLECTION_SCHEMAS = {
        "contracts": {
            "primary_key": "id",
            "entity_fields": {
                "governing_law_state": "governing_law_states",
                "contractor_party": "contractor_parties",
                "contracting_party": "contracting_parties",
                "contract_type": "contract_types"
            },
            "indexed_fields": ["id", "governing_law_state", "contractor_party", 
                             "contracting_party", "contract_type", "effective_date"],
            "has_embeddings": True
        },
        "governing_law_states": {
            "primary_key": "normalized_name",
            "contract_list_field": "contracts",
            "stats_fields": ["contract_count", "total_value"],
            "indexed_fields": ["normalized_name", "display_name"]
        },
        "contractor_parties": {
            "primary_key": "normalized_name",
            "contract_list_field": "contracts",
            "stats_fields": ["contract_count", "total_value"],
            "indexed_fields": ["normalized_name", "display_name"]
        },
        "contracting_parties": {
            "primary_key": "normalized_name",
            "contract_list_field": "contracts",
            "stats_fields": ["contract_count", "total_value"],
            "indexed_fields": ["normalized_name", "display_name"]
        },
        "contract_types": {
            "primary_key": "normalized_name",
            "contract_list_field": "contracts",
            "stats_fields": ["contract_count", "total_value"],
            "indexed_fields": ["normalized_name", "display_name"]
        },
        "contract_chunks": {
            "primary_key": "id",
            "parent_field": "parent_id",
            "indexed_fields": ["id", "parent_id"],
            "has_embeddings": True
        },
        "contract_clauses": {
            "primary_key": "id",
            "parent_field": "contract_id",
            "clause_type_field": "clause_type",
            "indexed_fields": ["id", "contract_id", "clause_type"],
            "has_embeddings": True
        }
    }
    
    # Query patterns that benefit from entity-first approach
    ENTITY_FIRST_PATTERNS = [
        "all contracts",
        "list of contracts",
        "contracts for",
        "contracts by",
        "governed by",
        "performed by",
        "initiated by"
    ]
    
    # Aggregation patterns
    AGGREGATION_PATTERNS = [
        "how many",
        "count",
        "total",
        "sum",
        "average",
        "number of"
    ]
    
    def __init__(self, strategy_obj: Dict):
        """
        Initialize the optimizer with a strategy object from ContractStrategyBuilder
        
        Args:
            strategy_obj: Strategy dictionary containing entities and query metadata
        """
        self.strategy = strategy_obj
        self.natural_language = strategy_obj.get("natural_language", "").lower()
        self.entities = strategy_obj.get("entities", {})
        self.query_strategy = strategy_obj.get("strategy", "")  # db, vector, or graph
        
    def determine_optimal_path(self) -> Dict:
        """
        Determine the optimal collection and retrieval strategy
        
        Returns:
            Dictionary containing:
            - collection: Primary collection to query
            - strategy: QueryStrategy enum value
            - entity_info: Entity details if using entity-first
            - filter: Query filter if using direct query
            - explanation: Human-readable explanation of choice
        """
        # Check for aggregation queries first
        if self._is_aggregation_query():
            return self._build_aggregation_path()
        
        # Check if this is a single-entity query
        if self._is_single_entity_query():
            return self._build_entity_first_path()
        
        # Check if this is a multi-filter query
        if self._is_multi_filter_query():
            return self._build_contract_direct_path()
        
        # Check for relationship queries (graph)
        if self._is_relationship_query():
            return self._build_graph_traversal_path()
        
        # Default to contract direct query
        return self._build_default_path()
    
    def _is_aggregation_query(self) -> bool:
        """Check if query is asking for aggregated data"""
        return any(pattern in self.natural_language for pattern in self.AGGREGATION_PATTERNS)
    
    def _is_single_entity_query(self) -> bool:
        """
        Check if query is focused on a single entity with high selectivity

        Note: ENTITY_FIRST requires at least one positive entity to look up.
        Queries with ONLY negations should use CONTRACT_DIRECT instead.
        """
        # Count total POSITIVE entities identified
        entity_count = sum([
            len(self.entities.get("contractor_parties", [])),
            len(self.entities.get("contracting_parties", [])),
            len(self.entities.get("governing_law_states", [])),
            len(self.entities.get("contract_types", []))
        ])

        # ENTITY_FIRST requires at least one positive entity
        # (Cannot do entity-first lookup with only negations)
        if entity_count == 0:
            return False

        # Single entity queries are optimal for entity-first approach
        if entity_count == 1:
            # Check for entity-first patterns
            return any(pattern in self.natural_language for pattern in self.ENTITY_FIRST_PATTERNS)

        return False
    
    def _is_multi_filter_query(self) -> bool:
        """
        Check if query has multiple filter criteria.

        Counts both positive entities and negations as filters.
        Returns True if there are multiple filters OR if there are any filters
        (including negation-only queries).
        """
        # Count different entity types (positive)
        entity_types = 0
        if self.entities.get("contractor_parties"):
            entity_types += 1
        if self.entities.get("contracting_parties"):
            entity_types += 1
        if self.entities.get("governing_law_states"):
            entity_types += 1
        if self.entities.get("contract_types"):
            entity_types += 1

        # Count negations
        negations = self.strategy.get("negations", {})
        negation_types = 0
        if negations.get("contractor_parties"):
            negation_types += 1
        if negations.get("contracting_parties"):
            negation_types += 1
        if negations.get("governing_law_states"):
            negation_types += 1
        if negations.get("contract_types"):
            negation_types += 1

        # Multi-filter if:
        # 1. Multiple positive entities, OR
        # 2. Mix of positive and negative, OR
        # 3. Single negation (needs direct query, not entity-first)
        total_filters = entity_types + negation_types
        return total_filters > 1 or (total_filters == 1 and negation_types == 1)
    
    def _is_relationship_query(self) -> bool:
        """Check if query is asking about relationships between entities"""
        relationship_keywords = ["between", "relationship", "connected", "related", "involving"]
        return any(keyword in self.natural_language for keyword in relationship_keywords)
    
    def _get_primary_entity(self) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Get the primary entity from the identified entities
        
        Returns:
            Tuple of (entity_type, entity_details)
        """
        # Priority order for entity types
        priority = ["governing_law_states", "contract_types", "contracting_parties", "contractor_parties"]
        
        for entity_type in priority:
            entities = self.entities.get(entity_type, [])
            if entities:
                # Return the highest confidence entity
                best_entity = max(entities, key=lambda x: x.get("confidence", 0))
                return entity_type, best_entity
        
        return None, None
    
    def _build_aggregation_path(self) -> Dict:
        """Build query path for aggregation queries"""
        entity_type, entity = self._get_primary_entity()
        
        if entity_type and entity:
            collection = self._get_entity_collection_name(entity_type)
            return {
                "collection": collection,
                "strategy": QueryStrategy.ENTITY_AGGREGATION,
                "entity_info": {
                    "type": entity_type,
                    "value": entity.get("normalized_name"),
                    "display_name": entity.get("display_name")
                },
                "aggregation_type": self._identify_aggregation_type(),
                "explanation": f"Using {collection} collection for aggregation query on {entity.get('display_name')}"
            }
        
        # Fallback to contract collection for aggregation
        return {
            "collection": "contracts",
            "strategy": QueryStrategy.CONTRACT_DIRECT,
            "filter": self._build_composite_filter(),
            "aggregation_type": self._identify_aggregation_type(),
            "explanation": "Using contracts collection for multi-entity aggregation"
        }
    
    def _build_entity_first_path(self) -> Dict:
        """Build query path for single-entity queries"""
        entity_type, entity = self._get_primary_entity()
        
        if entity_type and entity:
            collection = self._get_entity_collection_name(entity_type)
            return {
                "collection": collection,
                "strategy": QueryStrategy.ENTITY_FIRST,
                "entity_info": {
                    "type": entity_type,
                    "value": entity.get("normalized_name"),
                    "display_name": entity.get("display_name"),
                    "field_in_contract": self._get_contract_field_name(entity_type)
                },
                "explanation": f"Query {collection} collection first for {entity.get('display_name')}, then retrieve contracts"
            }
        
        return self._build_default_path()
    
    def _build_contract_direct_path(self) -> Dict:
        """Build query path for multi-filter queries"""
        return {
            "collection": "contracts",
            "strategy": QueryStrategy.CONTRACT_DIRECT,
            "filter": self._build_composite_filter(),
            "explanation": "Direct query on contracts collection with multiple filters"
        }
    
    def _build_graph_traversal_path(self) -> Dict:
        """Build query path for relationship queries"""
        return {
            "collection": "graph",
            "strategy": QueryStrategy.GRAPH_TRAVERSAL,
            "entities": self._prepare_entities_for_graph(),
            "explanation": "Using graph traversal for relationship query"
        }
    
    def _build_default_path(self) -> Dict:
        """Build default query path"""
        return {
            "collection": "contracts",
            "strategy": QueryStrategy.CONTRACT_DIRECT,
            "filter": self._build_composite_filter() if self.entities else {},
            "explanation": "Default to contracts collection query"
        }
    
    def _get_entity_collection_name(self, entity_type: str) -> str:
        """Map entity type to collection name"""
        collection_map = {
            "contractor_parties": "contractor_parties",
            "contracting_parties": "contracting_parties",
            "governing_law_states": "governing_law_states",
            "contract_types": "contract_types"
        }
        return collection_map.get(entity_type, "contracts")
    
    def _get_contract_field_name(self, entity_type: str) -> str:
        """Get the field name in contracts collection for an entity type"""
        field_map = {
            "contractor_parties": "contractor_party",
            "contracting_parties": "contracting_party",
            "governing_law_states": "governing_law_state",
            "contract_types": "contract_type"
        }
        return field_map.get(entity_type, "")
    
    def _build_composite_filter(self) -> Dict:
        """
        Build a composite filter for multi-criteria queries.
        Handles both positive filters (entity = value) and negations (entity != value).

        Returns:
            Dictionary with field names as keys and values/negations as values.
            Negations are marked with a special structure: {"$ne": value}
        """
        filter_dict = {}

        # Add positive filters for each entity type
        for entity_type, entities in self.entities.items():
            if entities:
                field_name = self._get_contract_field_name(entity_type)
                if field_name:
                    # Use the first entity of each type
                    filter_dict[field_name] = entities[0].get("normalized_name")

        # Add negation filters
        negations = self.strategy.get("negations", {})
        for entity_type, negated_entities in negations.items():
            if negated_entities:
                field_name = self._get_contract_field_name(entity_type)
                if field_name:
                    # Mark as negation using $ne operator
                    negated_value = negated_entities[0].get("normalized_name")
                    filter_dict[field_name] = {"$ne": negated_value}
                    logging.info(f"Added negation filter: {field_name} != {negated_value}")

        return filter_dict
    
    def _identify_aggregation_type(self) -> str:
        """Identify the type of aggregation requested"""
        if "count" in self.natural_language or "how many" in self.natural_language:
            return "count"
        elif "total" in self.natural_language or "sum" in self.natural_language:
            return "sum"
        elif "average" in self.natural_language:
            return "average"
        else:
            return "count"  # Default
    
    def _prepare_entities_for_graph(self) -> List[Dict]:
        """Prepare entities for graph traversal"""
        graph_entities = []
        
        for entity_type, entities in self.entities.items():
            for entity in entities:
                graph_entities.append({
                    "type": entity_type,
                    "value": entity.get("normalized_name"),
                    "display_name": entity.get("display_name"),
                    "confidence": entity.get("confidence", 0)
                })
        
        return graph_entities
    
    def get_estimated_selectivity(self) -> float:
        """
        Estimate the selectivity of the query (0.0 to 1.0)
        Lower values mean more selective (fewer results)
        """
        # Single entity queries are highly selective
        if self._is_single_entity_query():
            return 0.1
        
        # Multi-filter queries have moderate selectivity
        if self._is_multi_filter_query():
            entity_count = len(self._build_composite_filter())
            return max(0.01, 0.5 / entity_count)
        
        # No filters means low selectivity
        return 1.0
    
    def recommend_indexes(self) -> List[str]:
        """
        Recommend indexes that would optimize this query pattern
        """
        recommendations = []
        
        filter_dict = self._build_composite_filter()
        for field in filter_dict.keys():
            if field not in self.COLLECTION_SCHEMAS["contracts"]["indexed_fields"]:
                recommendations.append(f"Consider adding index on contracts.{field}")
        
        return recommendations