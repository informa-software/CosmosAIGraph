# Phase 1 Testing Guide - Backend Infrastructure

## What We've Implemented

Phase 1 provides the backend infrastructure for storing analysis results:

✅ **CosmosDB Container**: `analysis_results` container with partitioning and indexing
✅ **Pydantic Models**: Type-safe models for comparison and query results
✅ **Service Layer**: `AnalysisResultsService` for CRUD operations
✅ **API Endpoints**: REST API for saving/retrieving results
✅ **Router Integration**: Registered in FastAPI application

## Setup Instructions

### 1. Create the CosmosDB Container

**Windows:**
```powershell
cd web_app
.\setup_analysis_results_container.ps1
```

**Linux/Mac:**
```bash
cd web_app
python setup_analysis_results_container.py
```

**Expected Output:**
```
Starting Analysis Results container setup...
Creating container: analysis_results
Partition key: /user_id
✓ Container 'analysis_results' ready

========================================
Analysis Results Container Setup Complete!
========================================
```

### 2. Start the Web Application

```powershell
cd web_app
.\web_app.ps1
```

The API will be available at: https://localhost:8000

### 3. Access API Documentation

Open in browser: **https://localhost:8000/docs**

You should see the new endpoints under **"analysis-results"** tag:
- POST `/api/analysis-results/comparison`
- POST `/api/analysis-results/query`
- GET `/api/analysis-results/results/{result_id}`
- GET `/api/analysis-results/user/{user_id}/results`
- GET `/api/analysis-results/user/{user_id}/statistics`
- DELETE `/api/analysis-results/results/{result_id}`

## Testing the API

### Test 1: Save a Comparison Result

**Endpoint:** `POST /api/analysis-results/comparison`

**Request Body:**
```json
{
  "user_id": "test@example.com",
  "standard_contract_id": "contract_abc_123",
  "compare_contract_ids": ["contract_def_456", "contract_ghi_789"],
  "comparison_mode": "full",
  "results": {
    "comparisons": [
      {
        "contract_id": "contract_def_456",
        "overall_similarity_score": 0.85,
        "risk_level": "low",
        "critical_findings": ["No major issues found"],
        "missing_clauses": [],
        "additional_clauses": []
      }
    ]
  },
  "metadata": {
    "title": "Test Comparison Report",
    "description": "Testing comparison storage",
    "execution_time_seconds": 2.5
  }
}
```

**Expected Response:**
```json
{
  "result_id": "result_1729795200_abc12345",
  "message": "Comparison results saved successfully"
}
```

**Save the `result_id` for the next tests!**
result_1761263389839_eadd53fd
---

### Test 2: Save a Query Result

**Endpoint:** `POST /api/analysis-results/query`

**Request Body:**
```json
{
  "user_id": "test@example.com",
  "query_text": "Which of these contracts have the broadest indemnification for the contracting party?",
  "query_type": "natural_language",
  "contracts_queried": [
    {
      "contract_id": "contract_abc_123",
      "filename": "Westervelt_Standard_MSA.json",
      "contract_title": "Westervelt Standard MSA"
    },
    {
      "contract_id": "contract_def_456",
      "filename": "ACME_Corp_Agreement.json",
      "contract_title": "ACME Corp Service Agreement"
    }
  ],
  "results": {
    "answer_summary": "Based on analysis, Contract ABC has the broadest indemnification coverage...",
    "ranked_contracts": [
      {
        "contract_id": "contract_abc_123",
        "filename": "Westervelt_Standard_MSA.json",
        "rank": 1,
        "score": 0.95,
        "reasoning": "This contract provides the most comprehensive indemnification...",
        "relevant_clauses": [
          {
            "clause_type": "Indemnification",
            "clause_text": "Party A shall indemnify...",
            "analysis": "Covers all potential liabilities"
          }
        ]
      }
    ],
    "execution_metadata": {
      "contracts_analyzed": 2,
      "query_time_seconds": 3.2,
      "llm_model": "gpt-4"
    }
  },
  "metadata": {
    "title": "Indemnification Analysis",
    "description": "Query across 2 contracts"
  }
}
```

**Expected Response:**
```json
{
  "result_id": "result_1729795300_def67890",
  "message": "Query results saved successfully"
}
```
result_1761263468170_b35a002f
---

### Test 3: Retrieve a Result

**Endpoint:** `GET /api/analysis-results/results/{result_id}?user_id=test@example.com`

Use the `result_id` from Test 1 or Test 2.

**Expected Response:**
```json
{
  "id": "result_1729795200_abc12345",
  "result_id": "result_1729795200_abc12345",
  "result_type": "comparison",
  "user_id": "test@example.com",
  "created_at": "2025-10-23T14:30:00Z",
  "status": "completed",
  "metadata": {
    "title": "Test Comparison Report",
    "description": "Testing comparison storage",
    "execution_time_seconds": 2.5
  },
  "comparison_data": {
    "standard_contract_id": "contract_abc_123",
    "compare_contract_ids": ["contract_def_456", "contract_ghi_789"],
    "comparison_mode": "full",
    "results": { ... }
  }
}
```

---

### Test 4: List User Results

**Endpoint:** `GET /api/analysis-results/user/test@example.com/results`

**Optional Query Parameters:**
- `result_type=comparison` or `result_type=query`
- `limit=10`
- `offset=0`

**Expected Response:**
```json
{
  "results": [
    {
      "id": "result_1729795300_def67890",
      "result_type": "query",
      ...
    },
    {
      "id": "result_1729795200_abc12345",
      "result_type": "comparison",
      ...
    }
  ],
  "total_count": 2,
  "page": 1,
  "page_size": 50
}
```

---

### Test 5: Get User Statistics

**Endpoint:** `GET /api/analysis-results/user/test@example.com/statistics`

**Expected Response:**
```json
{
  "total_results": 2,
  "by_type": {
    "comparison": 1,
    "query": 1
  },
  "last_30_days": 2
}
```

---

### Test 6: Delete a Result

**Endpoint:** `DELETE /api/analysis-results/results/{result_id}?user_id=test@example.com`

**Expected Response:**
```json
{
  "message": "Result deleted: result_1729795200_abc12345"
}
```

## Testing with cURL

If you prefer command-line testing:

### Save Comparison Result
```bash
curl -X POST "https://localhost:8000/api/analysis-results/comparison" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@example.com",
    "standard_contract_id": "contract_abc",
    "compare_contract_ids": ["contract_def"],
    "comparison_mode": "full",
    "results": {"comparisons": []}
  }'
```

### Get Result
```bash
curl -X GET "https://localhost:8000/api/analysis-results/results/YOUR_RESULT_ID?user_id=test@example.com"
```

## Verifying in CosmosDB

You can also verify the data was stored correctly:

1. Go to Azure Portal
2. Navigate to your CosmosDB account
3. Open Data Explorer
4. Select the `analysis_results` container
5. Query: `SELECT * FROM c WHERE c.user_id = "test@example.com"`

You should see your saved comparison and query results.

## Common Issues

### Issue: "Container not found"
**Solution:** Run the container setup script:
```powershell
.\setup_analysis_results_container.ps1
```

### Issue: "Failed to connect to CosmosDB"
**Solution:** Check your environment variables:
```powershell
echo $env:CAIG_COSMOSDB_NOSQL_URI
echo $env:CAIG_COSMOSDB_NOSQL_KEY
```

### Issue: "Module not found: routers.analysis_results_router"
**Solution:** Ensure the router file exists:
```
web_app/routers/analysis_results_router.py
```

### Issue: "404 Not Found for endpoint"
**Solution:** Check that the router is registered in `web_app.py`:
```python
app.include_router(analysis_results_router)
```

## Next Steps

Once Phase 1 testing is complete:

1. ✅ Backend infrastructure verified
2. ⏭️ **Phase 2**: Implement PDF generation service
3. ⏭️ **Phase 3**: Implement email service
4. ⏭️ **Phase 4**: Update Angular frontend

## Success Criteria

Phase 1 is complete when:
- ✅ Container exists in CosmosDB
- ✅ API endpoints return 200 status codes
- ✅ Data is correctly stored and retrieved
- ✅ User statistics are accurate
- ✅ Results can be listed and filtered

---

**Phase 1 Complete!** 🎉

Ready to move to Phase 2 (PDF Generation) when you're ready.
