# SPARQL Query Implications with Normalized Entity Values

## Overview

With the implementation of normalized entity values in contract documents, there are several important implications for SPARQL query generation and execution. This document outlines the challenges and recommended solutions.

## Current Architecture

### 1. Data Storage Structure
```json
{
  "metadata": {
    "ContractorPartyName": {
      "value": "The Westervelt Company",  // Original value from AI extraction
      "normalizedValue": "westervelt",     // Normalized for searching
      "confidence": 0.95
    }
  },
  "contractor_party": "westervelt"  // Root level uses normalized value
}
```

### 2. Graph Service Data Flow
- Java Graph Service reads documents from CosmosDB
- `ContractsGraphTriplesBuilder.java` extracts values from ROOT-LEVEL properties
- These root-level properties NOW contain NORMALIZED values
- RDF triples are created with normalized values

## Key Implications

### 1. **Entity Names in Graph are Now Normalized**
   - **Before**: Graph contained "The Westervelt Company"
   - **After**: Graph contains "westervelt"
   - **Impact**: SPARQL queries must use normalized values for exact matches

### 2. **Natural Language to SPARQL Mapping Challenge**
   - User asks: "Find contracts with Westervelt Company"
   - System needs to normalize "Westervelt Company" → "westervelt"
   - SPARQL must search for "westervelt" not "Westervelt Company"

### 3. **Case Sensitivity Issues**
   - SPARQL is case-sensitive by default
   - Normalized values are lowercase
   - Queries need to account for this

## Solutions and Recommendations

### Solution 1: Pre-process Natural Language Queries

**Implementation in `ContractStrategyBuilder.py`:**
```python
def prepare_entities_for_sparql(self, natural_language: str) -> Dict:
    """
    Identify and normalize entities before SPARQL generation.
    Returns both original and normalized forms.
    """
    # Identify entities in text
    entities = ContractEntitiesService.identify_entities_in_text(natural_language)
    
    # Create mapping of original to normalized
    entity_mapping = {}
    for party in entities.get("contractor_parties", []):
        original = party["display_name"]
        normalized = party["normalized_name"]
        entity_mapping[original] = normalized
    
    # Replace entities in query with normalized forms
    modified_query = natural_language
    for original, normalized in entity_mapping.items():
        # Replace with normalized form in brackets for clarity
        modified_query = modified_query.replace(original, f"[{normalized}]")
    
    return {
        "original_query": natural_language,
        "modified_query": modified_query,
        "entity_mapping": entity_mapping
    }
```

### Solution 2: Update SPARQL Generation Prompt

**Modified `prompts/gen_sparql_v2.txt`:**
```text
You are a helpful agent designed to generate a SPARQL 1.1 query for an Apache Jena knowledge graph.

IMPORTANT: Entity values in the graph are normalized (lowercase, underscores for spaces, no punctuation).
When searching for entities:
- Company names are normalized (e.g., "The Westervelt Company" → "westervelt")
- State names are normalized (e.g., "Alabama." → "alabama")
- Contract types are normalized (e.g., "Master Services Agreement" → "master_services_agreement")

If brackets [] are present in the query, they indicate pre-normalized entity values that should be used exactly.
Example: "Find contracts with [westervelt]" means search for exactly "westervelt"

For string comparisons:
- Use FILTER with CONTAINS for partial matches
- Use exact match for normalized values
- Consider using LCASE() for case-insensitive matching on non-normalized fields
```

### Solution 3: Enhanced Entity Identification

**Update `RAGDataService.get_graph_rag_data()`:**
```python
async def get_graph_rag_data(self, user_text, rdr: RAGDataResult, max_doc_count=10) -> None:
    try:
        # First identify and normalize entities
        entities = ContractEntitiesService.identify_entities_in_text(user_text)
        
        # Enhance the query with normalized entity information
        enhanced_text = self.enhance_query_with_normalized_entities(user_text, entities)
        
        # Generate SPARQL with enhanced query
        info = dict()
        info["natural_language"] = enhanced_text
        info["owl"] = OntologyService().get_owl_content()
        info["identified_entities"] = entities  # Pass entities to AI
        
        sparql = self.ai_svc.generate_sparql_from_user_prompt(info)["sparql"]
```

### Solution 4: Add Entity Denormalization in Graph Service

**Option A: Store Both Values in Graph**
```java
// In ContractsGraphTriplesBuilder.java
private void ingestContractDocument(Map<String, Object> doc) {
    // Get both normalized (root) and original (metadata) values
    String contractorPartyNormalized = (String) doc.get("contractor_party");
    
    Map<String, Object> metadata = (Map<String, Object>) doc.get("metadata");
    String contractorPartyOriginal = null;
    if (metadata != null && metadata.containsKey("ContractorPartyName")) {
        Map<String, Object> field = (Map<String, Object>) metadata.get("ContractorPartyName");
        contractorPartyOriginal = (String) field.get("value");
    }
    
    // Add both as properties
    contractResource.addProperty(contractorPartyNameProperty, contractorPartyNormalized);
    if (contractorPartyOriginal != null) {
        contractResource.addProperty(contractorPartyDisplayNameProperty, contractorPartyOriginal);
    }
}
```

## Recommended Implementation Approach

### Phase 1: Immediate Changes (Required)
1. **Update SPARQL generation prompt** to explain normalized values
2. **Enhance entity identification** in ContractStrategyBuilder
3. **Pass normalized entities** to SPARQL generation

### Phase 2: Optimal Solution
1. **Modify Graph Service** to store both normalized and display values
2. **Update ontology** to include displayName properties
3. **Enable flexible SPARQL** queries on either form

### Phase 3: Advanced Features
1. **Implement query rewriting** to automatically handle variations
2. **Add fuzzy matching** in SPARQL using custom functions
3. **Create entity resolution service** for real-time normalization

## Example SPARQL Queries

### Before Normalization
```sparql
SELECT ?contract ?contractor ?value
WHERE {
  ?contract rdf:type :Contract .
  ?contract :contractorPartyName "The Westervelt Company" .
  ?contract :maximumContractValue ?value .
}
```

### After Normalization
```sparql
SELECT ?contract ?contractor ?value
WHERE {
  ?contract rdf:type :Contract .
  ?contract :contractorPartyName "westervelt" .
  ?contract :maximumContractValue ?value .
}
```

### With Flexible Matching
```sparql
SELECT ?contract ?contractor ?value
WHERE {
  ?contract rdf:type :Contract .
  ?contract :contractorPartyName ?contractor .
  FILTER(CONTAINS(LCASE(?contractor), "westervelt"))
  ?contract :maximumContractValue ?value .
}
```

## Testing Strategy

### 1. Unit Tests
- Test entity normalization consistency
- Verify SPARQL generation with normalized values
- Test entity identification and mapping

### 2. Integration Tests
- End-to-end query with natural language input
- Verify graph contains normalized values
- Test SPARQL execution returns expected results

### 3. Test Cases
```python
test_cases = [
    {
        "input": "Find contracts with Westervelt Company",
        "expected_entity": "westervelt",
        "expected_results": ["contract_123", "contract_456"]
    },
    {
        "input": "Show contracts governed by Alabama",
        "expected_entity": "alabama",
        "expected_results": ["contract_789"]
    }
]
```

## Migration Path

1. **Clear existing database** (as planned)
2. **Load contracts with normalized values**
3. **Update SPARQL generation prompt**
4. **Test with sample queries**
5. **Monitor and adjust entity identification**

## Future Enhancements

1. **Bidirectional Mapping Service**
   - Cache original ↔ normalized mappings
   - Fast lookup for query enhancement

2. **Smart Query Rewriting**
   - Automatically detect entity mentions
   - Rewrite queries with normalized forms

3. **Graph Enhancement**
   - Add rdfs:label for display names
   - Use normalized values as URIs
   - Enable SPARQL label searches

## Conclusion

The normalization of entity values significantly improves data consistency and search accuracy, but requires careful handling in SPARQL query generation. The recommended approach is to:

1. **Immediately**: Update prompts and enhance entity identification
2. **Next Sprint**: Modify graph service to store both forms
3. **Long-term**: Implement advanced query rewriting and fuzzy matching

This ensures that natural language queries continue to work seamlessly while benefiting from the improved entity normalization.