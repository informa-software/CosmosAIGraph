# LLM Execution Mode - Implementation Guide

## Overview

**Phase 3: LLM Execution Mode** is now implemented. The system can execute LLM-generated queries directly instead of just comparing them to rule-based queries.

## Implementation Status

✅ **COMPLETE** - All components implemented and tested

### Components Created

1. **LLMQueryExecutor** (`src/services/llm_query_executor.py`)
   - Executes LLM-generated SQL and SPARQL queries
   - Validates queries before execution (confidence threshold, syntax validation)
   - Routes SQL to CosmosNoSQLService, SPARQL to OntologyService
   - Returns ExecutionResult with documents, RU cost, timing, and error handling

2. **Execution Mode Support** (ContractStrategyBuilder)
   - Added `CAIG_LLM_EXECUTION_MODE` environment variable
   - Three modes: `comparison_only`, `execution`, `a_b_test`

3. **LLM Execution Routing** (RAGDataService)
   - Routes queries to LLM execution when mode is enabled
   - Falls back to rule-based on validation failure or execution error
   - Tracks execution path (LLM vs rule-based) in execution tracker

4. **Fallback Logic**
   - Confidence threshold: >= 0.5 required
   - SQL/SPARQL syntax validation
   - Automatic fallback to rule-based on any failure
   - Fallback count tracked in execution traces

## Configuration

### Environment Variables

```bash
# Enable LLM query planning
CAIG_USE_LLM_STRATEGY=true

# Set execution mode
CAIG_LLM_EXECUTION_MODE=execution  # Options: comparison_only, execution, a_b_test
```

### Execution Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `comparison_only` | LLM plans logged, rule-based executes | Phase 1/2 - Analysis only |
| `execution` | LLM queries execute, fallback on failure | Phase 3 - Production use |
| `a_b_test` | Random 50/50 split for testing | A/B testing and validation |

## Testing

### Unit Tests (No Azure Resources Required)

Run unit tests to validate execution logic with mocked services:

```bash
python test_llm_executor_unit.py
```

Tests cover:
- ✅ SQL execution success
- ✅ SQL validation failure (low confidence)
- ✅ SPARQL execution success
- ✅ Unknown query type handling
- ✅ Execution error handling

**Result**: All 5 tests passing

### Integration Tests (Requires Azure Resources)

For full integration testing with live Azure services:

```bash
# Set environment variables
export CAIG_USE_LLM_STRATEGY=true
export CAIG_LLM_EXECUTION_MODE=execution
export CAIG_GRAPH_MODE=contracts

# Run integration test
python test_llm_execution_mode.py
```

Tests real queries:
1. Simple entity query (Delaware)
2. Multi-entity query (MSA + Microsoft)
3. Complex query (Alabama + indemnification clause)
4. Aggregation query (highest value contracts)
5. Semantic query (cloud services)

### Comprehensive Test Suite

Run all 85 test queries from Phase 2:

```bash
export CAIG_USE_LLM_STRATEGY=true
export CAIG_LLM_EXECUTION_MODE=execution
python test_llm_comprehensive.py
```

## How It Works

### Execution Flow

```
User Query
    ↓
ContractStrategyBuilder.build_strategy()
    ↓
[Parallel Processing]
    ↓                           ↓
Rule-Based Strategy      LLMQueryPlanner.plan_query()
    ↓                           ↓
    ↓                    LLMQueryPlan (strategy + query)
    ↓                           ↓
RAGDataService.get_database_rag_data()
    ↓
[Check execution mode]
    ↓
    ├─→ execution mode + valid plan?
    │       ↓
    │   _execute_llm_query()
    │       ↓
    │   LLMQueryExecutor.execute_plan()
    │       ↓
    │       ├─→ Validate (confidence, syntax, strategy)
    │       ├─→ Route to SQL/SPARQL service
    │       └─→ Return ExecutionResult
    │           ↓
    │   [Success] → Return documents
    │   [Failure] → Fall back to rule-based ↓
    │
    └─→ comparison_only mode OR invalid plan
            ↓
    Execute rule-based strategy
            ↓
    Return documents
```

### Validation Checks

Before executing LLM queries:

1. **Confidence Threshold**: >= 0.5 required
2. **Syntax Validation**: SQL/SPARQL validators check query syntax
3. **Strategy Validation**: Strategy must be in known list
4. **Service Availability**: Required service (CosmosDB/Ontology) must be configured

### Fallback Conditions

Falls back to rule-based when:
- Confidence < 0.5
- Invalid SQL/SPARQL syntax
- Unknown query type
- Unknown strategy
- Service unavailable
- Execution exception

## Execution Traces

Execution traces now show:

```
Strategy Path: CONTRACT_DIRECT
Query Type: SQL
Query Execution Time: 247ms
RU Cost: 12.5

LLM Generated Query:
  SELECT * FROM c
  WHERE c.governing_law_state = 'Alabama'
  AND EXISTS(SELECT VALUE 1 FROM clause IN c.clauses
             WHERE clause.type = 'indemnification')

Documents Retrieved: 5
```

## Next Steps

### Option B: Production Monitoring (Recommended)

Implement production monitoring before wider rollout:

1. **Success Rate Tracking**
   - LLM execution vs fallback ratio
   - Query type distribution
   - Strategy selection patterns

2. **Performance Metrics**
   - Execution time comparison (LLM vs rule-based)
   - RU cost analysis
   - Confidence score distribution

3. **Quality Monitoring**
   - Result accuracy validation
   - User satisfaction feedback
   - A/B test analysis

### Option D: Schema Refinement

Improve LLM query generation:

1. **Enhanced Schema Information**
   - Add sample values to schema
   - Include relationship descriptions
   - Document query patterns

2. **Few-Shot Examples**
   - Add example queries to prompts
   - Include common patterns
   - Show best practices

## Files Modified

### Created
- `src/services/llm_query_executor.py` - Query execution engine
- `test_llm_executor_unit.py` - Unit tests
- `test_llm_execution_mode.py` - Integration tests
- `LLM_EXECUTION_MODE_GUIDE.md` - This guide

### Modified
- `src/services/contract_strategy_builder.py` - Added execution mode support
- `src/services/rag_data_service.py` - Added LLM execution routing
- `src/services/query_execution_tracker.py` - Display LLM query text
- `LLM_STRATEGY_PLAN.md` - Updated with Phase 3 status

## References

See `LLM_STRATEGY_PLAN.md` for:
- Complete architecture overview
- Decision matrix
- Implementation phases
- Future enhancements
