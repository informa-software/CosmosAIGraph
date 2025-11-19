# Compliance System Testing Guide

**Project**: Contract Compliance Rules & Evaluation System
**Version**: 1.0
**Date**: 2025-01-09

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test Environment Setup](#test-environment-setup)
3. [Phase 1: Backend Services Testing](#phase-1-backend-services-testing)
4. [Phase 2: REST API Testing](#phase-2-rest-api-testing)
5. [Phase 3: Contract Ingestion Testing](#phase-3-contract-ingestion-testing)
6. [Phase 4: End-to-End Testing](#phase-4-end-to-end-testing)
7. [Performance Testing](#performance-testing)
8. [Troubleshooting](#troubleshooting)
9. [Test Data Cleanup](#test-data-cleanup)

---

## Prerequisites

### Required Services
- ✅ Azure CosmosDB NoSQL account with `caig` database
- ✅ Azure OpenAI service with GPT-4 deployment
- ✅ Python 3.12.9 with virtual environment
- ✅ FastAPI web application running on port 8000

### Required Containers
Verify these containers exist in CosmosDB `caig` database:
```bash
- compliance_rules (partition key: /id)
- compliance_results (partition key: /contract_id)
- evaluation_jobs (partition key: /id, TTL: 7 days)
- contracts (for contract data)
- contract_clauses (for clause data)
- contract_chunks (for chunk data)
```

### Environment Variables
Verify `.env` file contains:
```bash
CAIG_GRAPH_MODE="contracts"
CAIG_COSMOSDB_NOSQL_URI="<your-cosmos-endpoint>"
CAIG_COSMOSDB_NOSQL_KEY="<your-cosmos-key>"
CAIG_AZURE_OPENAI_URL="<your-openai-endpoint>"
CAIG_AZURE_OPENAI_KEY="<your-openai-key>"
CAIG_AZURE_OPENAI_COMPLETIONS_DEP="<deployment-name>"
```

---

## Test Environment Setup

### 1. Start Web Application
```bash
cd web_app
.\web_app.ps1
```

**Expected Output:**
```
deleting tmp\ files ...
activating the venv ...
[INFO] webapp.py started
[INFO] Application startup complete.
[INFO] Uvicorn running on http://127.0.0.1:8000
```

### 2. Verify Application Health
```bash
curl http://localhost:8000/ping
```

**Expected Response:**
```json
{
  "epoch": "1704812345.678"
}
```

### 3. Verify Compliance Containers
Run the setup script if containers don't exist:
```bash
cd web_app
python setup_compliance_containers.py
```

**Expected Output:**
```
[INFO] Setting up compliance_rules container...
[INFO] ✅ Container created: compliance_rules
[INFO] Setting up compliance_results container...
[INFO] ✅ Container created: compliance_results
[INFO] Setting up evaluation_jobs container...
[INFO] ✅ Container created: evaluation_jobs
[INFO] ✅ Setup completed successfully!
```

---

## Phase 1: Backend Services Testing

### Test 1.1: Create Compliance Rule

**Endpoint:** `POST /api/compliance/rules`

**Request:**
```bash
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Payment Terms Window",
    "description": "Contract must specify payment terms between 14 and 30 days",
    "severity": "high",
    "category": "payment_terms",
    "active": true
  }'
```

**Expected Response (201):**
```json
{
  "id": "<uuid>",
  "name": "Payment Terms Window",
  "description": "Contract must specify payment terms between 14 and 30 days",
  "severity": "high",
  "category": "payment_terms",
  "active": true,
  "created_date": "2025-01-09T10:00:00Z",
  "updated_date": "2025-01-09T10:00:00Z",
  "created_by": "system"
}
```

**Validation:**
- ✅ Status code is 201
- ✅ Response includes UUID `id`
- ✅ All fields match request
- ✅ Timestamps are ISO 8601 format

### Test 1.2: List All Rules

**Endpoint:** `GET /api/compliance/rules`

**Request:**
```bash
curl http://localhost:8000/api/compliance/rules
```

**Expected Response (200):**
```json
[
  {
    "id": "<uuid>",
    "name": "Payment Terms Window",
    ...
  }
]
```

**Validation:**
- ✅ Status code is 200
- ✅ Array contains created rule
- ✅ All fields present

### Test 1.3: Get Single Rule

**Endpoint:** `GET /api/compliance/rules/{rule_id}`

**Request:**
```bash
curl http://localhost:8000/api/compliance/rules/<rule_id>
```

**Expected Response (200):**
```json
{
  "id": "<rule_id>",
  "name": "Payment Terms Window",
  ...
}
```

**Validation:**
- ✅ Status code is 200
- ✅ Correct rule returned
- ✅ All fields present

### Test 1.4: Update Rule

**Endpoint:** `PUT /api/compliance/rules/{rule_id}`

**Request:**
```bash
curl -X PUT http://localhost:8000/api/compliance/rules/<rule_id> \
  -H "Content-Type: application/json" \
  -d '{
    "description": "UPDATED: Contract must specify payment terms between 14 and 30 days",
    "severity": "critical"
  }'
```

**Expected Response (200):**
```json
{
  "message": "Rule updated successfully",
  "rule": {
    "id": "<rule_id>",
    "description": "UPDATED: Contract must specify payment terms between 14 and 30 days",
    "severity": "critical",
    "updated_date": "<new_timestamp>"
  }
}
```

**Validation:**
- ✅ Status code is 200
- ✅ Description updated
- ✅ Severity changed to "critical"
- ✅ `updated_date` is newer than `created_date`

### Test 1.5: Filter Rules by Category

**Endpoint:** `GET /api/compliance/rules?category=payment_terms`

**Request:**
```bash
curl "http://localhost:8000/api/compliance/rules?category=payment_terms"
```

**Expected Response (200):**
```json
[
  {
    "id": "<uuid>",
    "category": "payment_terms",
    ...
  }
]
```

**Validation:**
- ✅ Only payment_terms rules returned
- ✅ No other categories included

### Test 1.6: Delete Rule

**Endpoint:** `DELETE /api/compliance/rules/{rule_id}`

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/compliance/rules/<rule_id>
```

**Expected Response (200):**
```json
{
  "message": "Rule deleted successfully"
}
```

**Validation:**
- ✅ Status code is 200
- ✅ GET request returns 404

---

## Phase 2: REST API Testing

### Test 2.1: Create Multiple Rules

Create 5-10 rules from `sample_compliance_rules.md`:
- At least 1 critical severity
- At least 1 high severity
- At least 2 different categories

**Commands:**
```bash
# Critical: Confidentiality Clause
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Confidentiality Clause Required",
    "description": "Contract must include confidentiality obligations",
    "severity": "critical",
    "category": "confidentiality",
    "active": true
  }'

# High: Payment Terms
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Payment Terms Window",
    "description": "Contract must specify payment terms between 14 and 30 days",
    "severity": "high",
    "category": "payment_terms",
    "active": true
  }'

# High: Liability Cap
curl -X POST http://localhost:8000/api/compliance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Limitation of Liability Cap",
    "description": "Contract must include a cap on liability",
    "severity": "high",
    "category": "liability",
    "active": true
  }'
```

**Validation:**
```bash
# Verify count
curl http://localhost:8000/api/compliance/rules | jq 'length'
# Expected: 3 or more

# Verify by severity
curl "http://localhost:8000/api/compliance/rules?severity=critical" | jq 'length'
# Expected: 1 or more

# Verify active rules only
curl "http://localhost:8000/api/compliance/rules?active_only=true" | jq 'length'
# Expected: All rules (if all are active)
```

### Test 2.2: List Categories

**Endpoint:** `GET /api/compliance/categories`

**Request:**
```bash
curl http://localhost:8000/api/compliance/categories
```

**Expected Response (200):**
```json
[
  {
    "id": "payment_terms",
    "name": "Payment Terms",
    "description": "Rules related to payment schedules, terms, and conditions"
  },
  {
    "id": "confidentiality",
    "name": "Confidentiality",
    "description": "Rules related to confidentiality and non-disclosure"
  },
  ...
]
```

**Validation:**
- ✅ Returns all predefined categories
- ✅ Categories used in rules are included

### Test 2.3: Get Compliance Summary (Empty)

**Endpoint:** `GET /api/compliance/summary`

**Request:**
```bash
curl http://localhost:8000/api/compliance/summary
```

**Expected Response (200):**
```json
{
  "total_rules": 3,
  "active_rules": 3,
  "total_contracts_evaluated": 0,
  "overall_pass_rate": 0.0,
  "rules_summary": [
    {
      "rule_id": "<uuid>",
      "rule_name": "Payment Terms Window",
      "severity": "high",
      "category": "payment_terms",
      "total_evaluated": 0,
      "pass_count": 0,
      "fail_count": 0,
      "partial_count": 0,
      "not_applicable_count": 0,
      "pass_rate": 0.0,
      "stale_count": 0,
      "last_evaluated": null
    },
    ...
  ]
}
```

**Validation:**
- ✅ `total_contracts_evaluated` is 0
- ✅ All rules show 0 evaluations
- ✅ All `last_evaluated` are null

---

## Phase 3: Contract Ingestion Testing

### Test 3.1: Verify Sample Contracts

**Check contract files exist:**
```bash
cd web_app
ls data/contracts/*.json | wc -l
```

**Expected:** At least 1 contract file

**If no contracts exist:** Create a sample contract JSON file or use existing test data.

### Test 3.2: Load Contracts WITHOUT Compliance Rules

**Purpose:** Verify contract loading works independently

**Steps:**
1. Delete all compliance rules
2. Load contracts
3. Verify no compliance evaluation occurs

**Commands:**
```bash
# Delete all rules (via API or Azure Portal)
curl -X DELETE http://localhost:8000/api/compliance/rules/<rule_id>

# Load contracts
cd web_app
python main_contracts.py load_contracts caig contracts data/contracts 1
```

**Expected Log Output:**
```
[INFO] Compliance evaluation disabled: No active rules found
[INFO] Processing contract 1/1: <filename>
[INFO] Stored parent document: contract_<id>
[INFO] load_contracts completed; results: {
  "contracts_read": 1,
  "parent_docs_stored": 1,
  "clause_docs_stored": X,
  "chunk_docs_stored": Y
}
```

**Validation:**
- ✅ No compliance evaluation messages
- ✅ Contract stored successfully
- ✅ No `compliance_evaluations_*` counters

### Test 3.3: Load Contracts WITH Compliance Rules

**Purpose:** Verify automatic compliance evaluation during ingestion

**Steps:**
1. Create 3-5 active compliance rules
2. Load 1 contract
3. Verify compliance evaluation occurs

**Commands:**
```bash
# Create rules (use sample_compliance_rules.md)
curl -X POST http://localhost:8000/api/compliance/rules ...

# Verify rules
curl "http://localhost:8000/api/compliance/rules?active_only=true" | jq 'length'
# Expected: 3-5

# Load contracts
cd web_app
python main_contracts.py load_contracts caig contracts data/contracts 1
```

**Expected Log Output:**
```
[INFO] Compliance evaluation enabled: 3 active rules found
[INFO] Processing contract 1/1: <filename>
[INFO] Stored parent document: contract_<id>
[INFO] Evaluating compliance rules for contract: contract_<id>
[INFO] Compliance evaluation completed for contract_<id>: Pass=1, Fail=1, Partial=0, N/A=1
[INFO] load_contracts completed; results: {
  "contracts_read": 1,
  "parent_docs_stored": 1,
  "clause_docs_stored": X,
  "chunk_docs_stored": Y,
  "compliance_evaluations_completed": 1
}
```

**Validation:**
- ✅ "Compliance evaluation enabled" message appears
- ✅ "Evaluating compliance rules" message per contract
- ✅ Pass/Fail/Partial/N/A counts logged
- ✅ `compliance_evaluations_completed` counter incremented

### Test 3.4: Verify Compliance Results Stored

**Endpoint:** `GET /api/compliance/results/contract/{contract_id}`

**Request:**
```bash
curl http://localhost:8000/api/compliance/results/contract/contract_<id>
```

**Expected Response (200):**
```json
{
  "contract_id": "contract_<id>",
  "results": [
    {
      "id": "<uuid>",
      "contract_id": "contract_<id>",
      "rule_id": "<rule_uuid>",
      "rule_name": "Payment Terms Window",
      "rule_description": "Contract must specify payment terms...",
      "rule_version_date": "2025-01-09T10:00:00Z",
      "evaluation_result": "pass",
      "confidence": 0.85,
      "explanation": "The contract specifies payment terms of Net 30 days...",
      "evidence": [
        "Payment shall be made within thirty (30) days of invoice date."
      ],
      "evaluated_date": "2025-01-09T10:05:00Z"
    },
    ...
  ],
  "summary": {
    "total": 3,
    "pass": 1,
    "fail": 1,
    "partial": 0,
    "not_applicable": 1
  }
}
```

**Validation:**
- ✅ Results exist for each rule evaluated
- ✅ Each result has all required fields
- ✅ `evaluation_result` is one of: pass, fail, partial, not_applicable
- ✅ `confidence` is between 0.0 and 1.0
- ✅ `explanation` is non-empty
- ✅ `evidence` array contains contract excerpts
- ✅ Summary totals match result count

### Test 3.5: Load Multiple Contracts

**Purpose:** Test batch processing performance

**Commands:**
```bash
cd web_app
python main_contracts.py load_contracts caig contracts data/contracts 5
```

**Expected Log Output:**
```
[INFO] Compliance evaluation enabled: 3 active rules found
[INFO] Processing contract 1/5: contract1.json
[INFO] Compliance evaluation completed for contract_<id1>: Pass=1, Fail=1, Partial=0, N/A=1
[INFO] Processing contract 2/5: contract2.json
[INFO] Compliance evaluation completed for contract_<id2>: Pass=2, Fail=0, Partial=1, N/A=0
...
[INFO] load_contracts completed; results: {
  "contracts_read": 5,
  "parent_docs_stored": 5,
  "compliance_evaluations_completed": 5
}
```

**Validation:**
- ✅ All contracts processed
- ✅ Compliance evaluation per contract
- ✅ No errors or failures
- ✅ Performance acceptable (check timestamps)

---

## Phase 4: End-to-End Testing

### Test 4.1: Complete Workflow Test

**Scenario:** Create rules → Load contracts → Review dashboard → Update rule → Check stale results

**Step 1: Create Rules**
```bash
# Create 3 rules from different categories
curl -X POST http://localhost:8000/api/compliance/rules ...
```

**Step 2: Load Contracts**
```bash
cd web_app
python main_contracts.py load_contracts caig contracts data/contracts 2
```

**Step 3: View Dashboard**
```bash
curl http://localhost:8000/api/compliance/summary
```

**Expected Dashboard:**
```json
{
  "total_rules": 3,
  "active_rules": 3,
  "total_contracts_evaluated": 2,
  "overall_pass_rate": 0.67,
  "rules_summary": [
    {
      "rule_name": "Payment Terms Window",
      "total_evaluated": 2,
      "pass_count": 1,
      "fail_count": 1,
      "pass_rate": 0.5,
      "stale_count": 0,
      "last_evaluated": "2025-01-09T10:15:00Z"
    },
    ...
  ]
}
```

**Step 4: Update Rule (Change Description)**
```bash
curl -X PUT http://localhost:8000/api/compliance/rules/<rule_id> \
  -H "Content-Type: application/json" \
  -d '{
    "description": "UPDATED: New stricter payment terms requirement"
  }'
```

**Step 5: Check for Stale Results**
```bash
curl http://localhost:8000/api/compliance/stale-rules
```

**Expected Response:**
```json
[
  {
    "rule_id": "<rule_id>",
    "rule_name": "Payment Terms Window",
    "stale_result_count": 2,
    "last_updated": "2025-01-09T10:20:00Z"
  }
]
```

**Step 6: Re-evaluate Stale Results**
```bash
curl -X POST http://localhost:8000/api/compliance/reevaluate/stale/<rule_id>
```

**Expected Response:**
```json
{
  "job_id": "<job_uuid>",
  "message": "Re-evaluation queued for 2 stale results"
}
```

**Step 7: Check Job Status**
```bash
curl http://localhost:8000/api/compliance/jobs/<job_id>
```

**Expected Response:**
```json
{
  "id": "<job_id>",
  "job_type": "evaluate_rule",
  "status": "completed",
  "total_items": 2,
  "completed_items": 2,
  "failed_items": 0,
  "progress_percentage": 100.0
}
```

**Validation:**
- ✅ Rules created successfully
- ✅ Contracts evaluated automatically
- ✅ Dashboard shows accurate statistics
- ✅ Rule update creates stale results
- ✅ Stale results detected
- ✅ Re-evaluation job completes successfully
- ✅ Results no longer stale after re-evaluation

### Test 4.2: Manual Evaluation Test

**Scenario:** Evaluate specific contract on-demand

**Step 1: Get Contract ID**
```bash
curl http://localhost:8000/api/contracts | jq '.[0].id'
```

**Step 2: Evaluate Contract**
```bash
curl -X POST http://localhost:8000/api/compliance/evaluate/contract/<contract_id>
```

**Expected Response (200):**
```json
{
  "job_id": "<job_uuid>",
  "results": [...],
  "summary": {
    "total": 3,
    "pass": 2,
    "fail": 1,
    "partial": 0,
    "not_applicable": 0
  }
}
```

**Validation:**
- ✅ Job created (if async)
- ✅ Results returned
- ✅ Summary accurate

---

## Performance Testing

### Test 5.1: Rule Evaluation Performance

**Test:** Measure LLM call time for batch evaluation

**Method:**
1. Create 10 rules
2. Load 1 contract
3. Check logs for timing

**Expected Performance:**
- Single LLM call for up to 10 rules
- Total evaluation time: 5-15 seconds per contract
- No timeout errors

**Commands:**
```bash
# Create 10 rules
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/compliance/rules ...
done

# Load contract with timing
time python main_contracts.py load_contracts caig contracts data/contracts 1
```

**Performance Targets:**
- ✅ < 15 seconds per contract (10 rules)
- ✅ < 30 seconds per contract (20 rules)
- ✅ < 60 seconds per contract (30 rules)

### Test 5.2: Batch Contract Loading

**Test:** Load multiple contracts with compliance evaluation

**Commands:**
```bash
time python main_contracts.py load_contracts caig contracts data/contracts 10
```

**Performance Targets:**
- ✅ < 3 minutes for 10 contracts (3 rules each)
- ✅ No memory errors
- ✅ All evaluations complete successfully

---

## Troubleshooting

### Issue 1: 500 Error - Method Not Found

**Error:** `'CosmosNoSQLService' object has no attribute 'create_document'`

**Solution:** Use `create_item()` and `upsert_item()` instead of `create_document()` and `upsert_document()`

**Fixed in:** All compliance services

### Issue 2: Dataclass Initialization Error

**Error:** `ComplianceRule.__init__() got an unexpected keyword argument '_rid'`

**Solution:** Filter CosmosDB system fields in `from_dict()` methods

**Fixed in:** All compliance models

### Issue 3: Compliance Evaluation Not Running

**Symptom:** Contracts load but no compliance evaluation occurs

**Check:**
1. Are there active rules?
   ```bash
   curl "http://localhost:8000/api/compliance/rules?active_only=true"
   ```
2. Check logs for "Compliance evaluation disabled"
3. Verify rules created successfully

**Solution:** Create at least 1 active rule before loading contracts

### Issue 4: LLM Timeout Errors

**Symptom:** Evaluation fails with timeout error

**Possible Causes:**
- Too many rules in batch (>10)
- Very long contract text
- Azure OpenAI throttling

**Solutions:**
1. Reduce `MAX_RULES_PER_BATCH` in `compliance_evaluation_service.py`
2. Check Azure OpenAI quota limits
3. Add retry logic

### Issue 5: Stale Results Not Detected

**Symptom:** Updated rule doesn't show stale results

**Check:**
1. Verify rule `updated_date` is newer than result `rule_version_date`
2. Check for timezone issues (all should be UTC with 'Z' suffix)

**Solution:** Ensure all timestamps use ISO 8601 format with UTC timezone

---

## Test Data Cleanup

### Clean Up Test Data

**Remove All Compliance Rules:**
```bash
# List all rules
curl http://localhost:8000/api/compliance/rules | jq -r '.[].id' > rule_ids.txt

# Delete each rule
while read rule_id; do
  curl -X DELETE http://localhost:8000/api/compliance/rules/$rule_id
done < rule_ids.txt
```

**Remove Results (via Azure Portal):**
1. Go to CosmosDB Data Explorer
2. Select `caig` database
3. Select `compliance_results` container
4. Delete all documents

**Remove Jobs (via Azure Portal):**
1. Select `evaluation_jobs` container
2. Delete all documents
3. (Or wait 7 days for TTL auto-cleanup)

**Remove Test Contracts:**
```bash
# Via Azure Portal:
# Delete documents from 'contracts', 'contract_clauses', 'contract_chunks' containers
```

---

## Test Success Criteria

### ✅ Phase 1: Backend Services
- [ ] Create rule returns 201 with valid UUID
- [ ] List rules returns all created rules
- [ ] Get rule returns correct rule
- [ ] Update rule changes fields and updates timestamp
- [ ] Delete rule removes rule permanently
- [ ] Filter by category returns correct subset
- [ ] Filter by severity returns correct subset
- [ ] Active filter excludes inactive rules

### ✅ Phase 2: REST API
- [ ] Multiple rules can be created
- [ ] Categories endpoint returns all categories
- [ ] Summary endpoint returns correct structure
- [ ] Empty summary shows 0 evaluations

### ✅ Phase 3: Contract Ingestion
- [ ] Contracts load without rules (no evaluation)
- [ ] Contracts load with rules (automatic evaluation)
- [ ] Results stored in compliance_results container
- [ ] Each result has all required fields
- [ ] Evidence contains contract excerpts
- [ ] Summary counts match actual results

### ✅ Phase 4: End-to-End
- [ ] Complete workflow executes successfully
- [ ] Dashboard shows accurate statistics
- [ ] Rule updates create stale results
- [ ] Stale detection works correctly
- [ ] Re-evaluation completes successfully
- [ ] Manual evaluation works on-demand

### ✅ Phase 5: Performance
- [ ] Single contract evaluates in < 15 seconds
- [ ] Batch loading completes without errors
- [ ] No memory or timeout issues
- [ ] LLM batching reduces API calls

---

## Appendix: Sample Test Contract

For testing, create a simple contract JSON:

```json
{
  "imageQuestDocumentId": "test_contract_001",
  "filename": "test_contract.pdf",
  "status": "Analyzed",
  "result": {
    "contents": [
      {
        "markdown": "# Master Services Agreement\n\nThis Agreement is made on January 1, 2025.\n\n## Payment Terms\nPayment shall be made within thirty (30) days of invoice date.\n\n## Confidentiality\nBoth parties agree to maintain confidentiality of proprietary information.\n\n## Termination\nEither party may terminate this agreement with 60 days written notice.\n\n## Governing Law\nThis agreement shall be governed by the laws of the State of Delaware.",
        "fields": {
          "ContractTitle": {
            "type": "string",
            "valueString": "Master Services Agreement"
          },
          "ContractDate": {
            "type": "date",
            "valueDate": "2025-01-01"
          },
          "PaymentTerms": {
            "type": "string",
            "valueString": "Net 30"
          }
        }
      }
    ]
  }
}
```

Save as `web_app/data/contracts/test_contract_001.json` for testing.

---

**End of Testing Guide**
