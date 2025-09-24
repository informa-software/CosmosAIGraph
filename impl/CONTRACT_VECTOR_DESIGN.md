# Contract Vector Storage and Search Design Document

## Executive Summary

This document outlines the design for extending the existing CosmosDB AI Graph system from library/developer management to comprehensive contract management. The design introduces a multi-level vector storage architecture that supports both extracted contract clauses and document chunks, enabling sophisticated semantic search and retrieval capabilities for contract analysis.

## Current State Analysis

### Existing System Architecture
- **Domain**: Software libraries and developers (PyPi packages)
- **Storage**: Single embedding vector per document
- **Search**: Vector similarity search returning full document attributes
- **RAG Pipeline**: Embeddings → Vector Search → Document Retrieval → LLM Context

### Key Components Requiring Modification
1. **Ontology Files**: `libraries.owl` → `contracts.owl`
2. **Graph Builder**: `LibrariesGraphTriplesBuilder.java` → `ContractsGraphTriplesBuilder.java`
3. **Entity Service**: `entities_service.py` modification for contract entities
4. **Vector Storage**: Single vector per document → Multi-level vector hierarchy

## Proposed Contract Management Architecture

### 1. Document Hierarchy

```
Contract (Parent Document)
├── Extracted Clauses (Structured entities with individual vectors)
│   ├── Termination Clauses
│   ├── Payment Terms
│   ├── Liability Clauses
│   └── Other Clause Types
└── Document Chunks (Raw text segments with vectors)
    ├── Chunk 1 (pages 1-2)
    ├── Chunk 2 (pages 2-3)
    └── Chunk N
```

### 2. Data Model

#### 2.1 Parent Contract Document
```json
{
  "_id": "contract_CTR2024001",
  "pk": "contracts",
  "doctype": "contract_parent",
  "contract_number": "CTR-2024-001",
  "contract_title": "Service Agreement",
  "parties": ["Party A", "Party B"],
  "contract_type": "service_agreement",
  "effective_date": "2024-01-01",
  "expiration_date": "2025-12-31",
  "total_value": 1000000,
  "status": "active",
  "clause_ids": ["clause_001", "clause_002", ...],
  "chunk_ids": ["chunk_001", "chunk_002", ...],
  "summary_embedding": [...],  // Optional overall contract summary vector
  "metadata": {
    "pdf_url": "https://storage.../contract.pdf",
    "page_count": 45,
    "extraction_date": "2024-01-15",
    "last_modified": "2024-01-15T10:30:00Z"
  }
}
```

#### 2.2 Extracted Clause Document
```json
{
  "_id": "contract_CTR2024001_clause_001",
  "pk": "contract_clauses",
  "doctype": "contract_clause",
  "parent_id": "contract_CTR2024001",
  "clause_type": "termination",
  "clause_number": "8.1",
  "clause_title": "Termination for Convenience",
  "clause_text": "Either party may terminate this agreement...",
  "embedding": [0.123, -0.456, ...],  // 1536-dimension vector
  "page_numbers": [12, 13],
  "attributes": {
    "notice_period_days": 30,
    "penalty_amount": 0,
    "requires_cause": false
  },
  "metadata": {
    "contract_number": "CTR-2024-001",
    "parties": ["Party A", "Party B"],
    "effective_date": "2024-01-01"
  }
}
```

#### 2.3 Document Chunk Document
```json
{
  "_id": "contract_CTR2024001_chunk_001",
  "pk": "contract_chunks",
  "doctype": "contract_chunk",
  "parent_id": "contract_CTR2024001",
  "chunk_index": 1,
  "chunk_text": "Full text of this section...",
  "embedding": [0.234, -0.567, ...],  // 1536-dimension vector
  "page_numbers": [1, 2],
  "section_title": "Introduction and Definitions",
  "overlapping_clause_ids": ["clause_003", "clause_004"],
  "metadata": {
    "contract_number": "CTR-2024-001",
    "parties": ["Party A", "Party B"]
  }
}
```

### 3. Ontology Design (contracts.owl)

```xml
<?xml version="1.0"?>
<rdf:RDF
  xmlns="http://cosmosdb.com/caig#"
  xmlns:owl="http://www.w3.org/2002/07/owl#"
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">

  <owl:Ontology rdf:about="">
    <rdfs:comment>Contract Management Ontology</rdfs:comment>
    <rdfs:label>Legal Contract Ontology</rdfs:label>
  </owl:Ontology>

  <!-- Classes -->
  <owl:Class rdf:ID="Contract">
    <rdfs:label>Contract</rdfs:label>
    <rdfs:comment>A legal contract or agreement</rdfs:comment>
  </owl:Class>

  <owl:Class rdf:ID="Party">
    <rdfs:label>Party</rdfs:label>
    <rdfs:comment>A party to a contract</rdfs:comment>
  </owl:Class>

  <owl:Class rdf:ID="Clause">
    <rdfs:label>Clause</rdfs:label>
    <rdfs:comment>A clause within a contract</rdfs:comment>
  </owl:Class>

  <owl:Class rdf:ID="Amendment">
    <rdfs:label>Amendment</rdfs:label>
    <rdfs:comment>An amendment to a contract</rdfs:comment>
  </owl:Class>

  <!-- Object Properties -->
  <owl:ObjectProperty rdf:ID="hasParty">
    <rdfs:domain rdf:resource="#Contract"/>
    <rdfs:range rdf:resource="#Party"/>
  </owl:ObjectProperty>

  <owl:ObjectProperty rdf:ID="containsClause">
    <rdfs:domain rdf:resource="#Contract"/>
    <rdfs:range rdf:resource="#Clause"/>
  </owl:ObjectProperty>

  <owl:ObjectProperty rdf:ID="amendedBy">
    <rdfs:domain rdf:resource="#Contract"/>
    <rdfs:range rdf:resource="#Amendment"/>
  </owl:ObjectProperty>

  <!-- Data Properties -->
  <owl:DatatypeProperty rdf:ID="contractNumber">
    <rdfs:domain rdf:resource="#Contract"/>
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string"/>
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="effectiveDate">
    <rdfs:domain rdf:resource="#Contract"/>
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#date"/>
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="expirationDate">
    <rdfs:domain rdf:resource="#Contract"/>
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#date"/>
  </owl:DatatypeProperty>
</rdf:RDF>
```

### 4. Search Architecture

#### 4.1 Search Strategy Builder Pattern
Following the existing `strategy_builder.py` pattern, implement a `ContractSearchStrategyBuilder` that intelligently determines the optimal search approach based on user intent, including graph traversal for relationship queries.

#### 4.2 Search Strategies
- **Direct Database (`db`)**: Direct lookup for known contracts, parties, or specific attributes
- **Vector Search (`vector`)**: Semantic similarity search across clauses and chunks
- **Graph Traversal (`graph`)**: Relationship queries, dependencies, and contract networks
- **Hybrid (`hybrid`)**: Combination of strategies based on query complexity

#### 4.3 Strategy Determination Algorithm
```python
class ContractSearchStrategyBuilder:
    def determine(self, query: str) -> dict:
        strategy = {
            "query": query,
            "strategy": "",  # db, vector, graph, or hybrid
            "search_mode": "",  # clause, chunk, or both (for vector)
            "target_entities": [],  # contracts, parties, clauses identified
            "operations": [],  # similarity, relationships, lookup
            "filters": {}  # dates, values, status, etc.
        }
        
        # Step 1: Quick rule-based detection
        self.check_for_simple_patterns(strategy)
        if strategy["strategy"]:
            return strategy
        
        # Step 2: LLM-based intent classification
        system_prompt = """
        Determine the data source for answering contract questions:
        - 'db': Direct lookups (specific contracts, parties, dates)
        - 'vector': Similarity searches (similar clauses, related terms)
        - 'graph': Relationship queries (contract networks, dependencies, hierarchies)
        
        Examples:
        - "Show contracts between Party A and Party B" → graph
        - "Find similar termination clauses" → vector  
        - "Get contract CTR-2024-001" → db
        - "Show all amendments to this contract" → graph
        - "Find contracts expiring this month" → db
        
        Classify with one word: db, vector, or graph.
        """
        
        # Step 3: Determine search scope for vector searches
        if strategy["strategy"] == "vector":
            strategy["search_mode"] = self.determine_search_mode(query)
            strategy["clause_types"] = self.extract_clause_types(query)
        
        return strategy
```

#### 4.4 Graph-Specific Patterns
```python
# Graph relationship patterns for contracts
GRAPH_PATTERNS = {
    "amendments": ["amends", "amendment", "addendum", "modification"],
    "relationships": ["between", "related", "connected", "linked"],
    "dependencies": ["depends on", "requires", "prerequisite", "based on"],
    "hierarchies": ["parent", "master", "sub-contract", "umbrella"],
    "networks": ["all contracts with", "network of", "web of"],
    "temporal": ["timeline", "sequence", "progression", "evolution"]
}

# Example graph queries:
Query: "Show all amendments to contract CTR-2024-001"
→ Strategy: "graph", operation: "amendments"

Query: "Find contracts between Company A and Company B"
→ Strategy: "graph", operation: "relationships"

Query: "Show the network of contracts involving Party X"
→ Strategy: "graph", operation: "networks"

Query: "What contracts depend on the master agreement?"
→ Strategy: "graph", operation: "dependencies"
```

#### 4.5 Combined Strategy Examples
```python
Query: "Find similar payment terms in contracts between Party A and Party B"
→ Primary: "graph" (to find contracts between parties)
→ Secondary: "vector" (to find similar payment terms)
→ Result: Hybrid strategy with graph filtering + vector search

Query: "Show how termination clauses evolved in our vendor contracts"
→ Primary: "graph" (temporal relationships)
→ Secondary: "vector" (clause similarity)
→ Result: Hybrid strategy analyzing clause evolution

Query: "Find all contracts with similar indemnification to CTR-2024-001"
→ Primary: "db" (get reference contract)
→ Secondary: "vector" (similarity search)
→ Result: Two-phase search strategy
```

#### 4.6 Search Mode Determination (for Vector Searches)
```python
def determine_search_mode(query: str) -> str:
    """Determine whether to search clauses, chunks, or both"""
    
    # Clause-specific indicators
    clause_indicators = [
        "clause", "term", "provision", "section",
        "indemnification", "termination", "payment",
        "liability", "warranty", "obligation"
    ]
    
    # Document-level indicators
    document_indicators = [
        "summary", "overall", "entire", "whole",
        "document", "contract says", "mentions"
    ]
    
    query_lower = query.lower()
    
    clause_score = sum(1 for ind in clause_indicators if ind in query_lower)
    doc_score = sum(1 for ind in document_indicators if ind in query_lower)
    
    if clause_score > doc_score:
        return "clause"
    elif doc_score > clause_score:
        return "chunk"
    else:
        return "hybrid"  # Search both when unclear
```

#### 4.3 Vector Search SQL Templates

**Clause Search:**
```sql
SELECT TOP {limit}
    c._id,
    c.parent_id,
    c.clause_type,
    c.clause_title,
    c.clause_text,
    c.attributes,
    VectorDistance(c.embedding, @embedding) as score
FROM c
WHERE c.doctype = 'contract_clause'
  AND c.clause_type IN (@types)  -- Optional filter
ORDER BY VectorDistance(c.embedding, @embedding)
```

**Chunk Search:**
```sql
SELECT TOP {limit}
    c._id,
    c.parent_id,
    c.chunk_index,
    c.chunk_text,
    c.section_title,
    VectorDistance(c.embedding, @embedding) as score
FROM c
WHERE c.doctype = 'contract_chunk'
ORDER BY VectorDistance(c.embedding, @embedding)
```

### 5. Implementation Components

#### 5.1 Java Components (graph_app)

**ContractsGraphTriplesBuilder.java**
- Replace `LibrariesGraphTriplesBuilder.java`
- Define contract-specific URIs and properties
- Build RDF triples from contract documents

```java
public class ContractsGraphTriplesBuilder {
    public static final String TYPE_CONTRACT_URI = "http://cosmosdb.com/caig#Contract";
    public static final String TYPE_PARTY_URI = "http://cosmosdb.com/caig#Party";
    public static final String TYPE_CLAUSE_URI = "http://cosmosdb.com/caig#Clause";
    
    // Implementation for building contract graph triples
}
```

#### 5.2 Python Components (web_app)

**Modified Services:**
- `entities_service.py`: Handle contract entities
- `cosmos_nosql_service.py`: Extended vector search for multi-level documents
- `rag_data_service.py`: Contract-specific RAG data retrieval

**New Services:**
- `contract_vector_search_service.py`: Specialized contract search
- `clause_extraction_pipeline.py`: PDF processing and clause extraction
- `contract_rag_service.py`: Contract-specific RAG orchestration

### 6. Data Processing Pipeline

#### 6.1 Contract Ingestion Flow
```
1. PDF Upload
   ↓
2. Text Extraction
   ↓
3. Parallel Processing:
   ├── Chunk Creation (500-1000 tokens, 10-20% overlap)
   └── Clause Extraction (AI-powered)
   ↓
4. Embedding Generation
   ├── Generate embeddings for each chunk
   └── Generate embeddings for each clause
   ↓
5. Storage in CosmosDB
   ├── Parent contract document
   ├── Clause documents
   └── Chunk documents
   ↓
6. Graph Update (RDF triples)
```

#### 6.2 Chunking Strategy
- **Chunk Size**: 500-1000 tokens per chunk
- **Overlap**: 10-20% overlap between consecutive chunks
- **Metadata Preservation**: Maintain page numbers and section titles
- **Cross-Reference**: Track which clauses appear in which chunks

### 7. CosmosDB Configuration

#### 7.1 Containers Required
- `contracts`: Parent contract documents
- `contract_clauses`: Extracted clause documents
- `contract_chunks`: Document chunk documents
- `config`: Configuration and entities

#### 7.2 Index Policy
```json
{
  "indexingPolicy": {
    "automatic": true,
    "indexingMode": "consistent",
    "vectorIndexes": [
      {
        "path": "/embedding",
        "type": "quantizedFlat",
        "dimensions": 1536,
        "distanceMetric": "cosine"
      },
      {
        "path": "/summary_embedding",
        "type": "quantizedFlat",
        "dimensions": 1536,
        "distanceMetric": "cosine"
      }
    ],
    "includedPaths": [
      {"path": "/*"}
    ],
    "compositeIndexes": [
      [
        {"path": "/doctype", "order": "ascending"},
        {"path": "/clause_type", "order": "ascending"}
      ],
      [
        {"path": "/parent_id", "order": "ascending"},
        {"path": "/chunk_index", "order": "ascending"}
      ]
    ]
  }
}
```

### 8. Environment Variables

Add/Modify in `.env` and configuration files:
```bash
# Database Configuration
CAIG_GRAPH_SOURCE_DB=caig
CAIG_GRAPH_SOURCE_CONTAINER=contracts
CAIG_CLAUSE_CONTAINER=contract_clauses
CAIG_CHUNK_CONTAINER=contract_chunks

# Ontology Configuration
CAIG_GRAPH_SOURCE_OWL_FILENAME=ontologies/contracts.owl
CAIG_GRAPH_NAMESPACE=http://cosmosdb.com/caig#

# Processing Configuration
CAIG_CHUNK_SIZE=750
CAIG_CHUNK_OVERLAP=0.15
CAIG_MAX_CLAUSES_PER_CONTRACT=100
CAIG_MAX_CHUNKS_PER_CONTRACT=200
```

### 9. API Endpoints

#### 9.1 New Endpoints Required
- `POST /ingest_contract`: Upload and process contract PDF
- `POST /search_clauses`: Search specific clause types
- `POST /search_contracts`: Hybrid contract search
- `GET /contract/{id}/clauses`: Get all clauses for a contract
- `GET /compare_clauses`: Compare similar clauses across contracts
- `POST /extract_clauses`: Extract clauses from uploaded document

#### 9.2 Modified Endpoints
- `/sparql_query`: Support contract-specific SPARQL queries
- `/vector_search`: Extended to support multi-level search
- `/ai_completion`: Context-aware completions for contract queries

### 10. SPARQL Query Templates

Create new templates in `sparql/` directory:
- `contracts_by_party.txt`
- `active_contracts.txt`
- `expiring_contracts.txt`
- `contracts_by_clause_type.txt`
- `contracts_missing_clauses.txt`

Example:
```sparql
# contracts_by_party.txt
PREFIX c: <http://cosmosdb.com/caig#>
SELECT ?contract ?contractNumber ?effectiveDate
WHERE {
    ?contract c:hasParty <http://cosmosdb.com/caig/{{party_id}}> .
    ?contract c:contractNumber ?contractNumber .
    ?contract c:effectiveDate ?effectiveDate .
}
ORDER BY DESC(?effectiveDate)
LIMIT {{limit}}
```

### 11. Migration Strategy

#### Phase 1: Infrastructure Setup
1. Create new CosmosDB containers
2. Deploy updated ontology files
3. Update environment variables

#### Phase 2: Core Components
1. Implement ContractsGraphTriplesBuilder.java
2. Update entities_service.py
3. Create contract-specific services

#### Phase 3: Search Implementation
1. Implement multi-level vector search
2. Create clause extraction pipeline
3. Update RAG services

#### Phase 4: UI Updates
1. Update web templates for contract terminology
2. Create contract-specific console pages
3. Update example queries

### 12. Testing Strategy

#### 12.1 Unit Tests
- Test clause extraction accuracy
- Validate embedding generation
- Verify search result ranking

#### 12.2 Integration Tests
- End-to-end contract ingestion
- Multi-level search validation
- RAG pipeline testing

#### 12.3 Performance Tests
- Vector search latency with multiple embeddings
- Chunk size optimization
- Query response time under load

### 13. Performance Considerations

#### 13.1 Storage Optimization
- **Estimated Storage per Contract**:
  - Parent document: ~2 KB
  - Clauses (avg 20): ~100 KB
  - Chunks (avg 50): ~500 KB
  - Embeddings: ~24 KB per vector (1536 dimensions × 4 bytes × 4 vectors average)

#### 13.2 Query Optimization
- Use composite indexes for filtering
- Implement result caching for common queries
- Batch embedding generation for efficiency

#### 13.3 Scaling Considerations
- Partition strategy: Consider partitioning by contract type or date range
- Vector index limits: Monitor CosmosDB vector index performance
- Implement pagination for large result sets

### 14. Security Considerations

- **PII Handling**: Implement redaction for sensitive contract information
- **Access Control**: Role-based access to contract documents
- **Audit Logging**: Track all contract searches and retrievals
- **Encryption**: Ensure embeddings don't leak sensitive information

### 15. Future Enhancements

1. **Clause Template Library**: Pre-defined standard clause templates
2. **Automated Compliance Checking**: Verify required clauses present
3. **Contract Comparison Tool**: Side-by-side clause comparison
4. **Anomaly Detection**: Identify unusual clauses using vector similarity
5. **Multi-language Support**: Extract and search clauses in multiple languages
6. **Version Control**: Track contract amendments and versions
7. **Automated Alerts**: Notify on expiring contracts or missing clauses

## Implementation Checklist

### Phase 1: Foundation (Week 1-2)
- [ ] Create contracts.owl ontology file
- [ ] Set up CosmosDB containers
- [ ] Update environment configurations
- [ ] Create ContractsGraphTriplesBuilder.java

### Phase 2: Data Model (Week 2-3)
- [ ] Implement contract document schemas
- [ ] Create clause extraction pipeline
- [ ] Implement chunking strategy
- [ ] Set up embedding generation

### Phase 3: Search Implementation (Week 3-4)
- [ ] Extend vector search for multi-level documents
- [ ] Implement hybrid search modes
- [ ] Create contract-specific RAG service
- [ ] Update API endpoints

### Phase 4: Integration & Testing (Week 4-5)
- [ ] Update UI for contract management
- [ ] Create SPARQL query templates
- [ ] Implement comprehensive tests
- [ ] Performance optimization

### Phase 5: Deployment (Week 5-6)
- [ ] Deploy to development environment
- [ ] User acceptance testing
- [ ] Documentation updates
- [ ] Production deployment

## Appendix A: Clause Type Taxonomy

Standard clause types for classification:
- `termination`: Termination conditions and procedures
- `payment`: Payment terms and schedules
- `liability`: Limitation of liability
- `indemnification`: Indemnification provisions
- `confidentiality`: Non-disclosure and confidentiality
- `warranty`: Warranties and representations
- `force_majeure`: Force majeure provisions
- `dispute_resolution`: Arbitration and dispute resolution
- `intellectual_property`: IP ownership and licensing
- `assignment`: Assignment and transfer rights
- `governing_law`: Governing law and jurisdiction
- `notice`: Notice requirements
- `amendment`: Amendment procedures
- `severability`: Severability provisions
- `entire_agreement`: Entire agreement clause

## Appendix B: Sample Queries

### Find Similar Termination Clauses
```python
similar_clauses = await contract_search.find_similar_clauses(
    clause_type="termination",
    reference_text="30 days written notice",
    min_similarity=0.85
)
```

### Find Contracts Missing Critical Clauses
```python
incomplete = await contract_search.find_incomplete_contracts(
    required_clauses=["liability", "indemnification", "governing_law"]
)
```

### Extract Key Terms from Contract
```python
key_terms = await contract_analysis.extract_key_terms(
    contract_id="CTR2024001",
    categories=["dates", "parties", "amounts", "obligations"]
)
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-20 | System Design Team | Initial design document |

## References

- Original CosmosDB AI Graph Implementation
- Azure CosmosDB Vector Search Documentation
- Apache Jena RDF/SPARQL Documentation
- OpenAI Embedding API Documentation