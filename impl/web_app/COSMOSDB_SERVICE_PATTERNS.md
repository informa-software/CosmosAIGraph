# CosmosDB NoSQL Service Usage Patterns

## ⚠️ CRITICAL: Correct Method Names

The `CosmosNoSQLService` class uses **specific method names** that must be followed. Using incorrect method names will result in `AttributeError` at runtime.

## Common Mistakes to Avoid

### ❌ INCORRECT (Will cause AttributeError)
```python
# These methods DO NOT EXIST:
await cosmos.query_documents(container, query, params)  # ❌ NO
await cosmos.get_document(container, id, pk)            # ❌ NO
await cosmos.upsert_document(container, doc)            # ❌ NO
```

### ✅ CORRECT Method Names
```python
# These are the actual methods:
await cosmos.query_items(sql, cross_partition, pk)           # ✅ YES
await cosmos.parameterized_query(sql, params, cross_partition, pk)  # ✅ YES
await cosmos.upsert_item(doc)                                # ✅ YES
```

## Required Pattern: set_container() First

**CRITICAL:** You must call `set_container()` before EVERY operation:

```python
# ✅ CORRECT PATTERN
cosmos.set_container("my_container")
await cosmos.upsert_item(document)

cosmos.set_container("my_container")
results = await cosmos.query_items(query, cross_partition=True)
```

## Complete Usage Examples

### 1. Query Items (Simple)
```python
# Query with SQL string
query = "SELECT * FROM c WHERE c.status = 'active'"
cosmos.set_container("my_container")
results = await cosmos.query_items(
    query,
    cross_partition=True,  # Set to False if querying within single partition
    pk=None,               # Provide partition key value if querying single partition
    max_items=100          # Optional, defaults to 100
)
```

### 2. Parameterized Query (Recommended for user input)
```python
# Use parameterized queries to prevent injection and handle special characters
query = "SELECT * FROM c WHERE c.id = @id AND c.type = @type"
parameters = [
    {"name": "@id", "value": "my-id"},
    {"name": "@type", "value": "clause"}
]

cosmos.set_container("my_container")
results = await cosmos.parameterized_query(
    query,
    parameters,
    cross_partition=True,
    pk=None,
    max_items=100
)
```

### 3. Get Single Document by ID
```python
# No direct get_document() method - use query instead
query = "SELECT * FROM c WHERE c.id = @id"
parameters = [{"name": "@id", "value": document_id}]

cosmos.set_container("my_container")
results = await cosmos.parameterized_query(
    query,
    parameters,
    cross_partition=False,  # Can be False if you provide partition key
    pk=partition_key_value   # Provide the partition key value
)

if results:
    document = results[0]  # Get first result
```

### 4. Upsert (Insert or Update) Document
```python
# Document must have 'id' and partition key field
document = {
    "id": "my-id",
    "type": "clause",  # Partition key field
    "name": "Sample Clause",
    "content": "..."
}

cosmos.set_container("my_container")
await cosmos.upsert_item(document)
```

### 5. Vector Search with Embeddings
```python
# Vector search using VectorDistance function
query = """
SELECT TOP @top_k c.*, VectorDistance(c.embedding, @embedding) AS similarity
FROM c
WHERE c.type = 'clause' AND c.status = 'active'
ORDER BY VectorDistance(c.embedding, @embedding)
"""

parameters = [
    {"name": "@top_k", "value": 5},
    {"name": "@embedding", "value": embedding_vector}  # List of floats
]

cosmos.set_container("my_container")
results = await cosmos.parameterized_query(
    query,
    parameters,
    cross_partition=True
)
```

## Method Signature Reference

### query_items()
```python
async def query_items(
    self,
    sql: str,                      # SQL query string
    cross_partition: bool = False, # True to query across all partitions
    pk: str | None = None,         # Partition key value if querying single partition
    max_items: int = 100           # Maximum items to return
) -> list[dict]
```

### parameterized_query()
```python
async def parameterized_query(
    self,
    sql_template: str,             # SQL query with @parameter placeholders
    sql_parameters: list[dict],    # List of {"name": "@param", "value": value}
    cross_partition: bool = False, # True to query across all partitions
    pk: str | None = None,         # Partition key value if querying single partition
    max_items: int = 100           # Maximum items to return
) -> list[dict]
```

### upsert_item()
```python
async def upsert_item(
    self,
    doc: dict  # Document with 'id' and partition key field
) -> dict  # Returns the upserted document
```

### set_container()
```python
def set_container(
    self,
    container_name: str  # Name of the container to use
) -> None
```

## Best Practices

### 1. Always Use Parameterized Queries for User Input
```python
# ❌ BAD - Vulnerable to injection, doesn't handle special characters
query = f"SELECT * FROM c WHERE c.name = '{user_input}'"

# ✅ GOOD - Safe and handles all characters correctly
query = "SELECT * FROM c WHERE c.name = @name"
parameters = [{"name": "@name", "value": user_input}]
```

### 2. Use Appropriate cross_partition Setting
```python
# Query within single partition (faster, lower RU cost)
cosmos.set_container("my_container")
results = await cosmos.query_items(
    query,
    cross_partition=False,
    pk="my-partition-key"
)

# Query across all partitions (slower, higher RU cost)
cosmos.set_container("my_container")
results = await cosmos.query_items(
    query,
    cross_partition=True
)
```

### 3. Always Call set_container() Before Operations
```python
# ❌ BAD - Will query wrong container or cause error
cosmos.set_container("container_a")
await cosmos.upsert_item(doc1)
await cosmos.upsert_item(doc2)  # Still uses container_a

# ✅ GOOD - Explicit container before each operation
cosmos.set_container("container_a")
await cosmos.upsert_item(doc1)

cosmos.set_container("container_b")
await cosmos.upsert_item(doc2)
```

### 4. Handle Empty Results
```python
cosmos.set_container("my_container")
results = await cosmos.query_items(query, cross_partition=True)

if results:
    # Process results
    for item in results:
        print(item)
else:
    # Handle no results found
    print("No documents found")
```

## Error Prevention Checklist

Before committing code that uses CosmosNoSQLService:

- [ ] Used `query_items()` or `parameterized_query()` (not `query_documents()`)
- [ ] Used `upsert_item()` (not `upsert_document()`)
- [ ] No calls to `get_document()` (use parameterized query instead)
- [ ] Called `set_container()` before EVERY operation
- [ ] Used parameterized queries for any user input or special characters
- [ ] Set appropriate `cross_partition` value based on query scope
- [ ] Handled empty result sets with `if results:` checks

## Historical Context

This document was created on October 28, 2025, after encountering multiple `AttributeError` issues when implementing the Clause Library service. The service incorrectly used method names like `query_documents()`, `get_document()`, and `upsert_document()` which don't exist in `CosmosNoSQLService`.

**Key lesson:** Always verify method names by checking the actual `cosmos_nosql_service.py` implementation rather than assuming standard naming patterns.
