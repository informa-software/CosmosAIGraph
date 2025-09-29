# Vector and Database Search Issues with Normalized Contract Data

## Executive Summary

The implementation of normalized entity values creates significant challenges for vector and database search strategies, particularly due to the multi-document architecture where contracts, chunks, and clauses are stored separately. This document analyzes these issues and provides a comprehensive solution approach.

## Current Architecture Analysis

### Critical Design Decision: Original Text in Chunks
**IMPORTANT**: The chunk_text and clause_text fields contain the ORIGINAL text from contracts, NOT normalized values. This is a crucial design decision that:
- **Preserves semantic meaning** for vector embeddings
- **Enables accurate vector search** with natural language queries
- **Maintains readability** in search results
- **BUT requires hybrid approach** for entity-based filtering

### Document Structure
```
contracts (container)
├── contract_parent documents
│   └── Contains normalized values at root level
│       ├── contractor_party: "westervelt"  (normalized)
│       ├── metadata.ContractorPartyName.value: "The Westervelt Company" (original)
│       └── metadata.ContractorPartyName.normalizedValue: "westervelt"

contract_chunks (container)
├── chunk documents
│   └── Mixed content: normalized metadata, original text
│       ├── contractor_party: "westervelt"  (normalized for filtering)
│       └── chunk_text: "The contract between The Westervelt Company..." (ORIGINAL text)

contract_clauses (container)
├── clause documents
│   └── Mixed content: normalized metadata, original text  
│       ├── contractor_party: "westervelt"  (normalized for filtering)
│       └── clause_text: "The Westervelt Company shall indemnify..." (ORIGINAL text)
```

### Current Search Flow
1. **Database Search**: `get_documents_by_name()` searches by exact name match
2. **Vector Search**: Embeds user query and searches in `contract_chunks` container
3. **Graph Search**: Uses SPARQL on normalized values

## Identified Issues

### Issue 1: Entity Mismatch in Database Search
**Problem**: User searches for "Westervelt Company" but database has "westervelt"
```python
# Current code in get_database_rag_data()
rag_docs_list = await self.nosql_svc.get_documents_by_name([name])
# This searches for exact match, won't find normalized values
```

**Impact**: 
- Direct database lookups will fail
- Users won't find contracts by company names they know

### Issue 2: Cross-Container Search Complexity
**Problem**: Contract data is split across three containers
- Parent contract in `contracts` container
- Chunks in `contract_chunks` container  
- Clauses in `contract_clauses` container

**Impact**:
- Vector search only searches chunks, misses parent metadata
- No aggregation of related documents
- Incomplete context for AI responses

### Issue 3: Mismatch Between Vector Content and Metadata
**Problem**: Chunks have ORIGINAL text but NORMALIZED metadata
```python
# Chunk document structure:
{
    "chunk_text": "This contract between The Westervelt Company and ABC Corporation...",  # ORIGINAL
    "contractor_party": "westervelt",  # NORMALIZED for filtering
    "contracting_party": "abc",  # NORMALIZED for filtering
    "embedding": [...]  # Generated from ORIGINAL chunk_text
}
```

**Impact**:
- Vector search works well (original text preserves semantic meaning)
- BUT filtering by normalized fields creates disconnect
- Need to handle both original text search AND normalized field filtering

### Issue 4: Missing Entity Context in Search Results
**Problem**: Search returns documents but loses entity mapping
- No way to map "westervelt" back to "The Westervelt Company"
- Display names not available in search results

### Issue 5: Incomplete Query Strategy Selection
**Problem**: `ContractStrategyBuilder` identifies entities but doesn't use normalized forms for search
```python
# Identifies entities but doesn't normalize for search
entities = ContractEntitiesService.identify_entities_in_text(natural_language)
# But database search still uses original text
```

## Comprehensive Solution Approach

### Solution 1: Enhanced Database Search with Entity Normalization

**Implementation**:
```python
async def get_database_rag_data(self, user_text: str, name: str, rdr: RAGDataResult, max_doc_count=10) -> None:
    """
    Enhanced database search that handles normalized entities.
    """
    try:
        # First try to identify if 'name' is an entity
        entities = ContractEntitiesService.identify_entities_in_text(user_text)
        
        # Collect all normalized names to search for
        search_names = []
        
        # Check if name matches any identified entities
        for contractor in entities.get("contractor_parties", []):
            if contractor["display_name"].lower() in user_text.lower():
                search_names.append(contractor["normalized_name"])
        
        for contracting in entities.get("contracting_parties", []):
            if contracting["display_name"].lower() in user_text.lower():
                search_names.append(contracting["normalized_name"])
        
        # If no entities found, try normalizing the name directly
        if not search_names:
            normalized = ContractEntitiesService.normalize_entity_name(name)
            search_names = [normalized, name]  # Try both
        
        # Search across multiple containers
        all_docs = []
        
        # Search parent contracts
        self.nosql_svc.set_container(ConfigService.graph_source_container())
        parent_docs = await self.search_by_normalized_entities(search_names, "contractor_party", "contracting_party")
        all_docs.extend(parent_docs)
        
        # Search chunks if needed
        if len(all_docs) < max_doc_count:
            self.nosql_svc.set_container(ConfigService.graph_vector_container())
            chunk_docs = await self.search_by_normalized_entities(search_names, "contractor_party", "contracting_party")
            all_docs.extend(chunk_docs)
        
        # Enhance documents with display names
        for doc in all_docs[:max_doc_count]:
            self.enhance_doc_with_display_names(doc)
            rdr.add_doc(doc)
            
    except Exception as e:
        logging.error(f"Error in enhanced database search: {e}")
```

### Solution 2: Multi-Container Aggregation Strategy

**Implementation**:
```python
async def aggregate_contract_documents(self, contract_id: str) -> Dict:
    """
    Aggregate all related documents for a contract.
    Returns a unified view with parent, chunks, and clauses.
    """
    result = {
        "parent": None,
        "chunks": [],
        "clauses": [],
        "display_entities": {}
    }
    
    # Get parent contract
    self.nosql_svc.set_container("contracts")
    parent = await self.nosql_svc.point_read(contract_id, "contracts")
    if parent:
        result["parent"] = parent
        # Extract display names from metadata
        metadata = parent.get("metadata", {})
        for field, data in metadata.items():
            if "value" in data and "normalizedValue" in data:
                result["display_entities"][data["normalizedValue"]] = data["value"]
    
    # Get related chunks
    self.nosql_svc.set_container("contract_chunks")
    chunks_query = f"SELECT * FROM c WHERE c.parent_id = '{contract_id}'"
    chunks = await self.nosql_svc.query_items(chunks_query)
    result["chunks"] = list(chunks)
    
    # Get related clauses
    self.nosql_svc.set_container("contract_clauses")
    clauses_query = f"SELECT * FROM c WHERE c.parent_id = '{contract_id}'"
    clauses = await self.nosql_svc.query_items(clauses_query)
    result["clauses"] = list(clauses)
    
    return result
```

### Solution 3: Enhanced Vector Search with Hybrid Filtering

**Implementation**:
```python
async def get_vector_rag_data(self, user_text, rdr: RAGDataResult = None, max_doc_count=10) -> None:
    """
    Enhanced vector search that leverages both original text and normalized metadata.
    
    KEY INSIGHT: Chunk text contains ORIGINAL entity names (good for vector search)
    while metadata fields contain NORMALIZED names (good for filtering).
    """
    try:
        # Identify entities in the query
        entities = ContractEntitiesService.identify_entities_in_text(user_text)
        
        # Create entity mapping for filtering and display
        entity_mapping = {}
        normalized_filters = []
        
        for party_type in ["contractor_parties", "contracting_parties"]:
            for party in entities.get(party_type, []):
                entity_mapping[party["normalized_name"]] = party["display_name"]
                normalized_filters.append(party["normalized_name"])
        
        # Generate embedding from ORIGINAL query text
        # This works well because chunk_text also contains ORIGINAL entity names
        embedding = self.ai_svc.generate_embeddings(user_text).data[0].embedding
        
        # Vector search finds chunks with similar ORIGINAL text
        self.nosql_svc.set_container(ConfigService.graph_vector_container())
        vs_results = await self.nosql_svc.vector_search(
            embedding_value=embedding,
            search_text=user_text,  # Original text for semantic search
            search_method="rrf",
            embedding_attr="embedding",
            limit=max_doc_count * 2  # Get extra for post-filtering
        )
        
        # Optional: Post-filter by normalized metadata fields if entities were identified
        if normalized_filters:
            filtered_results = []
            for chunk in vs_results:
                # Check if chunk's normalized fields match any identified entities
                contractor = chunk.get("contractor_party", "")
                contracting = chunk.get("contracting_party", "")
                
                if contractor in normalized_filters or contracting in normalized_filters:
                    # Priority results that match identified entities
                    filtered_results.insert(0, chunk)
                else:
                    filtered_results.append(chunk)
            
            vs_results = filtered_results
        
        # Enhance results with parent metadata
        enhanced_results = []
        parent_cache = {}
        
        for chunk in vs_results:
            parent_id = chunk.get("parent_id")
            
            # Get parent if not cached
            if parent_id and parent_id not in parent_cache:
                self.nosql_svc.set_container("contracts")
                parent = await self.nosql_svc.point_read(parent_id, "contracts")
                parent_cache[parent_id] = parent
            
            # Enhance chunk with display names
            if parent_id in parent_cache:
                parent = parent_cache[parent_id]
                metadata = parent.get("metadata", {})
                
                # Add display names to chunk
                chunk["display_entities"] = {}
                for field, data in metadata.items():
                    if "normalizedValue" in data:
                        chunk["display_entities"][data["normalizedValue"]] = data["value"]
            
            # Add entity mapping from query
            chunk["query_entities"] = entity_mapping
            enhanced_results.append(chunk)
        
        # Add to RAG result
        for doc in enhanced_results[:max_doc_count]:
            doc.pop("embedding", None)
            rdr.add_doc(doc)
            
    except Exception as e:
        logging.error(f"Error in enhanced vector search: {e}")
```

### Solution 4: Query Preprocessing Service

**Implementation**:
```python
class QueryPreprocessor:
    """
    Preprocesses queries to handle normalized entities.
    """
    
    @staticmethod
    def prepare_for_search(query: str) -> Dict:
        """
        Prepare query for different search strategies.
        """
        # Identify entities
        entities = ContractEntitiesService.identify_entities_in_text(query)
        
        # Create search variations
        search_terms = {
            "original": query,
            "normalized_entities": [],
            "display_entities": [],
            "entity_mapping": {}
        }
        
        # Extract all entity forms
        for entity_type in ["contractor_parties", "contracting_parties", 
                           "governing_laws", "contract_types"]:
            for entity in entities.get(entity_type, []):
                normalized = entity.get("normalized_name", "")
                display = entity.get("display_name", "")
                
                if normalized:
                    search_terms["normalized_entities"].append(normalized)
                if display:
                    search_terms["display_entities"].append(display)
                if normalized and display:
                    search_terms["entity_mapping"][normalized] = display
        
        # Create modified query with normalized terms
        modified_query = query
        for norm, disp in search_terms["entity_mapping"].items():
            # Replace display names with normalized in query
            modified_query = modified_query.replace(disp, f"[{norm}]")
        
        search_terms["modified_query"] = modified_query
        
        return search_terms
```

### Solution 5: Unified Search Interface

**Implementation**:
```python
async def unified_contract_search(self, query: str, strategy: str = "auto") -> List[Dict]:
    """
    Unified search across all contract documents with entity normalization.
    """
    # Preprocess query
    search_terms = QueryPreprocessor.prepare_for_search(query)
    
    results = []
    
    if strategy in ["auto", "db"]:
        # Database search with normalized entities
        db_results = await self.search_contracts_by_entities(
            search_terms["normalized_entities"],
            search_terms["entity_mapping"]
        )
        results.extend(db_results)
    
    if strategy in ["auto", "vector"] and len(results) < 10:
        # Vector search with enhancement
        vector_results = await self.enhanced_vector_search(
            query,
            search_terms["entity_mapping"]
        )
        results.extend(vector_results)
    
    if strategy in ["auto", "graph"] and len(results) < 10:
        # Graph search with normalized query
        graph_results = await self.graph_search_with_normalization(
            search_terms["modified_query"],
            search_terms["entity_mapping"]
        )
        results.extend(graph_results)
    
    # Deduplicate and rank results
    results = self.deduplicate_and_rank(results)
    
    # Enhance all results with display names
    for result in results:
        self.enhance_with_display_names(result, search_terms["entity_mapping"])
    
    return results
```

### Solution 6: Result Enhancement Service

**Implementation**:
```python
class ResultEnhancer:
    """
    Enhances search results with display names and context.
    NOTE: chunk_text already contains ORIGINAL entity names, no replacement needed.
    """
    
    @staticmethod
    def enhance_document(doc: Dict, entity_mapping: Dict) -> Dict:
        """
        Enhance a document with display names for normalized fields.
        """
        enhanced = doc.copy()
        
        # Add display names for normalized metadata fields
        if "contractor_party" in doc:
            normalized = doc["contractor_party"]
            display = entity_mapping.get(normalized, normalized)
            enhanced["contractor_party_display"] = display
        
        if "contracting_party" in doc:
            normalized = doc["contracting_party"]
            display = entity_mapping.get(normalized, normalized)
            enhanced["contracting_party_display"] = display
        
        # chunk_text already has ORIGINAL names - no replacement needed!
        # Just mark it for clarity
        if "chunk_text" in doc:
            enhanced["text_contains_original_names"] = True
            enhanced["display_text"] = doc["chunk_text"]  # Already readable
        
        # Add metadata to show the mapping
        enhanced["entity_mapping"] = entity_mapping
        
        return enhanced
```

## Implementation Phases

### Phase 1: Immediate Fixes (1-2 days)
1. **Update QueryPreprocessor** to identify and normalize entities
2. **Enhance database search** to use normalized values
3. **Add entity mapping** to search results

### Phase 2: Core Improvements (3-5 days)
1. **Implement multi-container aggregation**
2. **Enhance vector search** with parent metadata
3. **Create result enhancement service**

### Phase 3: Advanced Features (1 week)
1. **Unified search interface** across all strategies
2. **Intelligent result ranking** based on entity matches
3. **Caching layer** for entity mappings

## Configuration Updates Required

### Environment Variables
```bash
# Add new configuration for search behavior
CAIG_SEARCH_USE_NORMALIZED=true
CAIG_SEARCH_AGGREGATE_CONTAINERS=true
CAIG_SEARCH_ENHANCE_RESULTS=true
```

### Container Index Policies
- Add composite indexes on normalized fields
- Ensure vector indexes support normalized values
- Add full-text indexes where needed

## Testing Strategy

### Test Cases
```python
test_scenarios = [
    {
        "query": "Find contracts with Westervelt Company",
        "expected_normalized": "westervelt",
        "expected_strategy": "db",
        "expected_results": ["contract_123"]
    },
    {
        "query": "Show indemnification clauses for Alabama contracts",
        "expected_normalized": "alabama",
        "expected_strategy": "vector",
        "expected_containers": ["contract_clauses", "contracts"]
    },
    {
        "query": "Contracts between ABC Corp and XYZ Inc",
        "expected_normalized": ["abc", "xyz_inc"],
        "expected_strategy": "graph",
        "expected_aggregation": true
    }
]
```

## Performance Considerations

### Optimization Strategies
1. **Cache entity mappings** in memory
2. **Batch container queries** where possible
3. **Use projection queries** to reduce data transfer
4. **Implement result pagination** for large datasets

### Expected Performance Impact
- Initial query: +100-200ms for entity identification
- Multi-container search: +50-100ms per additional container
- Result enhancement: +20-50ms for display name mapping
- Overall: ~300-400ms total overhead, acceptable for improved accuracy

## Key Architectural Insights

### The Hybrid Data Model
The system uses a **hybrid approach** that combines the best of both worlds:

1. **Text Fields (chunk_text, clause_text)**: Contain ORIGINAL entity names
   - Preserves semantic meaning for vector search
   - Maintains readability in results
   - Enables natural language queries to work effectively

2. **Metadata Fields (contractor_party, contracting_party)**: Contain NORMALIZED values
   - Enables consistent filtering and grouping
   - Supports exact match queries
   - Facilitates entity-based aggregation

### Search Strategy Implications

| Search Type | Uses | Works Well Because |
|------------|------|-------------------|
| **Vector Search** | Original text in chunks | Embeddings preserve semantic meaning of "The Westervelt Company" |
| **Database Search** | Normalized metadata | Can find all variations of "Westervelt" consistently |
| **Graph Search** | Normalized values | SPARQL queries use consistent entity names |
| **Hybrid Search** | Both | Can leverage semantic similarity AND entity filtering |

## Conclusion

The normalization of entity values combined with preserving original text in chunks creates a powerful hybrid system. The proposed solutions leverage this architecture to:

1. **Maintain vector search accuracy** through original text in embeddings
2. **Enable consistent filtering** through normalized metadata fields
3. **Aggregate related documents** across containers using normalized keys
4. **Preserve readability** by keeping original text in chunk_text
5. **Support flexible searching** across all strategies

The critical insight is that **chunk_text contains original entity names**, which means:
- Vector search works naturally with user queries
- No need to replace entity names in chunk text
- Focus on mapping normalized metadata fields to display names
- Leverage both original and normalized data for optimal search

The phased implementation approach ensures immediate improvements while building toward a robust, unified search system that handles the hybrid data model seamlessly.