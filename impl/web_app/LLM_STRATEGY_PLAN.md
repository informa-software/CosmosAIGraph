# LLM-Based Query Strategy Determination - Implementation Plan

## Executive Summary

This document outlines a plan to use an LLM (Azure OpenAI) to both determine optimal query strategies AND generate ready-to-execute queries in a single call, replacing brittle regex-based pattern matching. The LLM will analyze natural language queries and return a complete execution plan with SQL/SPARQL queries ready to run.

**Status**: Planning - Not Yet Implemented
**Created**: 2025-10-02
**Updated**: 2025-10-02 (Revised to single-call approach)
**Goal**: Solve complex query interpretation (negations, OR lists, compound filters)
**Approach**: Single LLM call for strategy + query generation (optimized for speed and simplicity)

---

## Problem Statement

### Current Issues with Rule-Based Approach

1. **Negation Complexity**: Queries like "not governed by Alabama" require complex regex patterns that are brittle
2. **List Interpretation**: "Show contracts in California, Texas, or Florida" - unclear how to handle:
   - Should this be ENTITY_FIRST with first state?
   - CONTRACT_DIRECT with OR conditions?
   - Three separate lookups merged?
3. **Pattern Brittleness**: Variations break regex:
   - "contracts excluding California and Texas"
   - "all states except Alabama, Florida, and Georgia"
   - "contracts in any state but not California"
4. **Compound Queries**: "MSA contracts with Microsoft in California or Texas but not governed by Alabama"
   - Multiple entities + OR logic + negation = pattern matching nightmare

### Why LLM-First Makes Sense

- ✅ **Natural Language Understanding**: LLMs excel at parsing intent from varied phrasings
- ✅ **Context Awareness**: Can understand "or", "and", "except", "excluding" in context
- ✅ **Schema Knowledge**: Can be given database schema and make informed routing decisions
- ✅ **Explainability**: Can provide reasoning for strategy choice
- ✅ **Maintainability**: Prompt tuning vs code changes

---

## Solution Architecture

### High-Level Flow (Single-Call Approach)

```
User Query
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ LLMQueryPlanner (NEW - Single Call)                             │
│ Input:  query + DB schema + Ontology + strategies               │
│ Output: strategy + ready-to-execute query + reasoning           │
│ Time:   ~250ms (one API call)                                   │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ Query Validation Layer                                          │
│ - Validates SQL syntax (for CONTRACT_DIRECT)                    │
│ - Validates SPARQL syntax (for GRAPH_TRAVERSAL)                 │
│ - Validates execution plan structure                            │
│ - Falls back to rule-based on validation failure                │
└──────────────────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────────────────┐
│ Direct Execution (No Translation Layer Needed)                  │
│ - Execute SQL query as-is                                       │
│ - Execute SPARQL query as-is                                    │
│ - Execute entity lookup plan                                    │
└──────────────────────────────────────────────────────────────────┘
    ↓
Results + Execution Trace
```

**Key Difference from Two-Call Approach**:
- ✅ One LLM call instead of two (strategy determination + query generation)
- ✅ ~45% faster (250ms vs 450ms)
- ✅ Simpler implementation (no coordination between calls)
- ✅ LLM has full context for better decisions
- ✅ Ready-to-execute queries (no translation step)

---

## LLM Input Design (Single Unified Call)

### Overview

Send everything in one call:
- User's natural language query
- Complete database schema (all collections)
- Complete graph ontology (for SPARQL)
- Available strategies with descriptions
- Query generation rules

**Token Budget**: ~5K-6K input tokens (acceptable for single call)
**Response**: ~800 tokens (strategy + query + reasoning)

### 1. Database Schema Context

**Schema Definition File**: `web_app/schemas/cosmos_contracts_schema.json`

The schema should be externalized to a JSON file that evolves independently from code. `StrategySchemaBuilder` loads this file and passes it to the LLM.

**Recommended Schema Format** (with field-level details for better LLM understanding):

```json
{
  "schema_version": "1.0",
  "last_updated": "2025-10-03",
  "database": "CosmosDB NoSQL",
  "collections": {
    "contracts": {
      "description": "Main contract documents collection",
      "primary_key": "id",
      "fields": [
        {"name": "id", "type": "string", "description": "Unique contract ID"},
        {"name": "governing_law_state", "type": "string", "description": "State governing contract (normalized: lowercase, underscores)"},
        {"name": "contractor_party", "type": "string", "description": "Party performing contract (normalized)"},
        {"name": "contracting_party", "type": "string", "description": "Party initiating contract (normalized)"},
        {"name": "contract_type", "type": "string", "description": "Contract type: msa, nda, sow (normalized)"},
        {"name": "effective_date", "type": "string", "description": "Contract effective date (ISO format)"},
        {"name": "expiration_date", "type": "string", "description": "Contract expiration date (ISO format)"},
        {"name": "maximum_contract_value", "type": "number", "description": "Maximum value in dollars"}
      ],
      "indexed_fields": ["id", "governing_law_state", "contractor_party", "contracting_party", "contract_type", "effective_date"],
      "has_embeddings": true,
      "supports": ["direct_query", "vector_search"],
      "entity_references": {
        "governing_law_state": "governing_law_states",
        "contractor_party": "contractor_parties",
        "contracting_party": "contracting_parties",
        "contract_type": "contract_types"
      }
    },
    "governing_law_states": {
      "description": "Entity collection for states with pre-computed aggregations",
      "primary_key": "normalized_name",
      "fields": [
        {"name": "normalized_name", "type": "string", "description": "Normalized state (e.g., 'california')"},
        {"name": "display_name", "type": "string", "description": "Display name (e.g., 'California')"},
        {"name": "contracts", "type": "array<string>", "description": "Array of contract IDs"},
        {"name": "contract_count", "type": "number", "description": "Pre-computed count"},
        {"name": "total_value", "type": "number", "description": "Pre-computed sum of contract values"}
      ],
      "indexed_fields": ["normalized_name", "display_name"],
      "is_entity_collection": true,
      "stats_fields": ["contract_count", "total_value"],
      "supports": ["entity_first_lookup", "aggregation"]
    },
    "contractor_parties": {
      "description": "Entity collection for contractor parties",
      "primary_key": "normalized_name",
      "fields": [
        {"name": "normalized_name", "type": "string", "description": "Normalized party name"},
        {"name": "display_name", "type": "string", "description": "Display name"},
        {"name": "contracts", "type": "array<string>", "description": "Array of contract IDs"},
        {"name": "contract_count", "type": "number", "description": "Pre-computed count"},
        {"name": "total_value", "type": "number", "description": "Pre-computed sum"}
      ],
      "indexed_fields": ["normalized_name", "display_name"],
      "is_entity_collection": true,
      "stats_fields": ["contract_count", "total_value"],
      "supports": ["entity_first_lookup", "aggregation"]
    },
    "contracting_parties": {
      "description": "Entity collection for contracting parties",
      "primary_key": "normalized_name",
      "fields": [
        {"name": "normalized_name", "type": "string", "description": "Normalized party name"},
        {"name": "display_name", "type": "string", "description": "Display name"},
        {"name": "contracts", "type": "array<string>", "description": "Array of contract IDs"},
        {"name": "contract_count", "type": "number", "description": "Pre-computed count"},
        {"name": "total_value", "type": "number", "description": "Pre-computed sum"}
      ],
      "indexed_fields": ["normalized_name", "display_name"],
      "is_entity_collection": true,
      "stats_fields": ["contract_count", "total_value"],
      "supports": ["entity_first_lookup", "aggregation"]
    },
    "contract_types": {
      "description": "Entity collection for contract types",
      "primary_key": "normalized_name",
      "fields": [
        {"name": "normalized_name", "type": "string", "description": "Normalized type (msa, nda, sow)"},
        {"name": "display_name", "type": "string", "description": "Display name (MSA, NDA, SOW)"},
        {"name": "contracts", "type": "array<string>", "description": "Array of contract IDs"},
        {"name": "contract_count", "type": "number", "description": "Pre-computed count"},
        {"name": "total_value", "type": "number", "description": "Pre-computed sum"}
      ],
      "indexed_fields": ["normalized_name", "display_name"],
      "is_entity_collection": true,
      "stats_fields": ["contract_count", "total_value"],
      "supports": ["entity_first_lookup", "aggregation"]
    }
  },
  "normalization_rules": {
    "description": "All entity values are normalized: lowercase, underscores for spaces, special chars removed",
    "examples": {
      "California": "california",
      "New York": "new_york",
      "Microsoft Corporation": "microsoft"
    }
  }
}
```

**Benefits of External Schema File:**
- ✅ Version controlled - track schema evolution over time
- ✅ Field descriptions help LLM understand semantics and generate accurate queries
- ✅ Add new collections/fields without code changes
- ✅ Rich context improves LLM query generation quality
- ✅ Schema validation ensures consistency between code and LLM
- ✅ Single source of truth for database structure
- ✅ Documents normalization rules for LLM to apply correctly

### 2. Graph Ontology Context

Provide complete ontology from `web_app/ontologies/contracts.owl` (used for SPARQL generation):

**Key Classes:**
- `caig:Contract` - Legally binding agreement
- `caig:ContractorParty` - Party performing the contract
- `caig:ContractingParty` - Party initiating the contract
- `caig:GoverningLawState` - State whose laws govern the contract
- `caig:Clause` - Contractual clause/provision (base class with 14+ subclasses)

**Key Object Properties:**
- `caig:is_performed_by` - Contract → ContractorParty
- `caig:performs` - ContractorParty → Contract (inverse)
- `caig:is_initiated_by` - Contract → ContractingParty
- `caig:initiates` - ContractingParty → Contract (inverse)
- `caig:is_governed_by` - Contract → GoverningLawState
- `caig:governs` - GoverningLawState → Contract (inverse)
- `caig:contains` - Contract → Clause
- `caig:is_contained_in` - Clause → Contract (inverse)

**Key Datatype Properties:**
- `caig:contractorPartyName` - Name of contractor party (xsd:string)
- `caig:contractingPartyName` - Name of contracting party (xsd:string)
- `caig:contractType` - Type of contract like MSA, NDA, SOW (xsd:string)
- `caig:effectiveDate` - Contract effective date (xsd:string)
- `caig:expirationDate` - Contract expiration date (xsd:string)
- `caig:maximumContractValue` - Maximum contract value (xsd:decimal)
- `caig:filename` - Contract document filename (xsd:string)

**SPARQL Prefix:**
```sparql
PREFIX caig: <http://cosmosdb.com/caig#>

# Data Properties
caig:contractId rdf:type owl:DatatypeProperty .
caig:vendor rdf:type owl:DatatypeProperty .
caig:effectiveDate rdf:type owl:DatatypeProperty .
```

**Note**: Both database schema AND ontology are sent in every call. The LLM chooses which to use based on the query.

### 3. Available Query Strategies

```json
{
  "strategies": [
    {
      "name": "ENTITY_FIRST",
      "description": "Query entity collection first (e.g., governing_law_states), then batch retrieve contracts by IDs",
      "best_for": "Single entity queries with high selectivity",
      "requirements": "Exactly one positive entity (no negations only, no OR lists)",
      "performance": "Low RU cost (1-2 RUs entity + 0.1 RU per contract)",
      "example": "All contracts governed by California"
    },
    {
      "name": "CONTRACT_DIRECT",
      "description": "Direct SQL query on contracts collection with WHERE filters",
      "best_for": "Multi-filter queries, negations, OR conditions, complex filters",
      "requirements": "Any combination of filters (positive, negative, OR, AND)",
      "performance": "Medium RU cost (5-50 RUs depending on filters)",
      "example": "MSA contracts with Microsoft in California or Texas but not Alabama"
    },
    {
      "name": "ENTITY_AGGREGATION",
      "description": "Return pre-computed statistics from entity collections",
      "best_for": "Count, sum, average queries on single entity",
      "requirements": "Aggregation keywords + single entity",
      "performance": "Very low RU cost (1 RU)",
      "example": "How many contracts governed by California?"
    },
    {
      "name": "GRAPH_TRAVERSAL",
      "description": "SPARQL query on RDF graph for relationship queries",
      "best_for": "Queries about relationships, dependencies, connections",
      "requirements": "Relationship keywords (between, connected, depends on)",
      "performance": "Variable RU cost (10-100 RUs)",
      "example": "What contracts depend on Microsoft libraries?"
    },
    {
      "name": "VECTOR_SEARCH",
      "description": "Semantic similarity search using embeddings",
      "best_for": "Fuzzy matching, semantic queries, fallback when structured queries fail",
      "requirements": "Use as fallback only",
      "performance": "High RU cost (50-200 RUs)",
      "example": "Contracts similar to Acme Corp agreement"
    }
  ]
}
```

### 4. System Prompt Template (Single-Call with Query Generation)

```
You are a query execution planner for a contract database system.

You will receive:
1. User's natural language query
2. Complete database schema (CosmosDB NoSQL collections)
3. Complete graph ontology (for SPARQL queries)
4. Available query strategies

Your task is to:
1. Choose the optimal query strategy
2. Generate the ready-to-execute query (SQL, SPARQL, or lookup plan)
3. Provide execution plan details
4. Explain your reasoning

# Database Schema (for SQL queries)
{db_schema_json}

# Graph Ontology (for SPARQL queries)
{ontology_turtle}

# Available Strategies
- ENTITY_FIRST: Query entity collection, then batch retrieve contracts
  * Requirements: EXACTLY ONE entity from ONE collection (not "MSA + Microsoft")
  * Output: Multi-step lookup plan

- CONTRACT_DIRECT: Direct SQL on contracts with WHERE filters
  * Use for: Negations, OR lists, multiple entities, complex filters
  * Output: SQL query with proper WHERE clause

- ENTITY_AGGREGATION: Use pre-computed statistics
  * Use for: count/sum/average on single entity
  * Output: Entity lookup query

- GRAPH_TRAVERSAL: SPARQL query on RDF graph
  * Use for: Relationship queries (between, connected, depends on)
  * Output: SPARQL query with proper prefixes

- VECTOR_SEARCH: Semantic similarity (fallback only)
  * Use when: Structured queries fail
  * Output: Embedding search parameters

# Query Generation Rules
SQL Queries (CONTRACT_DIRECT):
- Use CosmosDB SQL syntax: SELECT TOP N * FROM c WHERE ...
- Operators: =, !=, IN, NOT IN, AND, OR
- Normalize values: lowercase, underscores (e.g., "california" not "California")
- Example: SELECT TOP 100 * FROM c WHERE c.governing_law_state IN ('california', 'texas')

SPARQL Queries (GRAPH_TRAVERSAL):
- Use PREFIX caig: <http://cosmosdb.com/caig#>
- Use correct ontology properties (hasGoverningLaw, dependsOn, etc.)
- Example: PREFIX caig: <http://cosmosdb.com/caig#> SELECT ?contract WHERE { ?contract caig:dependsOn ?lib }

Entity Lookup (ENTITY_FIRST):
- Step 1: Query entity collection by normalized_name
- Step 2: Batch retrieve contracts using IDs from step 1
- Provide SQL for step 1

# Critical Rules
1. ENTITY_FIRST requires EXACTLY ONE entity from ONE collection
   - "California" → ENTITY_FIRST ✓
   - "MSA contracts with Microsoft" → CONTRACT_DIRECT (2 entities) ✗

2. CONTRACT_DIRECT for complex patterns:
   - Negations: WHERE c.field != 'value'
   - OR lists: WHERE c.field IN ('val1', 'val2', 'val3')
   - Multiple entities: WHERE c.field1 = 'val1' AND c.field2 = 'val2'

3. Generate queries with normalized values (lowercase, underscores)

# Response Format (JSON only, no markdown)
{
  "strategy": "CONTRACT_DIRECT",
  "confidence": 0.95,
  "reasoning": "Brief explanation",

  "query": {
    "type": "SQL",
    "text": "SELECT TOP 100 * FROM c WHERE c.governing_law_state IN ('california', 'texas')"
  },

  "execution_plan": {
    "collection": "contracts",
    "estimated_ru_cost": 15,
    "estimated_results": 10
  },

  "fallback_strategy": "VECTOR_SEARCH"
}
```

---

## Expected LLM Response Format (With Ready-to-Execute Queries)

### TypeScript Interface

```typescript
interface LLMQueryPlan {
  strategy: "ENTITY_FIRST" | "CONTRACT_DIRECT" | "ENTITY_AGGREGATION" | "GRAPH_TRAVERSAL" | "VECTOR_SEARCH";
  fallback_strategy: string;

  // The ready-to-execute query
  query: {
    type: "SQL" | "SPARQL" | "ENTITY_LOOKUP";
    text?: string;  // For SQL and SPARQL
    steps?: Array<{  // For ENTITY_FIRST multi-step plans
      step: number;
      action: string;
      collection: string;
      key?: string;
      sql?: string;
      method?: string;
      note?: string;
    }>;
  };

  // Execution plan details
  execution_plan: {
    collection: string | string[];  // Primary collection(s)
    estimated_ru_cost: number;
    estimated_results: number;
  };

  confidence: number;  // 0.0-1.0
  reasoning: string;   // Explanation for debugging/logging
}
```

### Example Responses

#### Example 1: Simple Single Entity (ENTITY_FIRST with Multi-Step Plan)
**Query**: "Show all contracts governed by California"

```json
{
  "strategy": "ENTITY_FIRST",
  "fallback_strategy": "CONTRACT_DIRECT",

  "query": {
    "type": "ENTITY_LOOKUP",
    "steps": [
      {
        "step": 1,
        "action": "lookup_entity",
        "collection": "governing_law_states",
        "key": "california",
        "sql": "SELECT * FROM c WHERE c.normalized_name = 'california'"
      },
      {
        "step": 2,
        "action": "batch_retrieve_contracts",
        "collection": "contracts",
        "method": "batch_read",
        "note": "Use contract IDs from step 1"
      }
    ]
  },

  "execution_plan": {
    "collection": ["governing_law_states", "contracts"],
    "estimated_ru_cost": 2,
    "estimated_results": 12
  },

  "confidence": 0.95,
  "reasoning": "Single entity query with high selectivity. ENTITY_FIRST optimal for low RU cost."
}
```

#### Example 2: Negation Query (CONTRACT_DIRECT with SQL)
**Query**: "Show all contracts not governed by Alabama"

```json
{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",

  "query": {
    "type": "SQL",
    "text": "SELECT TOP 100 * FROM c WHERE c.governing_law_state != 'alabama'"
  },

  "execution_plan": {
    "collection": "contracts",
    "estimated_ru_cost": 10,
    "estimated_results": 85
  },

  "confidence": 0.98,
  "reasoning": "Negation query. ENTITY_FIRST cannot handle negations. CONTRACT_DIRECT with != operator required."
}
```

#### Example 3: State List with OR
**Query**: "Show contracts in California, Texas, or Florida"

```json
{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",

  "query": {
    "type": "SQL",
    "text": "SELECT TOP 100 * FROM c WHERE c.governing_law_state IN ('california', 'texas', 'florida')"
  },

  "execution_plan": {
    "collection": "contracts",
    "estimated_ru_cost": 15,
    "estimated_results": 45
  },

  "confidence": 0.97,
  "reasoning": "OR list with 3 states. ENTITY_FIRST requires single entity. CONTRACT_DIRECT with IN operator handles multiple values efficiently."
}
```

#### Example 4: Complex Multi-Filter
**Query**: "MSA contracts with Microsoft in California or Texas but not governed by Alabama"

```json
{
  "strategy": "CONTRACT_DIRECT",
  "fallback_strategy": "VECTOR_SEARCH",

  "query": {
    "type": "SQL",
    "text": "SELECT TOP 100 * FROM c WHERE c.contract_type = 'msa' AND c.contracting_party = 'microsoft' AND c.governing_law_state IN ('california', 'texas') AND c.governing_law_state != 'alabama'"
  },

  "execution_plan": {
    "collection": "contracts",
    "estimated_ru_cost": 25,
    "estimated_results": 12
  },

  "confidence": 0.92,
  "reasoning": "Complex query with multiple filters (contract_type, contracting_party), OR condition (CA/TX), and negation (NOT AL). Only CONTRACT_DIRECT can handle this combination."
}
```

#### Example 5: Aggregation
**Query**: "How many contracts are governed by California?"

```json
{
  "strategy": "ENTITY_AGGREGATION",
  "fallback_strategy": "CONTRACT_DIRECT",

  "query": {
    "type": "SQL",
    "text": "SELECT * FROM c WHERE c.id = 'california'"
  },

  "execution_plan": {
    "collection": "governing_law_states",
    "aggregation_field": "contract_count",
    "estimated_ru_cost": 1,
    "estimated_results": 1
  },

  "confidence": 0.99,
  "reasoning": "Count query on single entity. Pre-computed contract_count stat in governing_law_states collection provides instant 1 RU result."
}
```

---

## Implementation Phases

### Phase 1: Foundation (Parallel Analysis - No Behavior Change)
**Goal**: Add LLM query planner alongside existing rule-based approach without changing execution

**Tasks**:
1. ✅ **Create `LLMQueryPlanner` class**
   - Location: `web_app/src/services/llm_query_planner.py`
   - Method: `plan_query(user_text: str, schema_context: dict, ontology: str) -> LLMQueryPlan`
   - Single LLM call returns both strategy AND ready-to-execute query (SQL/SPARQL)
   - Builds system prompt with DB schema + ontology + strategy rules
   - Calls Azure OpenAI with `response_format={"type": "json_object"}`
   - Validates JSON response and query syntax
   - Returns structured `LLMQueryPlan` object with executable query

2. ✅ **Create `StrategySchemaBuilder` class**
   - Location: `web_app/src/services/strategy_schema_builder.py`
   - **Loads DB schema from `web_app/schemas/cosmos_contracts_schema.json`**
   - **Loads ontology from `web_app/ontologies/contracts.owl`**
   - Extracts key classes, properties, and relationships from both files
   - Provides strategy descriptions and decision rules
   - Returns unified context object for LLM prompt
   - Validates schema version compatibility

3. ✅ **Create schema definition file**
   - Location: `web_app/schemas/cosmos_contracts_schema.json`
   - Define all CosmosDB collections with field-level details
   - Include field descriptions for LLM semantic understanding
   - Document normalization rules and entity relationships
   - Version the schema for compatibility tracking

4. ✅ **Create Query Validators**
   - `SQLValidator` class: Validates CosmosDB SQL syntax
   - `SPARQLValidator` class: Validates SPARQL query syntax
   - Both check for common errors, injection risks, schema compliance
   - Used before executing LLM-generated queries

5. ✅ **Update `ContractStrategyBuilder.determine()`**
   - Add parameter: `use_llm_planning: bool = False`
   - When `True`:
     - Call `LLMQueryPlanner.plan_query()` first
     - Log LLM response with strategy, query, and reasoning
     - Store in `strategy["llm_plan"]` for comparison
   - **Still use rule-based path for actual execution**
   - Add comparison logging: `logger.info(f"LLM Strategy: {llm_plan.strategy}, Rule-Based: {rule_strategy}")`

6. ✅ **Add environment configuration**
   - `CAIG_USE_LLM_STRATEGY: bool` (default: `False`)
   - When `True`, enables parallel LLM planning for comparison
   - Does NOT change execution behavior yet

7. ✅ **Update execution tracker**
   - Add fields: `llm_plan`, `rule_based_strategy`, `strategy_match: bool`
   - Include LLM reasoning and generated query in trace metadata
   - Track query generation quality and syntax errors
   - Track disagreements for analysis

**Deliverables**:
- `llm_query_planner.py` - Single-call LLM planning engine
- `strategy_schema_builder.py` - Loads schema JSON + ontology OWL files
- `schemas/cosmos_contracts_schema.json` - **NEW: External schema definition file**
- `sql_validator.py` + `sparql_validator.py` - Query syntax validators
- Enhanced `contract_strategy_builder.py` - Parallel planning comparison
- Execution traces include LLM vs rule-based comparison with queries
- **Zero impact on query execution behavior**

**Testing**:
- Unit tests for `LLMQueryPlanner` with mocked OpenAI responses
- Query validator tests with valid/invalid SQL and SPARQL
- Integration test: run 10 sample queries, validate generated queries
- Verify execution still uses rule-based path

---

### Phase 2: Validation & Comparison
**Goal**: Compare LLM vs rule-based results, measure accuracy, iterate on prompt

**Tasks**:
1. ✅ **Create comprehensive test suite**
   - File: `web_app/test_llm_strategy_comparison.py`
   - 50+ test queries covering:
     - Simple single entity (10 queries)
     - Negations (10 queries)
     - OR lists (10 queries)
     - Multi-filter (10 queries)
     - Aggregations (5 queries)
     - Graph/relationship (5 queries)
     - Edge cases (10 queries)
   - For each query:
     - Expected strategy
     - Run both LLM and rule-based
     - Compare results
     - Log disagreements

2. ✅ **Add comparison metrics**
   - Metrics to track:
     - `llm_accuracy`: % of queries where LLM matches expected
     - `rule_based_accuracy`: % where rule-based matches expected
     - `agreement_rate`: % where LLM and rule-based agree
     - `llm_latency`: Average LLM analysis time
     - `confidence_distribution`: Histogram of LLM confidence scores
   - Store in execution tracker metadata

3. ✅ **Create comparison report generator**
   - Script: `web_app/generate_strategy_comparison_report.py`
   - Analyzes execution traces from `tmp/execution_trace_*.json`
   - Generates report:
     - Summary statistics
     - Disagreement analysis (queries where LLM != rule-based)
     - Categorization: improvements, regressions, equivalent
     - Recommendations for prompt tuning
   - Output: `tmp/llm_strategy_comparison_report.md`

4. ✅ **Iterate on LLM prompt**
   - Based on comparison report findings:
     - Adjust system prompt for edge cases
     - Add few-shot examples for problematic patterns
     - Tune temperature (start at 0.0 for deterministic)
     - Refine strategy rules and descriptions
   - Re-run test suite after each iteration
   - Track improvement over iterations

**Deliverables**:
- Comprehensive test suite with 50+ queries
- Comparison metrics in execution tracker
- Automated comparison report generator
- Refined LLM prompt based on empirical results
- Documentation of LLM accuracy vs rule-based

**Success Criteria**:
- LLM accuracy ≥ 90% on test suite
- LLM handles negations and OR lists correctly (100%)
- Disagreements with rule-based are justified improvements

---

### Phase 3: Enhanced Execution Path
**Goal**: Actually use LLM-generated queries for execution (opt-in via feature flag)

**Tasks**:
1. ✅ **Create `LLMQueryExecutor` class**
   - Location: `web_app/src/services/llm_query_executor.py`
   - Method: `execute_plan(llm_plan: LLMQueryPlan) -> QueryResults`
   - Validates LLM-generated query with validators (SQL/SPARQL)
   - Routes to appropriate service based on query type:
     - SQL → `CosmosNoSQLService.execute_sql()`
     - SPARQL → `OntologyService.sparql_query()`
   - Handles execution errors with fallback to rule-based
   - Tracks query performance metrics

2. ✅ **Update `CosmosNoSQLService.execute_sql()`**
   - Accept arbitrary SQL from LLM (already supports parameterized queries)
   - Validate SQL syntax before execution
   - Support all operators in LLM-generated SQL:
     - `=`, `!=` (already supported)
     - `IN`, `NOT IN` (already supported)
     - `AND`, `OR` combinations
   - Log actual SQL executed for debugging

3. ✅ **Update `RAGDataService.get_database_rag_data()`**
   - Check `ConfigService.envvar("CAIG_USE_LLM_EXECUTION", "false")`
   - When `True`:
     - Use `LLMQueryPlanner` to get strategy + query
     - Validate query with `SQLValidator` or `SPARQLValidator`
     - Execute query with `LLMQueryExecutor`
     - Track which path was used in execution trace
   - When `False` or on LLM/validation failure:
     - Fallback to rule-based `QueryOptimizer` + execution
     - Log fallback reason

4. ✅ **Add safety validations**
   - Validate `strategy` is one of known strategies
   - Validate `query.type` is "SQL" or "SPARQL"
   - Validate confidence ≥ 0.5 threshold
   - SQL injection prevention (parameterized queries, string escaping)
   - SPARQL injection prevention (PREFIX validation, pattern validation)
   - On validation failure:
     - Log warning with details
     - Fallback to rule-based approach
     - Track fallback in metrics

5. ✅ **Add LLM response caching**
   - Cache key: `hash(user_text + schema_version)`
   - Store in memory: `{query_hash: llm_plan}`
   - TTL: 1 hour (configurable)
   - Reduces latency for repeated queries (~250ms → ~10ms)
   - Clear cache on schema changes

**Deliverables**:
- `LLMQueryExecutor` - Executes LLM-generated queries
- Query validators prevent injection/syntax errors
- Feature flag: `CAIG_USE_LLM_EXECUTION`
- Safety validations with fallback
- LLM plan caching (250ms → 10ms for cached queries)
- Execution traces show LLM vs rule-based path used

**Testing**:
- Integration tests with `CAIG_USE_LLM_EXECUTION=true`
- Verify all test queries execute correctly with LLM-generated SQL/SPARQL
- Verify fallback works on invalid queries or execution errors
- Verify cache reduces latency on repeated queries
- Security testing: validate injection prevention works

---

### Phase 4: Production Rollout
**Goal**: Make LLM primary path in production with monitoring and gradual adoption

**Tasks**:
1. ✅ **Performance optimization**
   - Measure p50, p95, p99 latency with LLM enabled
   - Optimize prompt token usage (minimize schema size)
   - Consider GPT-3.5-turbo for cost savings if accuracy acceptable
   - Set timeout: 5 seconds for LLM call (fallback on timeout)

2. ✅ **Error handling & monitoring**
   - Comprehensive error handling:
     - LLM API failure → fallback to rule-based
     - Invalid JSON response → fallback
     - Query validation failure → fallback
     - Low confidence (<0.5) → fallback
     - Timeout → fallback
   - Metrics to track:
     - `llm_query_success_rate`
     - `llm_query_fallback_rate`
     - `llm_query_latency_p95`
     - `llm_cache_hit_rate`
     - `query_validation_failure_rate`
   - Alerting:
     - Alert if fallback rate > 10%
     - Alert if latency p95 > 1 second
     - Alert if validation failures > 5%

3. ✅ **Documentation**
   - Update `CLAUDE.md` with LLM query planning section
   - Document prompt template and schema format
   - Add troubleshooting guide:
     - How to debug LLM query generation
     - How to update prompt for better query quality
     - When to use rule-based fallback
     - How to validate generated queries
   - Document environment variables and feature flags

4. ✅ **Gradual rollout plan**
   - Week 1: Enable `CAIG_USE_LLM_STRATEGY=true` (parallel planning only)
     - Monitor: LLM accuracy, query quality, disagreements with rule-based
     - Action: Iterate on prompt based on disagreements and query errors
   - Week 2: Enable `CAIG_USE_LLM_EXECUTION=true` for 10% of queries
     - Monitor: Query execution success rate, fallback rate, latency, RU costs
     - Action: Address any query generation or execution errors
   - Week 3: Increase to 50% of queries
     - Monitor: Same metrics, compare to baseline
     - Action: Optimize based on production patterns
   - Week 4: Increase to 100% of queries
     - Monitor: Full production metrics
     - Action: Keep rule-based as permanent fallback
   - Future: Flip default to `CAIG_USE_LLM_EXECUTION=true`

**Deliverables**:
- Production-ready LLM query planning system
- Comprehensive monitoring and alerting
- Updated documentation
- Gradual rollout plan executed
- Rule-based fallback as permanent safety net

**Success Criteria**:
- LLM query generation success rate ≥ 95% in production
- Fallback rate ≤ 5%
- Latency p95 ≤ 300ms (single LLM call, including caching)
- Query validation failure rate ≤ 2%
- Zero increase in query execution errors
- Handles complex queries correctly (negations, OR lists, compound filters)

---

## File Structure

### New Files to Create

```
web_app/
├── schemas/
│   └── cosmos_contracts_schema.json          # **NEW**: External DB schema definition
├── ontologies/
│   └── contracts.owl                         # Existing: OWL ontology for SPARQL
├── src/
│   └── services/
│       ├── llm_query_planner.py              # Phase 1: Single-call LLM planning (strategy + query)
│       ├── strategy_schema_builder.py        # Phase 1: Loads schema JSON + ontology OWL
│       ├── sql_validator.py                  # Phase 1: SQL query syntax validator
│       ├── sparql_validator.py               # Phase 1: SPARQL query syntax validator
│       └── llm_query_executor.py             # Phase 3: Executes LLM-generated queries
├── test_llm_strategy_comparison.py           # Phase 2: Test suite
├── generate_strategy_comparison_report.py    # Phase 2: Report generator
└── LLM_STRATEGY_PLAN.md                      # This document
```

### Files to Modify

```
web_app/
├── src/
│   └── services/
│       ├── contract_strategy_builder.py      # Phase 1: Add parallel LLM planning
│       ├── cosmos_nosql_service.py           # Phase 3: Execute LLM-generated SQL
│       ├── ontology_service.py               # Phase 3: Execute LLM-generated SPARQL
│       ├── rag_data_service.py               # Phase 3: Route to LLM executor
│       └── query_execution_tracker.py        # Phase 1: Add LLM comparison fields
└── CLAUDE.md                                 # Phase 4: Document LLM approach
```

---

## Advantages of LLM Approach

### 1. **Handles Complex Queries Naturally**
- ✅ OR lists: "California, Texas, or Florida"
- ✅ Negations: "not Alabama"
- ✅ Compound: "MSA with Microsoft in CA or TX but not AL"
- ✅ Natural variations: "contracts excluding Alabama and Florida"
- ✅ Implicit logic: "all states except Alabama"

### 2. **Single-Call Efficiency**
- ✅ One LLM call for both strategy + query (~250ms vs 450ms for two calls)
- ✅ LLM has full context when generating query (schema + ontology + strategy)
- ✅ No context loss between strategy decision and query generation
- ✅ Simpler implementation without coordination logic
- ✅ Token cost negligible (~$0.0002 per query including unused schemas)

### 3. **Maintainability**
- ✅ No brittle regex patterns to maintain
- ✅ Schema changes reflected in prompt, not code
- ✅ Easy to add new strategies or entity types
- ✅ Prompt tuning vs code changes
- ✅ Extensible to new query patterns automatically

### 4. **Explainability**
- ✅ LLM provides reasoning for strategy choice
- ✅ LLM shows actual query that will be executed
- ✅ Can show users why a strategy was chosen
- ✅ Easier debugging with explicit reasoning
- ✅ Confidence scores indicate certainty

### 5. **Safety**
- ✅ Rule-based fallback always available
- ✅ Query validation (SQL/SPARQL syntax) before execution
- ✅ Injection prevention (parameterized queries, string escaping)
- ✅ Gradual rollout with feature flags
- ✅ Comparison mode validates improvements
- ✅ Monitoring detects regressions

---

## Risks & Mitigations

### Risk 1: LLM Latency
**Impact**: ~250ms additional latency per query (single-call approach)
**Probability**: High
**Mitigation**:
- Cache identical queries (expect 70%+ cache hit rate for common queries)
- Cached queries: ~10ms latency (96% reduction)
- Async LLM call while preparing other data
- Set aggressive timeout (5 seconds)
- Use GPT-3.5-turbo if latency critical (faster, cheaper)
- Single-call approach already 45% faster than two-call (250ms vs 450ms)
- Acceptable trade-off for improved accuracy on complex queries

### Risk 2: LLM Cost
**Impact**: ~$0.001-0.002 per query with GPT-4 (includes DB schema + ontology)
**Probability**: Medium
**Mitigation**:
- Single-call approach saves one API call (50% cost reduction vs two-call)
- Use GPT-3.5-turbo for 10x cost reduction (~$0.0001 per query)
- Cache frequently asked queries (70%+ hit rate = 70% cost reduction)
- Token cost of unused schemas negligible (~$0.0002 difference)
- Still much cheaper than incorrect query execution wasting RUs
- Estimated cost: $5-25/month for typical usage (single-call approach)

### Risk 3: LLM Errors or Hallucinations (Query Generation)
**Impact**: Invalid or incorrect SQL/SPARQL query
**Probability**: Low (with validation)
**Mitigation**:
- Query syntax validation before execution (SQL/SPARQL validators)
- Strict JSON schema validation (reject malformed responses)
- Injection prevention (parameterized queries, string escaping)
- Rule-based fallback on validation failure or low confidence
- Confidence threshold (require ≥0.5, prefer ≥0.8)
- Monitoring and alerting on fallback rate and validation failures
- Gradual rollout catches issues early

### Risk 4: Prompt Drift (Model Updates)
**Impact**: Azure OpenAI model updates change LLM behavior
**Probability**: Low
**Mitigation**:
- Version prompts in configuration (track changes)
- Test suite catches regressions on model updates
- Pin specific model version if needed
- A/B test new models before switching

### Risk 5: Schema Changes Break Prompt
**Impact**: Database schema changes invalidate LLM prompt
**Probability**: Low
**Mitigation**:
- Schema builder auto-generates schema JSON (stays in sync)
- Version schema in prompt (detect mismatches)
- Test suite runs on schema changes
- Gradual rollout for schema updates

---

## Metrics & Success Criteria

### Phase 1 Metrics (Parallel Planning)
- ✅ LLM response rate: % of queries that get valid LLM plan (strategy + query)
- ✅ Query validation rate: % of generated queries that pass syntax validation
- ✅ LLM latency: p50, p95, p99 of LLM planning time
- ✅ Agreement rate: % where LLM strategy matches rule-based strategy

**Success**: ≥95% valid response rate, ≥98% query validation rate, ≤300ms p95 latency

### Phase 2 Metrics (Comparison)
- ✅ LLM accuracy: % matching expected strategy on test suite
- ✅ Query quality: % of generated queries that are syntactically correct
- ✅ Rule-based accuracy: % matching expected strategy
- ✅ Disagreement analysis: Where and why they differ

**Success**: LLM accuracy ≥90%, query quality ≥98%, handles all negations and OR lists correctly

### Phase 3 Metrics (Execution)
- ✅ Execution success rate: % of LLM-generated queries that execute without error
- ✅ Query validation failure rate: % of queries rejected by validators
- ✅ Fallback rate: % falling back to rule-based
- ✅ Cache hit rate: % of queries served from cache

**Success**: ≥95% execution success, ≤2% validation failures, ≤5% fallback rate, ≥60% cache hit

### Phase 4 Metrics (Production)
- ✅ All Phase 3 metrics in production environment
- ✅ Query correctness: % returning expected results (spot check)
- ✅ Query generation quality: % of queries matching expected SQL/SPARQL patterns
- ✅ RU efficiency: Average RU cost vs baseline

**Success**: ≥95% success rate, ≤5% fallback, no regression in RU costs

---

## Timeline & Effort Estimates

| Phase | Tasks | Estimated Hours | Dependencies |
|-------|-------|----------------|--------------|
| **Phase 1: Foundation** | LLMQueryPlanner (single-call), StrategySchemaBuilder, SQL/SPARQL validators, parallel planning in ContractStrategyBuilder | 5-7 hours | None |
| **Phase 2: Validation** | Test suite (50+ queries), comparison report, query quality validation, prompt iteration | 6-8 hours | Phase 1 |
| **Phase 3: Execution** | LLMQueryExecutor, execute LLM-generated queries, feature flag, safety validations | 6-8 hours | Phase 2 |
| **Phase 4: Rollout** | Performance tuning, monitoring, documentation, gradual rollout | 4-6 hours | Phase 3 |
| **Total** | End-to-end implementation | **21-29 hours** | Sequential |

**Recommended Approach**: Implement in phases with validation gates between each phase.

---

## Next Steps

### Immediate Actions (Before Starting Implementation)

1. ✅ **Review and approve this plan**
   - Stakeholder sign-off on approach
   - Agreement on phases and timeline

2. ✅ **Validate LLM concept with prototype**
   - Create minimal prompt (just strategies, no schema)
   - Test with 10 sample queries manually
   - Verify JSON response format works
   - Confirm reasoning quality
   - **Estimated time**: 1-2 hours

3. ✅ **Set up development environment**
   - Ensure Azure OpenAI access and API key
   - Choose model: GPT-4 or GPT-3.5-turbo
   - Set up test environment variable flags
   - **Estimated time**: 30 minutes

### Phase 1 Kickoff (After Approval)

1. **Create schema definition file** `schemas/cosmos_contracts_schema.json`
2. Create `StrategySchemaBuilder` class (loads schema JSON + ontology OWL)
3. Create `LLMQueryPlanner` class (single-call for strategy + query generation)
4. Create `SQLValidator` and `SPARQLValidator` classes
5. Update `ContractStrategyBuilder` for parallel LLM planning
6. Add `CAIG_USE_LLM_STRATEGY` environment variable
7. Run initial tests with 10 queries
8. Validate query syntax and quality
9. Review LLM plans (strategy + query + reasoning)

**Decision Gate**: LLM responses must be valid JSON with reasonable strategy choices before proceeding to Phase 2.

---

## References

- **Current Implementation**: `web_app/src/services/contract_strategy_builder.py` (rule-based)
- **Query Optimizer**: `web_app/src/services/query_optimizer.py` (to be enhanced/replaced)
- **Execution Tracking**: `web_app/EXECUTION_TRACKING.md`
- **Negation Support**: `web_app/NEGATION_SUPPORT.md` (current regex-based approach)
- **Azure OpenAI Docs**: https://learn.microsoft.com/en-us/azure/ai-services/openai/

---

## Phase 2 Implementation Options

After completing Phase 1 (parallel LLM planning), you have multiple paths forward for Phase 2 validation and beyond. These options can be pursued independently or in combination.

### Option A: Enhanced Testing ✅ **COMPLETED**
**Purpose**: Comprehensive validation of LLM query planning with diverse test cases

**Status**: Implemented in `test_llm_comprehensive.py`

**Coverage**:
- **85 diverse test queries** across 8 categories:
  - Simple entity queries (10)
  - Negation queries (10)
  - OR list queries (10)
  - Aggregation queries (10)
  - Graph traversal queries (10)
  - Vector search queries (10)
  - Hybrid queries - entity + content/clause type (15)
  - Edge cases (10)

**Key Features**:
- Flexible strategy matching (accepts multiple valid strategies with `_OR_` syntax)
- Comprehensive validation (syntax, strategy, confidence, query type)
- Detailed analysis report with Phase 2 decision criteria
- Category-based breakdown and performance metrics

**Example Queries**:
- "Which contracts are governed by Alabama and contain an indemnification clause" (uses `contract_clauses` collection)
- "Find contracts with Microsoft OR Google OR Amazon"
- "Show contracts NOT governed by New York"
- "What is the total value of contracts in California?"

**Deliverables**:
- `test_llm_comprehensive.py` - Comprehensive test suite
- `test_results_comprehensive.json` - Detailed test results
- `test_report_comprehensive.txt` - Analysis report with recommendations

**Decision Criteria** (from test report):
- ✅ Strategy match rate ≥ 70%
- ✅ Query validation rate = 100%
- ✅ Average confidence ≥ 0.8
- ✅ Confidence for matches ≥ 0.8
- ✅ No critical edge cases where LLM fails

**Next Step**: Run `python test_llm_comprehensive.py` to validate Phase 1 implementation

---

### Option B: Production Monitoring Setup
**Purpose**: Collect real-world comparison data for Phase 2 validation

**Implementation Tasks**:

1. **Analysis Scripts**
   - Parse execution traces from `tmp/` directory
   - Extract LLM comparison metrics (strategy match rate, confidence distribution)
   - Aggregate data over time periods (daily, weekly, monthly)
   - Generate trend analysis and anomaly detection

2. **Dashboard/Reporting**
   - Create web dashboard showing:
     - Strategy match/mismatch trends over time
     - Confidence score distribution and histogram
     - Query validation rate and failure patterns
     - RU cost comparison (LLM estimated vs actual execution)
     - Query latency distribution (p50, p95, p99)
   - Export reports in JSON/CSV/PDF for analysis
   - Integration with existing monitoring tools

3. **Alerting System**
   - Alert on validation failures (syntax errors, injection attempts)
   - Alert on low confidence scores (< 0.5 threshold)
   - Alert on high strategy mismatch rate (> 40%)
   - Alert on query execution failures or timeout
   - Integration with Slack/email/PagerDuty

4. **Data Collection Period**
   - **Recommended**: 1-2 weeks in production with `CAIG_USE_LLM_STRATEGY=true`
   - **Minimum queries**: 1000+ diverse user queries
   - Capture edge cases and real-world patterns
   - Track user query diversity and complexity

**Files to Create**:
- `analyze_llm_traces.py` - Parse and analyze execution traces
- `llm_metrics_dashboard.py` - Web dashboard (FastAPI + HTML/JS)
- `llm_comparison_report.py` - Generate comparison reports
- `llm_alerts.py` - Alerting logic with configurable thresholds

**Metrics to Track**:
- `strategy_match_rate`: % LLM matches rule-based
- `confidence_avg`: Average LLM confidence score
- `confidence_distribution`: Histogram by confidence ranges
- `validation_pass_rate`: % queries passing syntax validation
- `query_complexity_score`: Measure query complexity (filters, operators, etc.)
- `fallback_trigger_rate`: % queries triggering fallback logic

**Success Criteria**:
- 1000+ queries analyzed over 1-2 weeks
- Clear trends identified for strategy matches/mismatches
- Confidence correlation with accuracy established
- Real-world edge cases documented

---

### Option C: Phase 3 - LLM Execution Mode
**Purpose**: Switch from logging to actual LLM execution (with fallback)

**Implementation Tasks**:

1. **Execution Mode Toggle**
   - Add `CAIG_LLM_EXECUTION_MODE` environment variable
   - Values:
     - `comparison_only` (Phase 1/2 - default)
     - `execution` (Phase 3 - use LLM queries)
     - `a_b_test` (hybrid - random 50/50 split)
   - Feature flag controls execution path in `RAGDataService`

2. **Fallback Logic Implementation**
   ```python
   if llm_plan and llm_plan.validation_status == "valid" and llm_plan.confidence >= 0.8:
       # Execute LLM-generated query
       result = llm_query_executor.execute_plan(llm_plan)
   else:
       # Fallback to rule-based approach
       logger.warning(f"LLM fallback: {validation_status}, confidence={confidence}")
       result = execute_rule_based_query(strategy)
   ```

3. **A/B Testing Framework**
   - Randomly route 50% of queries to LLM execution
   - Route other 50% to rule-based execution
   - Compare results between both approaches:
     - Result count (should match or improve)
     - RU cost (should be similar or lower)
     - Latency (include LLM planning overhead)
   - Track success rate, errors, and user satisfaction

4. **Safety Mechanisms**
   - **Circuit Breaker**: If LLM failure rate > 10% in 5-min window, switch to rule-based
   - **Query Timeout**: LLM query must complete within 10s (configurable)
   - **Result Validation**: Ensure LLM returns expected document format
   - **Gradual Rollout**: 10% → 25% → 50% → 100% over 2-4 weeks
   - **Rollback Plan**: Instant rollback via feature flag if issues detected

**Files to Modify**:
- `contract_strategy_builder.py` - Add execution mode logic and routing
- `rag_data_service.py` - Route to LLM execution based on mode
- `llm_query_executor.py` (NEW) - Execute LLM-generated queries with error handling

**Monitoring Additions**:
- `llm_execution_success_rate`: % successful LLM query executions
- `llm_vs_rulebased_result_diff`: % queries with different result counts
- `llm_ru_cost_ratio`: LLM RU cost / rule-based RU cost
- `circuit_breaker_trigger_count`: Number of times circuit breaker activated

**Testing Strategy**:
- Integration tests with `CAIG_LLM_EXECUTION_MODE=execution`
- Verify all 85 comprehensive test queries execute correctly
- Verify fallback triggers on invalid queries
- Security testing for SQL/SPARQL injection prevention
- Load testing to validate performance under production traffic

---

### Option D: Schema/Ontology Refinement
**Purpose**: Improve LLM accuracy through better schema and ontology descriptions

**Implementation Tasks**:

1. **Schema Enhancements** (`schemas/cosmos_contracts_schema.json`)
   - Add more field examples (3-5 examples per field)
   - Include common query patterns per collection
   - Add field relationships and foreign key constraints
   - Document query optimization strategies per field type
   - Add value validation rules and constraints
   - Include performance hints (indexed vs non-indexed fields)

2. **Ontology Improvements** (`ontologies/contracts.owl`)
   - Add more OWL classes for contract concepts (ContractClause subtypes, etc.)
   - Define additional object properties for relationships
   - Add datatype properties with range constraints
   - Include RDFS comments with detailed descriptions for LLM understanding
   - Add inverse properties for bidirectional navigation
   - Document SPARQL patterns for common queries

3. **Strategy Documentation Enhancement**
   - Add detailed strategy selection criteria with decision trees
   - Include RU cost estimates per strategy with formulas
   - Document fallback chains (primary → fallback → final fallback)
   - Provide query templates for each strategy type
   - Add anti-patterns (when NOT to use each strategy)
   - Include complexity scoring rules

4. **LLM Prompt Tuning**
   - Experiment with different system prompt structures
   - Add few-shot examples in prompt for common patterns
   - Optimize for CosmosDB SQL syntax specifics
   - Test different temperature settings (0.0 - 0.3 range)
   - A/B test prompt variations on test suite
   - Measure impact on strategy match rate and confidence

**Files to Modify**:
- `schemas/cosmos_contracts_schema.json` - Enhanced schema with richer metadata
- `ontologies/contracts.owl` - Improved ontology with more classes/properties
- `llm_query_planner.py` - Better system prompts and few-shot examples
- `strategy_schema_builder.py` - Enhanced context building logic

**Expected Improvements**:
- Strategy match rate: 70% → 85%+
- Confidence scores: 0.8 avg → 0.9+ avg
- Query validation rate: 98% → 99.5%+
- Edge case handling: Better coverage of unusual query patterns

---

## Recommended Implementation Path

### Conservative Path (Recommended for Production)
1. **Week 1**: Complete Option A (Enhanced Testing) ✅ DONE
2. **Week 2**: Analyze comprehensive test results
   - If criteria met (≥70% match, 100% validation, ≥0.8 confidence):
     - Proceed to Week 3
   - If criteria not met:
     - Implement Option D (refine schema/ontology)
     - Re-run tests, iterate until criteria met
3. **Week 3-4**: Implement Option B (Production Monitoring)
   - Deploy with `CAIG_USE_LLM_STRATEGY=true` (comparison only)
   - Collect 1-2 weeks of real-world data
   - Analyze patterns, edge cases, confidence correlation
4. **Week 5-6**: Implement Option C (LLM Execution) with gradual rollout
   - Start with 10% of queries
   - Monitor closely for 3-5 days
   - Increase to 50%, then 100% if metrics are good
5. **Week 7+**: Full production rollout
   - Keep rule-based as permanent fallback
   - Continue monitoring and refinement

### Aggressive Path (Quick Win Alternative)
If comprehensive test results are **excellent** (validation 100%, match ≥80%, confidence ≥0.85):
1. **Skip Option B** (production monitoring)
2. **Implement Option C immediately** with conservative fallback logic
3. **Deploy with gradual rollout**: 10% → 50% → 100% over 1 week
4. **Monitor closely** for first 48 hours
5. **Rollback instantly** if any issues detected

---

## Current Status & Next Actions

### Phase 1: Foundation ✅ COMPLETE
- ✅ Schema definition file created (`cosmos_contracts_schema.json`)
- ✅ StrategySchemaBuilder loads schema JSON + ontology OWL
- ✅ LLMQueryPlanner generates strategy + executable query in single call
- ✅ SQL/SPARQL validators prevent syntax errors and injection
- ✅ ContractStrategyBuilder runs parallel LLM planning
- ✅ Environment variable `CAIG_USE_LLM_STRATEGY` controls LLM usage
- ✅ Execution tracker captures LLM comparison data and generated queries
- ✅ Query text displayed in execution trace for debugging

### Option A: Enhanced Testing ✅ COMPLETE
- ✅ Comprehensive test suite with 85 queries created
- ✅ Covers all query types and edge cases
- ✅ Includes hybrid queries (entity + clause type)
- ✅ Generates detailed analysis report
- ⏳ **NEXT**: Run `python test_llm_comprehensive.py` to validate

### Options B, C, D: Ready to Implement
- 📋 Option B: Production monitoring (for real-world validation)
- 📋 Option C: LLM execution mode (switch from logging)
- 📋 Option D: Schema/ontology refinement (improve accuracy)
- 📋 Decision on path forward based on comprehensive test results

### Decision Point
After running comprehensive tests:
1. **Review test report** - Check if Phase 2 criteria are met
2. **Analyze mismatches** - Determine if LLM reasoning is sound
3. **Choose implementation path**:
   - Conservative: Option B → C (monitor then execute)
   - Aggressive: Option C directly (execute with fallback)
   - Refinement: Option D first (improve accuracy)

---

## Document History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-10-02 | 1.0 | Initial plan created | Claude Code |
| 2025-10-03 | 1.1 | Phase 1 implementation completed | Claude Code |
| 2025-10-03 | 1.2 | Option A (comprehensive testing) completed | Claude Code |
| 2025-10-04 | 2.0 | Added Phase 2 implementation options (A/B/C/D) | Claude Code |

---

**End of Document**
