# LLM Query Executor Async Fix

## Problem

The error:
```
CosmosNoSQLService.query_items() got an unexpected keyword argument 'container_name'
```

## Root Cause

The `LLMQueryExecutor` was calling `CosmosNoSQLService.query_items()` with incorrect parameters:

**Incorrect Call:**
```python
results = self.cosmos_service.query_items(
    container_name=collection,           # WRONG - parameter doesn't exist
    query=llm_plan.query_text,          # WRONG - should be 'sql'
    enable_cross_partition_query=True    # WRONG - should be 'cross_partition'
)
```

**Actual Method Signature:**
```python
async def query_items(self, sql: str, cross_partition: bool = False, pk: str | None = None, max_items: int = 100)
```

## Issues Fixed

### 1. **Parameter Names**
- ❌ `container_name` → Not in signature (container is set via `set_container()`)
- ❌ `query` → ✅ `sql`
- ❌ `enable_cross_partition_query` → ✅ `cross_partition`

### 2. **Async/Await**
- `query_items()` is an **async** method and must be awaited
- All methods in the execution chain needed to be made async

### 3. **Container Selection**
- CosmosNoSQLService uses `set_container(name)` to select the container
- Then `query_items()` operates on the current container
- No `container_name` parameter needed

### 4. **RU Cost Retrieval**
- ❌ `getattr(self.cosmos_service, 'last_request_charge', 0.0)` → Returns method object
- ✅ `self.cosmos_service.last_request_charge()` → Calls method to get RU cost
- Error: "unsupported format string passed to method.__format__"
- Cause: `last_request_charge` is a method, not an attribute

## Changes Made

### `llm_query_executor.py`

**1. Made `execute_plan()` async:**
```python
async def execute_plan(self, llm_plan: LLMQueryPlan, ...) -> ExecutionResult:
```

**2. Made `_execute_sql()` async and fixed API calls:**
```python
async def _execute_sql(self, llm_plan: LLMQueryPlan, timeout: float) -> ExecutionResult:
    # Set the container before querying
    self.cosmos_service.set_container(collection)

    # Execute query with correct parameters
    documents = await self.cosmos_service.query_items(
        sql=llm_plan.query_text,
        cross_partition=True
    )

    # Get RU cost - it's a method, must call it
    ru_cost = self.cosmos_service.last_request_charge()
```

**3. Made `_execute_sparql()` async:**
```python
async def _execute_sparql(self, llm_plan: LLMQueryPlan, timeout: float) -> ExecutionResult:
```

**4. Updated execute_plan to await method calls:**
```python
if llm_plan.query_type == "SQL":
    result = await self._execute_sql(llm_plan, timeout)
elif llm_plan.query_type == "SPARQL":
    result = await self._execute_sparql(llm_plan, timeout)
```

### `rag_data_service.py`

**Updated caller to await async method:**
```python
# Execute the query
result = await executor.execute_plan(plan_obj)
```

### `test_llm_executor_unit.py`

**1. Updated imports:**
```python
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock
```

**2. Made all test functions async:**
```python
async def test_sql_execution_success():
    # ...
    result = await executor.execute_plan(llm_plan)
```

**3. Updated mocks to use AsyncMock for async methods:**
```python
mock_cosmos.query_items = AsyncMock(return_value=[...])
mock_cosmos.last_request_charge = Mock(return_value=5.2)  # Method, not attribute
```

**4. Made main() async and run with asyncio:**
```python
async def main():
    # ...
    success = await test_func()

if __name__ == "__main__":
    success = asyncio.run(main())
```

## Correct Usage Pattern

```python
# 1. Create executor with CosmosDB service
executor = LLMQueryExecutor(cosmos_service=cosmos_service)

# 2. Create LLM plan
llm_plan = LLMQueryPlan(
    query_type="SQL",
    query_text="SELECT * FROM c WHERE c.governing_law_state = 'Alabama'",
    execution_plan={"collection": "contracts"},
    # ...
)

# 3. Execute (must await!)
result = await executor.execute_plan(llm_plan)

# 4. Process results
if result.success:
    for doc in result.documents:
        print(doc)
```

## Test Results

✅ All 5 unit tests passing:
1. SQL Execution Success
2. SQL Validation Failure
3. SPARQL Execution Success
4. Unknown Query Type
5. Execution Error Handling

## API Reference

### CosmosNoSQLService.query_items()

**Signature:**
```python
async def query_items(
    self,
    sql: str,                          # SQL query string
    cross_partition: bool = False,     # Enable cross-partition queries
    pk: str | None = None,             # Optional partition key filter
    max_items: int = 100               # Maximum items to return
) -> List[Dict]
```

**Usage:**
```python
# 1. Set the container first
cosmos_service.set_container("contracts")

# 2. Execute query
results = await cosmos_service.query_items(
    sql="SELECT * FROM c WHERE c.id = 'foo'",
    cross_partition=True
)

# 3. Results is a list of documents
for doc in results:
    process(doc)
```

### CosmosNoSQLService.set_container()

**Signature:**
```python
def set_container(self, cname: str) -> ContainerProxy
```

**Purpose:**
Sets the current container that subsequent operations will use. This is NOT async.

## Files Modified

- ✅ `src/services/llm_query_executor.py` - Made async, fixed API calls
- ✅ `src/services/rag_data_service.py` - Added await to executor call
- ✅ `test_llm_executor_unit.py` - Updated to async test pattern

## Error Summary

### Error 1: "got an unexpected keyword argument 'container_name'"
**Cause:** Using incorrect parameter names for `query_items()`
**Fix:** Use `sql`, `cross_partition` parameters and call `set_container()` first

### Error 2: "unsupported format string passed to method.__format__"
**Cause:** Trying to format a method object instead of calling it to get the value
**Fix:** Change `getattr(service, 'last_request_charge', 0.0)` to `service.last_request_charge()`

## Related Documentation

- Azure Cosmos Python SDK: https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-readme
- Async patterns in Python: https://docs.python.org/3/library/asyncio.html
- Python string formatting: https://docs.python.org/3/library/string.html#format-specification-mini-language
