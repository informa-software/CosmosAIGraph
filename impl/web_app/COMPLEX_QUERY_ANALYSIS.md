# Complex Query Analysis: Multi-Contract Clause Comparison

## Query Example
"Compare the indemnification clauses in the contracts between Westervelt and ContractorA and ContractorB"

## Query Decomposition

### Entities to Identify
1. **Westervelt** → Likely contracting party (normalized: "westervelt")
2. **ContractorA** → Contractor party (normalized: "contractora")
3. **ContractorB** → Contractor party (normalized: "contractorb")

### Requirements
1. Find contracts where Westervelt is contracting party
2. Filter for contracts with ContractorA OR ContractorB as contractor party
3. Retrieve ONLY indemnification clauses from these contracts
4. Need clause text for comparison

## What Current Approach Would Retrieve

### With Current Vector Search
```python
# Current vector search would:
1. Embed the full query text
2. Search in contract_chunks container
3. Return chunks that mention these entities and "indemnification"

# Problems:
- Might get unrelated chunks that happen to mention these terms
- Won't necessarily get the actual indemnification CLAUSES
- May retrieve chunks from wrong contracts
- No guarantee of getting both contracts for comparison
```

### With Current Database Search
```python
# Current DB search would:
1. Try to match "Westervelt" as a name
2. Fail to understand the multi-contract requirement
3. Not know to look in contract_clauses container

# Problems:
- Can't handle the complex relationship query
- Doesn't understand clause-specific retrieval
```

## What SHOULD Be Retrieved

### Ideal RAG Context
```json
{
  "contract_1": {
    "id": "contract_123",
    "contracting_party": "The Westervelt Company",
    "contractor_party": "ContractorA LLC",
    "indemnification_clause": {
      "clause_type": "Indemnification",
      "clause_text": "ContractorA shall defend, indemnify, and hold harmless Westervelt from any claims arising from...",
      "confidence": 0.92
    }
  },
  "contract_2": {
    "id": "contract_456",
    "contracting_party": "The Westervelt Company", 
    "contractor_party": "ContractorB Inc",
    "indemnification_clause": {
      "clause_type": "Indemnification",
      "clause_text": "ContractorB agrees to indemnify Westervelt against all losses, damages, and expenses...",
      "confidence": 0.89
    }
  },
  "comparison_context": {
    "common_contracting_party": "The Westervelt Company",
    "clause_type_requested": "Indemnification",
    "contracts_found": 2
  }
}
```

## Enhanced Solution for Complex Queries

### Step 1: Query Understanding Service
```python
class QueryUnderstandingService:
    """
    Decomposes complex queries into structured requirements.
    """
    
    @staticmethod
    async def analyze_query(query: str) -> Dict:
        """
        Parse and understand complex multi-entity, multi-document queries.
        """
        analysis = {
            "query_type": "",
            "entities": {},
            "relationships": [],
            "clause_types": [],
            "operation": "",
            "constraints": []
        }
        
        # Identify comparison operation
        if "compare" in query.lower():
            analysis["operation"] = "comparison"
        
        # Identify clause types mentioned
        clause_keywords = {
            "indemnification": ["Indemnification", "IndemnificationObligations"],
            "payment": ["PaymentObligations"],
            "termination": ["TerminationObligations"],
            "warranty": ["WarrantyObligations"]
        }
        
        for keyword, clause_types in clause_keywords.items():
            if keyword in query.lower():
                analysis["clause_types"].extend(clause_types)
        
        # Identify entities and their likely roles
        entities = ContractEntitiesService.identify_entities_in_text(query)
        
        # Heuristic: "between X and Y and Z" pattern
        # Westervelt likely contracting party, others are contractors
        if "between" in query.lower():
            parts = query.lower().split("between")[1].split("and")
            if len(parts) >= 2:
                # First entity after "between" is likely contracting party
                analysis["relationships"].append({
                    "type": "contracting_party",
                    "entity": "westervelt"  # normalized
                })
                # Others are contractor parties
                for contractor in ["contractora", "contractorb"]:
                    analysis["relationships"].append({
                        "type": "contractor_party",
                        "entity": contractor
                    })
        
        return analysis
```

### Step 2: Multi-Container Orchestrated Retrieval
```python
async def retrieve_for_comparison(self, query_analysis: Dict) -> Dict:
    """
    Orchestrated retrieval across multiple containers for comparison queries.
    """
    results = {
        "contracts": [],
        "clauses": [],
        "chunks": []
    }
    
    # Step 1: Find relevant contracts
    contracting_party = None
    contractor_parties = []
    
    for rel in query_analysis["relationships"]:
        if rel["type"] == "contracting_party":
            contracting_party = rel["entity"]
        elif rel["type"] == "contractor_party":
            contractor_parties.append(rel["entity"])
    
    # Query contracts container for matching contracts
    self.nosql_svc.set_container("contracts")
    
    for contractor in contractor_parties:
        contract_query = f"""
        SELECT * FROM c 
        WHERE c.contracting_party = '{contracting_party}'
        AND c.contractor_party = '{contractor}'
        """
        
        contracts = await self.nosql_svc.query_items(contract_query)
        
        for contract in contracts:
            contract_id = contract["id"]
            
            # Step 2: Get specific clauses for this contract
            self.nosql_svc.set_container("contract_clauses")
            
            for clause_type in query_analysis["clause_types"]:
                clause_query = f"""
                SELECT * FROM c
                WHERE c.parent_id = '{contract_id}'
                AND c.clause_type = '{clause_type}'
                """
                
                clauses = await self.nosql_svc.query_items(clause_query)
                
                for clause in clauses:
                    # Enhance clause with contract context
                    clause["contract_context"] = {
                        "contractor_party": contract.get("contractor_party"),
                        "contracting_party": contract.get("contracting_party"),
                        "contract_id": contract_id,
                        "contract_value": contract.get("contract_value")
                    }
                    results["clauses"].append(clause)
            
            results["contracts"].append(contract)
    
    return results
```

### Step 3: RAG Context Builder for Comparison
```python
class ComparisonRAGBuilder:
    """
    Builds structured RAG context for comparison queries.
    """
    
    @staticmethod
    def build_comparison_context(retrieval_results: Dict, query_analysis: Dict) -> str:
        """
        Build structured context optimized for comparison operations.
        """
        context_parts = []
        
        # Group clauses by contract
        clauses_by_contract = {}
        for clause in retrieval_results["clauses"]:
            contract_id = clause["contract_context"]["contract_id"]
            if contract_id not in clauses_by_contract:
                clauses_by_contract[contract_id] = []
            clauses_by_contract[contract_id].append(clause)
        
        # Build comparison context
        context_parts.append("COMPARISON CONTEXT:\n")
        context_parts.append(f"Comparing {query_analysis['clause_types']} clauses\n\n")
        
        for contract in retrieval_results["contracts"]:
            contract_id = contract["id"]
            
            # Get display names from metadata
            metadata = contract.get("metadata", {})
            contractor_display = metadata.get("ContractorPartyName", {}).get("value", contract["contractor_party"])
            contracting_display = metadata.get("ContractingPartyName", {}).get("value", contract["contracting_party"])
            
            context_parts.append(f"CONTRACT: {contractor_display} with {contracting_display}\n")
            context_parts.append(f"Contract ID: {contract_id}\n")
            
            # Add relevant clauses
            if contract_id in clauses_by_contract:
                for clause in clauses_by_contract[contract_id]:
                    context_parts.append(f"\n{clause['clause_type']} Clause:\n")
                    context_parts.append(f"{clause['clause_text']}\n")
                    context_parts.append(f"(Confidence: {clause.get('confidence', 'N/A')})\n")
            
            context_parts.append("\n" + "="*50 + "\n\n")
        
        return "".join(context_parts)
```

### Step 4: Enhanced RAG Data Service
```python
async def get_rag_data(self, user_text, max_doc_count=10, strategy_override: Optional[str] = None) -> RAGDataResult:
    """
    Enhanced to handle complex comparison queries.
    """
    rdr = RAGDataResult()
    
    # Analyze query complexity
    query_analysis = await QueryUnderstandingService.analyze_query(user_text)
    
    # Route based on query type
    if query_analysis["operation"] == "comparison" and query_analysis["clause_types"]:
        # Complex comparison query - use orchestrated retrieval
        retrieval_results = await self.retrieve_for_comparison(query_analysis)
        
        # Build structured comparison context
        comparison_context = ComparisonRAGBuilder.build_comparison_context(
            retrieval_results, 
            query_analysis
        )
        
        # Add as structured document
        rdr.add_doc({
            "type": "comparison_context",
            "context": comparison_context,
            "contracts_compared": len(retrieval_results["contracts"]),
            "clauses_retrieved": len(retrieval_results["clauses"])
        })
        
        # Also add individual documents for reference
        for clause in retrieval_results["clauses"]:
            rdr.add_doc(clause)
    
    else:
        # Fall back to existing strategies
        # ... existing code ...
```

## Required System Enhancements

### 1. Query Understanding Layer
- **NLP-based parsing** to identify entities, relationships, and intent
- **Clause type mapping** to database fields
- **Relationship inference** (who contracts with whom)

### 2. Multi-Container Orchestration
- **Coordinated queries** across contracts, chunks, and clauses
- **Relationship-based filtering** (contracting vs contractor party)
- **Clause-specific retrieval** from contract_clauses container

### 3. Context Assembly
- **Structured comparison format** for AI to process
- **Entity denormalization** for readability
- **Confidence scores** for clause extraction quality

### 4. Enhanced Strategy Builder
```python
class ContractStrategyBuilder:
    
    def determine(self, natural_language: str) -> Dict:
        # Check for complex comparison patterns
        if self.is_comparison_query(natural_language):
            return {
                "strategy": "orchestrated",
                "sub_strategy": "clause_comparison",
                "containers": ["contracts", "contract_clauses"],
                "requires_analysis": True
            }
        
        # ... existing logic ...
```

## Testing the Enhanced Approach

### Test Query 1: Simple Comparison
```
Query: "Compare indemnification clauses between Westervelt and ContractorA"
Expected:
- 1 contract retrieved
- 1 indemnification clause
- Structured comparison context
```

### Test Query 2: Multi-Contract Comparison
```
Query: "Compare payment terms in all Westervelt contracts"
Expected:
- All Westervelt contracts
- All payment obligation clauses
- Grouped by contractor
```

### Test Query 3: Complex Multi-Clause
```
Query: "Show termination and warranty clauses for ABC Corp contracts from 2024"
Expected:
- Filtered by company and date
- Multiple clause types
- Temporal filtering
```

## Performance Considerations

### Query Complexity Impact
- Simple vector search: ~200ms
- Orchestrated multi-container: ~500-800ms
- Complex comparison with 5+ contracts: ~1-2s

### Optimization Strategies
1. **Parallel container queries** where possible
2. **Selective field projection** to reduce data transfer
3. **Query result caching** for repeated comparisons
4. **Pre-computed relationships** in graph for complex queries

## Conclusion

The current approach needs significant enhancement to properly handle complex comparison queries. The solution requires:

1. **Query understanding** to decompose complex requests
2. **Multi-container orchestration** to retrieve related documents
3. **Clause-specific retrieval** from the contract_clauses container
4. **Structured context building** for comparison operations
5. **Entity resolution** to handle normalized vs display names

Without these enhancements, the system would likely return incomplete or incorrect results for comparison queries, missing the specific clauses needed for proper comparison.