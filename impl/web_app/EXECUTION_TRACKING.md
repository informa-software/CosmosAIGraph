# Query Execution Tracking & Visualization

Real-time execution tracking for the multi-collection RAG optimization system, showing actual query paths including fallbacks and performance metrics.

## Overview

The Query Execution Tracker captures and visualizes:
- **Planned vs Actual Strategy**: Shows what was planned and what actually executed
- **Execution Steps**: Detailed breakdown of each database operation
- **Fallback Chain**: Tracks when and why fallbacks occurred
- **Performance Metrics**: RU costs, timing, and document counts
- **Recommendations**: Actionable insights based on execution patterns

## Features

### 1. **ASCII Visualization**
Clean, terminal-friendly execution traces with:
- ✅ Success indicators
- ❌ Failure markers
- ⚠️  Fallback warnings
- 💡 Smart recommendations
- 💰 Performance savings calculations
- 📝 **Actual SQL/SPARQL queries executed**

### 2. **Minimal Code Impact**
- Optional tracking (enabled by default)
- Zero impact when disabled
- Backward compatible with existing code
- No breaking changes to APIs

### 3. **Multi-Strategy Support**
Tracks all query strategies:
- **ENTITY_FIRST**: Query entity collection → batch retrieve contracts
- **ENTITY_AGGREGATION**: Return pre-computed statistics
- **CONTRACT_DIRECT**: Direct contract queries with filters
- **GRAPH_TRAVERSAL**: Graph-based relationship queries
- **VECTOR_SEARCH**: Fallback vector similarity search

## Usage

### In Code

```python
from src.services.rag_data_service import RAGDataService

# Enable tracking (default)
rdr = await rag_data_svc.get_rag_data(
    user_text="Show contracts governed by Florida",
    max_doc_count=10,
    enable_tracking=True  # Optional, defaults to True
)

# Access execution trace
tracker = rdr.get_execution_tracker()
if tracker:
    # Get ASCII visualization
    print(tracker.visualize_ascii())

    # Or get structured data
    trace_data = tracker.to_dict()
```

### In Debug Logs & Files

When `CAIG_LOG_LEVEL=debug`, execution traces are automatically logged and saved:

```bash
# Set debug level
export CAIG_LOG_LEVEL=debug

# Run web app
python web_app.py

# Traces appear in:
# 1. Console logs (stdout)
# 2. tmp/execution_trace_<timestamp>.txt (ASCII visualization)
# 3. tmp/execution_trace_<timestamp>.json (structured data)
# 4. tmp/ai_conv_rdr.json (full RAG result including trace)
```

**Example saved files**:
- `tmp/execution_trace_1705345425.txt` - Human-readable ASCII trace
- `tmp/execution_trace_1705345425.json` - Machine-readable JSON trace
- `tmp/ai_conv_rdr.json` - Complete RAG result with execution trace

### In API Responses

Execution trace is included in RAG data result:

```json
{
  "type": "RAGDataResult",
  "user_text": "Show contracts governed by Florida",
  "strategy": ["db"],
  "rag_docs": [...],
  "execution_trace": {
    "query": "Show contracts governed by Florida",
    "planned_strategy": "db",
    "actual_strategy": "ENTITY_FIRST",
    "total_duration_ms": 123,
    "total_ru_cost": 13.7,
    "fallback_count": 0,
    "steps": [
      {
        "step_number": 1,
        "name": "Entity Collection Query",
        "strategy": "ENTITY_FIRST",
        "collection": "governing_law_states",
        "status": "success",
        "duration_ms": 45,
        "ru_cost": 1.2,
        "documents_found": 1
      },
      {
        "step_number": 2,
        "name": "Batch Contract Retrieval",
        "strategy": "ENTITY_FIRST",
        "collection": "contracts",
        "status": "success",
        "duration_ms": 78,
        "ru_cost": 12.5,
        "documents_found": 12
      }
    ]
  }
}
```

## Example Visualizations

### Successful Optimized Query
```
╔══════════════════════════════════════════════════════════════════════╗
║ QUERY EXECUTION TRACE                                                ║
║ Query: Show all contracts governed by Florida                        ║
║ Timestamp: 2025-01-15 14:23:45.123                                   ║
╚══════════════════════════════════════════════════════════════════════╝

PLANNED STRATEGY: db
ACTUAL EXECUTION PATH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Step 1: Entity Collection Query                    [SUCCESS] 45ms
   ├─ Collection: governing_law_states
   ├─ Key: florida
   ├─ SQL: SELECT * FROM c WHERE c.normalized_name = 'florida'
   ├─ Documents Found: 1
   └─ RU Cost: 1.2

✅ Step 2: Batch Contract Retrieval                   [SUCCESS] 78ms
   ├─ Collection: contracts
   ├─ Method: Batch Read
   ├─ Documents Found: 12
   └─ RU Cost: 12.5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION SUMMARY:
  Status: ✅ SUCCESS
  Total Time: 123ms
  Total RU Cost: 13.7
  Documents Returned: 12
  Fallbacks Used: 0

PERFORMANCE COMPARISON:
  ✅ ENTITY_FIRST (used):     13.7 RUs   123ms
  ❌ CONTRACT_DIRECT:         45.0 RUs   340ms  (↑ 228% cost)

  💰 SAVINGS: 31.3 RUs (69% reduction)
```

### Fallback Scenario
```
╔══════════════════════════════════════════════════════════════════════╗
║ QUERY EXECUTION TRACE                                                ║
║ Query: Contracts with Acme Corp in California                        ║
╚══════════════════════════════════════════════════════════════════════╝

PLANNED STRATEGY: db
ACTUAL EXECUTION PATH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Step 1: Entity Collection Query                    [FAILED] 23ms
   ├─ Collection: contracting_parties
   ├─ Key: acme_corp
   ├─ Error: Entity not found
   └─ RU Cost: 1.0

⚠️  FALLBACK TRIGGERED: Switching to VECTOR_SEARCH strategy

✅ Step 2: Vector Search (Fallback)                   [SUCCESS] 445ms
   ├─ Collection: contracts
   ├─ Documents Found: 3 (fuzzy matches)
   └─ RU Cost: 45.2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION SUMMARY:
  Status: ⚠️  SUCCESS (with fallbacks)
  Total Time: 468ms
  Total RU Cost: 46.2
  Documents Returned: 3
  Fallbacks Used: 1

FALLBACK CHAIN:
  1️⃣  ENTITY_FIRST (planned) → ❌ Entity not found
  2️⃣  VECTOR_SEARCH (fallback) → ✅ Found fuzzy matches

RECOMMENDATIONS:
  💡 Consider adding 'acme_corp' to entity catalog
  💡 Fuzzy matching suggests: 'acme_corporation', 'acme_corp_llc'
```

### SPARQL Graph Query
```
╔══════════════════════════════════════════════════════════════════════╗
║ QUERY EXECUTION TRACE                                                ║
║ Query: What contracts depend on Microsoft libraries?                 ║
╚══════════════════════════════════════════════════════════════════════╝

PLANNED STRATEGY: graph
ACTUAL EXECUTION PATH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Step 1: SPARQL Query Generation & Execution        [SUCCESS] 234ms
   ├─ Collection: graph
   ├─ SPARQL:
   │    PREFIX caig: <http://cosmosdb.com/caig#>
   │    SELECT ?contract ?library WHERE {
   │      ?contract caig:dependsOn ?library .
   │      ?library caig:vendor "Microsoft"
   │    }
   ├─ Documents Found: 15
   └─ RU Cost: 10.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION SUMMARY:
  Status: ✅ SUCCESS
  Total Time: 234ms
  Total RU Cost: 10.0
  Documents Returned: 15
  Fallbacks Used: 0
```

### Multi-Filter SQL Query
```
╔══════════════════════════════════════════════════════════════════════╗
║ QUERY EXECUTION TRACE                                                ║
║ Query: Show MSA contracts with Microsoft in Washington               ║
╚══════════════════════════════════════════════════════════════════════╝

PLANNED STRATEGY: db
ACTUAL EXECUTION PATH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Step 1: Direct Contract Query                      [SUCCESS] 156ms
   ├─ Collection: contracts
   ├─ Filter: {'contract_type': 'msa', 'contracting_party': 'microsoft', ...}
   ├─ SQL:
   │    SELECT TOP 10 * FROM c
   │    WHERE c.contract_type = 'msa'
   │      AND c.contracting_party = 'microsoft'
   │      AND c.governing_law_state = 'washington'
   ├─ Documents Found: 3
   └─ RU Cost: 8.3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION SUMMARY:
  Status: ✅ SUCCESS
  Total Time: 156ms
  Total RU Cost: 8.3
  Documents Returned: 3
  Fallbacks Used: 0
```

## Testing

Run the test suite to see execution tracking in action:

```bash
# Ensure you're in contracts mode
export CAIG_GRAPH_MODE=contracts

# Run test suite
cd web_app
python test_execution_tracker.py
```

The test suite demonstrates:
1. ✅ Entity-first optimized queries
2. ✅ Aggregation with pre-computed stats
3. ✅ Multi-filter direct queries
4. ✅ Fallback scenarios

## Performance Impact

- **Tracking Overhead**: < 1ms per query
- **Memory**: ~2KB per tracked query
- **Storage**: Trace data included in API response (optional)

## Saved Execution Traces

### File Locations

All execution traces are saved to the `tmp/` directory when debug logging is enabled:

| File | Format | Contents | Usage |
|------|--------|----------|-------|
| `execution_trace_<timestamp>.txt` | ASCII | Human-readable visualization | Quick review, debugging |
| `execution_trace_<timestamp>.json` | JSON | Structured trace data | Analysis, dashboards |
| `ai_conv_rdr.json` | JSON | Complete RAG result + trace | Full context debugging |

### Trace File Contents

**ASCII File (`execution_trace_<timestamp>.txt`)**:
```
╔══════════════════════════════════════════════════════════════════════╗
║ QUERY EXECUTION TRACE                                                ║
║ Query: Show all contracts governed by Florida                        ║
╚══════════════════════════════════════════════════════════════════════╝

✅ Step 1: Entity Collection Query [SUCCESS] 45ms
   ├─ SQL: SELECT * FROM c WHERE c.normalized_name = 'florida'
   └─ RU Cost: 1.2

EXECUTION SUMMARY:
  Total RU Cost: 13.7
  Documents Returned: 12
```

**JSON File (`execution_trace_<timestamp>.json`)**:
```json
{
  "query": "Show all contracts governed by Florida",
  "planned_strategy": "db",
  "actual_strategy": "ENTITY_FIRST",
  "total_duration_ms": 123,
  "total_ru_cost": 13.7,
  "steps": [
    {
      "step_number": 1,
      "name": "Entity Collection Query",
      "collection": "governing_law_states",
      "status": "success",
      "duration_ms": 45,
      "ru_cost": 1.2,
      "metadata": {
        "sql": "SELECT * FROM c WHERE c.normalized_name = 'florida'"
      }
    }
  ]
}
```

### File Management

- **Automatic Cleanup**: Consider adding a cleanup script for old trace files
- **Retention**: Trace files are not automatically deleted
- **Size**: Each trace is typically < 10KB
- **Timestamps**: Unix timestamps allow chronological sorting

**Cleanup Script Example**:
```bash
# Delete trace files older than 7 days
find tmp/ -name "execution_trace_*.txt" -mtime +7 -delete
find tmp/ -name "execution_trace_*.json" -mtime +7 -delete
```

## Configuration

### Enable/Disable Tracking

```python
# Disable tracking for a specific query
rdr = await rag_data_svc.get_rag_data(
    user_text=query,
    enable_tracking=False
)
```

### Debug Logging

```bash
# Show execution traces in logs
export CAIG_LOG_LEVEL=debug

# Hide execution traces
export CAIG_LOG_LEVEL=info
```

## Architecture

### Components

1. **QueryExecutionTracker** (`query_execution_tracker.py`)
   - Tracks execution steps in real-time
   - Calculates performance metrics
   - Generates visualizations

2. **ExecutionStep** (dataclass)
   - Individual step tracking
   - Status, timing, and metadata
   - Fallback indicators

3. **RAGDataResult** (enhanced)
   - Optional tracker attachment
   - Automatic trace inclusion in response
   - Backward compatible

4. **RAGDataService** (minimal changes)
   - Tracker initialization
   - Step tracking in optimized paths
   - Fallback detection

## Future Enhancements

Potential additions (not yet implemented):
- **Mermaid Diagrams**: Auto-generate flowcharts for documentation
- **D3.js Interactive**: Web-based interactive visualization
- **Historical Analysis**: Track patterns over time
- **ML-based Optimization**: Learn from execution patterns
- **Caching Recommendations**: Suggest caching opportunities

## Files Added/Modified

### New Files
- `web_app/src/services/query_execution_tracker.py` - Core tracker
- `web_app/test_execution_tracker.py` - Test suite
- `web_app/EXECUTION_TRACKING.md` - This documentation

### Modified Files
- `web_app/src/services/rag_data_result.py` - Added tracker support
- `web_app/src/services/rag_data_service.py` - Integrated tracking
- `web_app/web_app.py` - Added debug visualization

## Backward Compatibility

✅ **Fully backward compatible**:
- Tracking is optional (defaults to enabled)
- No breaking API changes
- Existing code works unchanged
- Trace data only added when tracker present

## See Also

- [Query Optimizer Documentation](query_optimizer.py) - Multi-collection optimization
- [Contract Strategy Builder](contract_strategy_builder.py) - Strategy determination
- [CLAUDE.md](../CLAUDE.md) - Project documentation
