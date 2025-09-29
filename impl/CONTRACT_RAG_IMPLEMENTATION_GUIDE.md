# Contract RAG Implementation Guide

## Overview
This document provides a comprehensive guide for implementing the Contract RAG (Retrieval-Augmented Generation) system with multi-container support and full preservation of the graph strategy. This guide should be used in future sessions to complete the implementation.

## Current State Analysis

### Problem Statement
The RAG Data Service is failing because:
1. `get_documents_by_name()` expects a "name" field that doesn't exist in contract documents
2. Contract data is spread across multiple containers (contracts, contract_chunks, contract_clauses)
3. The system needs to maintain full support for db, vector, and graph strategies

### Container Architecture
- **contracts**: Parent contract documents with metadata
- **contract_chunks**: Text chunks with embeddings for vector search
- **contract_clauses**: Specific clause extractions
- **contractor_parties**: Contractor entity catalog
- **contracting_parties**: Contracting entity catalog
- **governing_laws**: Governing law entity catalog
- **contract_types**: Contract type entity catalog
- **clause_types**: Clause type catalog (static reference data)

## Implementation Tasks

### Phase 1: Core Database Query Fixes

#### Task 1: Add get_documents_by_entity method to CosmosNoSQLService

**File**: `src/services/cosmos_nosql_service.py`

Add this new method:

```python
async def get_documents_by_entity(self, entity_type: str, entity_values: list, container_name: str = None):
    """
    Query documents by specific entity fields.
    
    Args:
        entity_type: Type of entity (contractor_parties, contracting_parties, etc.)
        entity_values: List of normalized entity values to search for
        container_name: Optional specific container to query
    
    Returns:
        List of documents matching the entity criteria
    """
    # Map entity types to document fields
    field_map = {
        'contractor_parties': 'contractor_party',
        'contracting_parties': 'contracting_party',
        'governing_laws': 'governing_law',
        'contract_types': 'contract_type'
    }
    
    field = field_map.get(entity_type)
    if not field:
        logging.error(f"Unknown entity type: {entity_type}")
        return []
    
    # Build quoted values for SQL query
    quoted_values = [f"'{val}'" for val in entity_values]
    
    # Set container
    if container_name:
        self.set_container(container_name)
    else:
        # Default to contracts container for entity lookups
        self.set_container("contracts")
    
    # Build and execute query
    sql = f"SELECT * FROM c WHERE c.{field} IN ({','.join(quoted_values)})"
    
    docs = []
    items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
    async for item in items_paged:
        cdf = CosmosDocFilter(item)
        docs.append(cdf.filter_out_embedding())
    
    return docs
```

#### Task 2: Update RAGDataService.get_database_rag_data

**File**: `src/services/rag_data_service.py`

Replace the existing method with:

```python
async def get_database_rag_data(
    self, user_text: str, strategy_obj: dict, rdr: RAGDataResult, max_doc_count=10
) -> None:
    rag_docs_list = list()
    try:
        logging.warning(
            f"RagDataService#get_database_rag_data, user_text: {user_text}, strategy: {strategy_obj}"
        )
        
        self.nosql_svc.set_db(ConfigService.graph_source_db())
        
        # Check if we have entity information
        if "primary_entity" in strategy_obj:
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
        
        else:
            # Fallback to old behavior if no entity detected
            logging.warning("No entity detected, falling back to vector search")
            rdr.add_strategy("vector")
            return  # Let vector search handle it
        
        # Add documents to result
        for doc in rag_docs_list[:max_doc_count]:
            doc_copy = dict(doc)
            doc_copy.pop("embedding", None)
            rdr.add_doc(doc_copy)
            
    except Exception as e:
        logging.critical(f"Exception in RagDataService#get_database_rag_data: {str(e)}")
        logging.exception(e, stack_info=True, exc_info=True)
```

### Phase 2: Enhanced Contract Strategy Builder

#### Task 3: Update ContractStrategyBuilder with Full Graph Support

**File**: `src/services/contract_strategy_builder.py`

Add these new methods and update the determine method:

```python
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
        
        # If graph strategy, enhance with graph-specific metadata
        if strategy["strategy"] == "graph":
            self.enhance_for_graph_strategy(strategy)
        
        return strategy
    
    # Identify contract entities in the query
    entities = ContractEntitiesService.identify_entities_in_text(natural_language)
    strategy["entities"] = entities
    
    # Add graph metadata to entities
    strategy["entities"] = self.enhance_entities_for_graph(entities)
    
    # Determine strategy based on identified entities and query type
    self.determine_strategy_from_entities(strategy)
    
    # If no clear strategy yet, use AI to classify
    if not strategy.get("strategy"):
        self.use_ai_classification(strategy)
    
    # Add strategy-specific configuration
    self.add_strategy_configuration(strategy)
    
    return strategy

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
```

### Phase 3: Fix Document Filtering

#### Task 4: Update CosmosDocFilter

**File**: `src/util/cosmos_doc_filter.py`

Update the filter methods to handle contract documents properly:

```python
def filter_for_rag_data(self):
    """
    Filter document for RAG data, handling both library and contract documents.
    """
    filtered = dict()
    
    if self.cosmos_doc is None:
        return filtered
    
    # Check document type
    doctype = self.cosmos_doc.get("doctype", "")
    
    if "contract" in doctype.lower():
        # Contract document filtering
        filtered_attrs = self.contract_rag_attributes()
    else:
        # Library document filtering (existing)
        filtered_attrs = self.rag_attributes()
    
    for attr in self.cosmos_doc.keys():
        if attr in filtered_attrs:
            # Handle special cases
            if attr == "chunk_text":
                filtered[attr] = self.cosmos_doc[attr][:1024]
            elif attr == "metadata":
                # Extract key metadata fields
                metadata = self.cosmos_doc[attr]
                filtered["contractor_party"] = metadata.get("ContractorPartyName", {}).get("normalizedValue", "")
                filtered["contracting_party"] = metadata.get("ContractingPartyName", {}).get("normalizedValue", "")
                filtered["effective_date"] = metadata.get("EffectiveDate", {}).get("value", "")
                filtered["contract_value"] = metadata.get("MaximumContractValue", {}).get("value", "")
            else:
                filtered[attr] = self.cosmos_doc[attr]
    
    return filtered

def contract_rag_attributes(self):
    """
    Attributes relevant for contract RAG data.
    """
    return [
        "id",
        "doctype",
        "filename",
        "contractor_party",
        "contracting_party",
        "effective_date",
        "expiration_date",
        "contract_value",
        "contract_type",
        "governing_law",
        "chunk_text",
        "metadata",
        "clause_ids",
        "chunk_ids"
    ]
```

### Phase 4: Testing

#### Test Scenarios

1. **Database Strategy Test**:
```python
# Query: "Find contracts with Westervelt"
# Expected: Direct lookup in contracts container where contracting_party = 'westervelt'
```

2. **Graph Strategy Test**:
```python
# Query: "Show all contracts between Westervelt and ABC Construction"
# Expected: SPARQL query generation with both entities
```

3. **Vector Strategy Test**:
```python
# Query: "Find contracts similar to master service agreements"
# Expected: Vector search in contract_chunks container
```

4. **Fallback Test**:
```python
# Query: "Find contracts with UnknownCompany"
# Expected: DB strategy fails, falls back to vector search
```

## Key Files to Modify

1. `src/services/cosmos_nosql_service.py` - Add entity-aware queries
2. `src/services/rag_data_service.py` - Update all three strategy methods
3. `src/services/contract_strategy_builder.py` - Add graph enhancements
4. `src/util/cosmos_doc_filter.py` - Fix field mappings
5. `web_app.py` - Ensure strategy object is passed correctly

## Testing Checklist

- [ ] Load contract data into all containers
- [ ] Initialize ContractEntitiesService with entity catalogs
- [ ] Test database strategy with known entities
- [ ] Test graph strategy with relationship queries
- [ ] Test vector strategy with similarity searches
- [ ] Test fallback mechanisms
- [ ] Verify SPARQL generation includes entity URIs
- [ ] Test multi-container aggregation
- [ ] Verify no "name" field errors occur
- [ ] Test Angular UI integration

## Success Criteria

1. All three strategies (db, vector, graph) work with contract data
2. No errors about missing "name" field
3. Graph strategy generates valid SPARQL with entity URIs
4. Entities are correctly identified and normalized
5. Cross-container queries retrieve complete data
6. Angular UI can execute queries through the backend

## Notes for Future Sessions

- This implementation preserves full graph functionality
- The ContractStrategyBuilder returns rich metadata for all strategies
- Entity URIs are generated consistently for RDF/SPARQL
- The system can fallback gracefully between strategies
- All changes are backward compatible with library mode

## Related Documents

- `CLAUDE.md` - Project setup and commands
- `CONTRACT_VECTOR_DESIGN.md` - Vector search design
- `COMPLEX_QUERY_ANALYSIS.md` - Query pattern analysis