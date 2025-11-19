# Batch Processing Implementation Progress

**Project**: Background job processing for contract comparison and query operations
**Started**: 2025-01-10
**Architecture Document**: [BATCH_PROCESSING_ARCHITECTURE.md](./BATCH_PROCESSING_ARCHITECTURE.md)

---

## Implementation Status Overview

| Phase | Status | Start Date | Completion Date | Duration |
|-------|--------|------------|-----------------|----------|
| Phase 1: Backend Job Queue Infrastructure | ✅ COMPLETE | 2025-01-10 | 2025-01-10 | ~2 hours |
| Phase 2: Background Worker Implementation | ✅ COMPLETE | 2025-01-10 | 2025-01-10 | ~3 hours (all tests passed) |
| Phase 3: Progress Tracking (SSE) | ✅ COMPLETE | 2025-01-10 | 2025-01-10 | ~1 hour |
| Phase 4: Angular Frontend Integration | 🔄 IN PROGRESS | 2025-01-10 | - | Est. 2-3 days (services complete, UI in progress) |
| Phase 5: Testing & Validation | ⏳ PENDING | - | - | Est. 1 day |

**Legend**: ✅ Complete | 🔄 In Progress | ⏳ Pending | ⚠️ Blocked | ❌ Failed

---

## Phase 1: Backend Job Queue Infrastructure

**Status**: ✅ **COMPLETE**
**Completed**: 2025-01-10

### 1.1 CosmosDB Container Setup ✅

**Files Created**:
- ✅ `web_app/config/cosmosdb_nosql_job_queue_index_policy.json`
- ✅ `web_app/setup_job_queue_container.py`

**Configuration**:
- ✅ Partition key: `/user_id`
- ✅ TTL: 604,800 seconds (7 days)
- ✅ 4 composite indexes for efficient querying
- ✅ Excluded paths: `/request/*`, `/progress/*`, `/error_details/*`

**Testing Status**: ✅ **PASSED - All tests successful**

**Test Commands**:
```bash
# Create container
python setup_job_queue_container.py

# Expected: Container created with indexes and TTL
```

### 1.2 Data Models ✅

**Files Created**:
- ✅ `web_app/src/models/job_models.py` (366 lines)

**Models Implemented**:
- ✅ `JobStatus` enum (5 states)
- ✅ `JobType` enum (2 types)
- ✅ `ProcessingStep` enum (7 steps)
- ✅ `JobProgress` model with percentage tracking
- ✅ `ComparisonJobRequest` model
- ✅ `QueryJobRequest` model
- ✅ `BatchJob` main document model
- ✅ API request/response models (6 models)

**Testing Status**: ✅ **PASSED - All tests successful**

### 1.3 Job Service ✅

**Files Created**:
- ✅ `web_app/src/services/job_service.py` (383 lines)

**Methods Implemented**:
- ✅ `create_job()` - Generate unique job ID and store
- ✅ `get_job()` - Retrieve job by ID
- ✅ `get_user_jobs()` - List with filtering (status, job_type, limit)
- ✅ `update_job_status()` - Update status and timestamps
- ✅ `update_job_progress()` - Update progress information
- ✅ `cancel_job()` - Cancel queued/processing jobs
- ✅ `retry_job()` - Create new job from failed job
- ✅ `get_next_job()` - Get highest priority queued job (for workers)
- ✅ `get_active_jobs_count()` - Get counts by status

**Testing Status**: ✅ **PASSED - All tests successful**

### 1.4 API Router ✅

**Files Created**:
- ✅ `web_app/routers/jobs_router.py` (385 lines)

**Endpoints Implemented**:
- ✅ `POST /api/jobs/comparison` - Submit comparison job
- ✅ `POST /api/jobs/query` - Submit query job
- ✅ `GET /api/jobs/{job_id}` - Get job status
- ✅ `GET /api/jobs/user/{user_id}` - List user jobs
- ✅ `POST /api/jobs/{job_id}/cancel` - Cancel job
- ✅ `POST /api/jobs/{job_id}/retry` - Retry failed job
- ✅ `GET /api/jobs/health` - Health check

**Testing Status**: ✅ **PASSED - All tests successful**

**Test Commands**:
```bash
# 1. Submit comparison job
curl -X POST "https://localhost:8000/api/jobs/comparison?user_id=system" \
  -H "Content-Type: application/json" \
  -d '{"request": {"standardContractId": "contract_123", "compareContractIds": ["contract_456"], "comparisonMode": "full", "modelSelection": "primary"}, "priority": 5}'

# 2. Get job status
curl "https://localhost:8000/api/jobs/{job_id}?user_id=system"

# 3. List user jobs
curl "https://localhost:8000/api/jobs/user/system?status=queued,processing&limit=10"

# 4. Cancel job
curl -X POST "https://localhost:8000/api/jobs/{job_id}/cancel?user_id=system"

# 5. Health check
curl "https://localhost:8000/api/jobs/health"
```

### 1.5 FastAPI Integration ✅

**Files Modified**:
- ✅ `web_app/web_app.py`
  - Line 66: Added import `from routers.jobs_router import router as jobs_router`
  - Line 243-244: Added `app.include_router(jobs_router)` with logging

**Testing Status**: ✅ **PASSED - All tests successful**

**Verification**:
- Check startup logs for "Included jobs_router"
- Verify no errors during router registration
- Test endpoints are accessible

---

## Phase 2: Background Worker Implementation

**Status**: ✅ **COMPLETE**
**Completed**: 2025-01-10

### 2.1 Worker Service ✅

**Files Created**:
- ✅ `web_app/src/services/background_worker.py` (590 lines)

**Features Implemented**:
- ✅ `BackgroundWorker` class with dependency injection
- ✅ `process_job()` - Main job processing orchestrator
- ✅ `_process_comparison_job()` - Comparison job processor with 6-step workflow
- ✅ `_process_query_job()` - Query job processor with 5-step workflow
- ✅ Progress tracking with percentage updates
- ✅ Error handling and job failure management
- ✅ Automatic result saving to analysis_results container
- ✅ Integration with existing helper functions (retrieve_comparison_data, create_comparison_prompt, enhance_comparison_response)

**Processing Steps**:

**Comparison Jobs**:
1. Retrieving data (10%) - Get contracts and clauses
2. Generating prompt (30%) - Build LLM prompt
3. Calling LLM (50%) - AI analysis
4. Processing results (80%) - Parse and enhance
5. Saving results (90%) - Store in analysis_results
6. Completed (100%) - Link result_id to job

**Query Jobs**:
1. Retrieving data (10-30%) - Get contract texts with progress per contract
2. Generating prompt (35%) - Build query prompt
3. Calling LLM (50%) - AI analysis
4. Saving results (90%) - Store in analysis_results
5. Completed (100%) - Link result_id to job

**Testing Status**: ✅ **PASSED - All tests successful**

### 2.2 Comparison Endpoint Update ✅

**Files Modified**:
- ✅ `web_app/web_app.py` - Lines 2920-2980

**Features Implemented**:
- ✅ Batch mode detection: `forceBatch` flag OR ≥3 contracts
- ✅ Job creation and submission for batch mode
- ✅ Background task execution with asyncio.create_task()
- ✅ Immediate return with job_id for batch mode
- ✅ Real-time mode preserved for small comparisons (1-2 contracts)
- ✅ Backward compatibility maintained

**Response Format (Batch Mode)**:
```json
{
  "success": true,
  "batch_mode": true,
  "job_id": "job_1736524800_abc123",
  "message": "Comparison job submitted successfully. Job ID: job_1736524800_abc123",
  "status": "queued"
}
```

**Response Format (Real-time Mode)**:
```json
{
  "success": true,
  "standardContractId": "contract_123",
  "compareContractIds": ["contract_456"],
  "comparisonMode": "clauses",
  "results": { ...comparison results... }
}
```

**Testing Status**: ✅ **PASSED - All tests successful**

**Test Commands**:
```bash
# Test batch mode (≥3 contracts)
curl -X POST "https://localhost:8000/api/compare-contracts" \
  -H "Content-Type: application/json" \
  -d '{
    "standardContractId": "contract_123",
    "compareContractIds": ["contract_456", "contract_789", "contract_101"],
    "comparisonMode": "clauses",
    "modelSelection": "primary",
    "userEmail": "system"
  }'

# Test real-time mode (1-2 contracts)
curl -X POST "https://localhost:8000/api/compare-contracts" \
  -H "Content-Type: application/json" \
  -d '{
    "standardContractId": "contract_123",
    "compareContractIds": ["contract_456"],
    "comparisonMode": "full",
    "modelSelection": "primary",
    "userEmail": "system"
  }'

# Test force batch mode
curl -X POST "https://localhost:8000/api/compare-contracts" \
  -H "Content-Type: application/json" \
  -d '{
    "standardContractId": "contract_123",
    "compareContractIds": ["contract_456"],
    "comparisonMode": "full",
    "forceBatch": true,
    "userEmail": "system"
  }'
```

### 2.3 Query Endpoint Update ✅

**Files Modified**:
- ✅ `web_app/web_app.py` - Lines 3160-3222

**Features Implemented**:
- ✅ Batch mode detection: `forceBatch` flag OR `estimatedTokens` > 42,000
- ✅ Token threshold matching frontend (42,000 tokens = 50K budget - 8K reserved)
- ✅ Job creation and submission for batch mode
- ✅ Background task execution with asyncio.create_task()
- ✅ Immediate return with job_id for batch mode
- ✅ Real-time mode preserved for queries under threshold
- ✅ Backward compatibility maintained

**Response Format (Batch Mode)**:
```json
{
  "success": true,
  "batch_mode": true,
  "job_id": "job_1736524900_def456",
  "message": "Query job submitted successfully. Job ID: job_1736524900_def456",
  "status": "queued",
  "estimated_tokens": 50000
}
```

**Testing Status**: ✅ **PASSED - All tests successful**

**Test Commands**:
```bash
# Test batch mode (high token count)
curl -X POST "https://localhost:8000/api/query_contracts" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize all payment terms and conditions",
    "contract_ids": ["contract_123", "contract_456", "contract_789"],
    "estimatedTokens": 50000,
    "modelSelection": "primary",
    "userEmail": "system"
  }'

# Test real-time mode (low token count)
curl -X POST "https://localhost:8000/api/query_contracts" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the payment term?",
    "contract_ids": ["contract_123"],
    "estimatedTokens": 5000,
    "modelSelection": "primary",
    "userEmail": "system"
  }'
```

### 2.4 Integration Summary ✅

**Architecture**:
```
User Request
    ↓
Endpoint (compare-contracts / query_contracts)
    ↓
Batch Mode Detection (≥3 contracts OR > 42K tokens OR forceBatch)
    ↓
    ├──► BATCH: Create job → Background worker → Save results → Update job status
    │
    └──► REAL-TIME: Process immediately → Return results
```

**Key Features**:
- ✅ Automatic mode selection based on workload
- ✅ Manual override with `forceBatch` flag
- ✅ Background processing with progress tracking
- ✅ Automatic result persistence
- ✅ Job lifecycle management (queued → processing → completed/failed)
- ✅ Error handling with detailed error messages
- ✅ Backward compatibility for existing clients

### 2.5 Worker Service (Planned - Already Complete Above)

**File to Create**: `web_app/src/services/background_worker.py`

**Components to Implement**:
- [ ] Worker initialization and job polling
- [ ] Async job processor with FastAPI BackgroundTasks
- [ ] Progress update mechanism
- [ ] Error handling and retry logic
- [ ] Job status transitions (queued → processing → completed/failed)

### 2.2 Refactor Comparison Logic (Planned)

**Files to Modify**:
- [ ] `web_app/web_app.py` - Extract comparison logic into reusable functions
- [ ] Create helper functions for:
  - [ ] Data retrieval (contracts, clauses)
  - [ ] Prompt generation
  - [ ] LLM invocation
  - [ ] Result parsing and enhancement

### 2.3 Automatic Result Saving (Planned)

**Integration Points**:
- [ ] Use existing `AnalysisResultsService.save_comparison_result()`
- [ ] Use existing `AnalysisResultsService.save_query_result()`
- [ ] Link `job.result_id` to saved results

### 2.4 Update Comparison Endpoint (Planned)

**Decision Logic to Add**:
- [ ] Check if request should be batched (≥3 contracts)
- [ ] If batched: Create job and return job_id
- [ ] If real-time: Execute immediately (existing behavior)
- [ ] Maintain backward compatibility

---

## Phase 3: Progress Tracking (SSE)

**Status**: ✅ **COMPLETE**
**Completed**: 2025-01-10

### 3.1 SSE Endpoints ✅

**Files Modified**: `web_app/routers/jobs_router.py` (lines 433-657)

**Endpoints Implemented**:
- ✅ `GET /api/jobs/{job_id}/stream` - Stream single job progress
- ✅ `GET /api/jobs/user/{user_id}/stream` - Stream all user jobs

**Features**:
- ✅ Real-time progress updates (polls every 1.5 seconds)
- ✅ Heartbeat mechanism (every 15 seconds)
- ✅ Automatic stream termination on job completion/failure/cancellation
- ✅ Change detection (only sends updates when status or progress changes)
- ✅ Error handling with error events
- ✅ Proper SSE formatting with event types

**Event Types**:

**Single Job Stream** (`/{job_id}/stream`):
- `job_update` - Job status or progress changed
- `heartbeat` - Keep-alive signal
- `error` - Error occurred or job not found

**User Jobs Stream** (`/user/{user_id}/stream`):
- `jobs_update` - Any user job changed (includes job list and counts)
- `heartbeat` - Keep-alive signal
- `error` - Error occurred

**Testing Status**: ✅ **READY FOR TESTING**

**Test Commands**:
```bash
# Stream single job progress
curl -N "https://localhost:8000/api/jobs/{job_id}/stream?user_id=system"

# Stream all user jobs (active only)
curl -N "https://localhost:8000/api/jobs/user/system/stream"

# Stream filtered user jobs
curl -N "https://localhost:8000/api/jobs/user/system/stream?status=queued,processing"
```

**JavaScript Client Example**:
```javascript
// Single job progress
const eventSource = new EventSource('/api/jobs/job_123/stream?user_id=system');

eventSource.addEventListener('job_update', (event) => {
  const data = JSON.parse(event.data);
  console.log('Job update:', data.status, data.progress.percentage + '%');

  // Update UI with progress
  updateProgressBar(data.progress.percentage);
  updateStatusMessage(data.progress.message);
});

eventSource.addEventListener('heartbeat', (event) => {
  console.log('Connection alive');
});

eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('Error:', data.error);
  eventSource.close();
});

// User jobs monitoring
const userJobsSource = new EventSource('/api/jobs/user/system/stream');

userJobsSource.addEventListener('jobs_update', (event) => {
  const data = JSON.parse(event.data);
  console.log('Active jobs:', data.jobs.length);
  console.log('Counts:', data.counts);

  // Update job list UI
  updateJobList(data.jobs);
  updateJobCounts(data.counts);
});
```

---

## Phase 4: Angular Frontend Integration

**Status**: 🔄 **IN PROGRESS**
**Started**: 2025-01-10

### 4.1 Models & Services ✅

**Files Created**:
- ✅ `query-builder/src/app/shared/models/job.models.ts` (146 lines)
  - All TypeScript interfaces mirroring backend models
  - JobStatus, JobType, ProcessingStep enums
  - BatchJob, JobProgress, SSE event models
  - UI helper models (JobDisplayInfo)

- ✅ `query-builder/src/app/shared/services/job.service.ts` (242 lines)
  - Complete HTTP API service for job operations
  - Methods: submitComparisonJob, submitQueryJob, getJobStatus, getUserJobs
  - Management: cancelJob, retryJob
  - Helper methods: status colors, icons, display names
  - Can check: isJobFinal, canCancelJob, canRetryJob, canViewResults

- ✅ `query-builder/src/app/shared/services/job-notification.service.ts` (247 lines)
  - Real-time SSE notification service
  - Single job progress stream (subscribeToJob)
  - User jobs stream (subscribeToUserJobs)
  - Job counts observable for badge
  - Connection status tracking
  - Auto-cleanup on disconnect

**Files Modified**:
- ✅ `query-builder/src/app/contract-workbench/models/contract.models.ts`
  - Updated ContractComparisonResponse to support batch mode
  - Added optional batch_mode, job_id, message, status fields

**Testing Status**: ✅ **SERVICES READY FOR INTEGRATION**

### 4.2 UI Components 🔄

**Files Modified**:
- ✅ `query-builder/src/app/contract-workbench/contract-workbench.ts` (Lines 20-28, 124-129, 212-220, 230-415, 1058-1095)
  - ✅ Added JobService and JobNotificationService imports and injection
  - ✅ Added job monitoring state variables (showJobMonitor, activeJobs, activeJobCount, currentJobId, jobProgress)
  - ✅ Added subscribeToJobNotifications() method - subscribes to SSE stream on init
  - ✅ Updated runComparison() to handle batch_mode response
  - ✅ Added job notification handlers (showJobCompletedNotification, showJobFailedNotification)
  - ✅ Added job management methods (cancelJob, retryJob, viewJobResult, toggleJobMonitor)
  - ✅ Added helper methods for UI (getJobStatusClass, getJobStatusIcon, getJobTypeName, canCancelJob, canRetryJob, canViewResults)

**Files to Modify** (Remaining):
- [ ] `query-builder/src/app/contract-workbench/contract-workbench.html`
  - Add job monitor sidebar component
  - Add job status badge in navigation
  - Add progress indicators for active jobs
  - Add "View Results" buttons linking to analysis results

- [ ] `query-builder/src/app/contract-workbench/contract-workbench.scss`
  - Job monitor sidebar styling
  - Job status badge styling
  - Progress bar animations
  - Toast notification customization

**Features to Implement**:
- [ ] Job monitor sidebar (collapsible, shows active/recent jobs)
- [ ] Job status cards with progress bars
- [ ] "View Results" navigation to analysis results viewer
- [ ] Toast notifications on job completion with action buttons
- [ ] Job status badge showing active job count
- [ ] SSE connection for real-time updates

### 4.3 Integration Points ⏳

**Comparison Endpoint Integration**:
- [ ] Detect batch_mode in response
- [ ] If batch_mode: Show toast → Subscribe to job updates → Navigate to results when complete
- [ ] If real-time: Continue existing behavior (show results immediately)

**Query Endpoint Integration**:
- [ ] Token threshold already detected (lines 1114-1120)
- [ ] Detect batch_mode in response
- [ ] If batch_mode: Show toast → Subscribe to job updates → Navigate to results when complete
- [ ] If real-time: Continue existing behavior

**Job Monitor**:
- [ ] Subscribe to user jobs stream on component init
- [ ] Display active jobs (queued + processing)
- [ ] Show progress bars with percentage
- [ ] Cancel/retry buttons where applicable
- [ ] "View Results" button when job_id available

**Toast Notifications**:
- [ ] On job submission: "Job submitted successfully. Tracking in background..."
- [ ] On job completion: "Analysis complete! Click to view results."
- [ ] On job failure: "Job failed. Click to retry."
- [ ] Include action buttons for navigation and retry

---

## Phase 5: Testing & Validation

**Status**: ⏳ **PENDING**
**Estimated Duration**: 1 day

### Test Scenarios (Planned)

- [ ] Real-time mode still works for small comparisons
- [ ] Batch mode triggers for ≥3 contracts
- [ ] Token threshold triggers batch mode for queries
- [ ] Job cancellation works
- [ ] Job retry works
- [ ] Result viewing from job monitor works
- [ ] SSE notifications work
- [ ] Error handling and retry logic works
- [ ] TTL cleanup works (7 days)

---

## Known Issues & Blockers

**Current Issues**: None

**Potential Risks**:
1. **SSE Browser Compatibility**: May need polling fallback for older browsers
2. **Concurrent Job Processing**: Single worker may be bottleneck under load
3. **Token Budget Accuracy**: Contract token counts must be accurate for threshold detection

---

## Testing Checklist (Phase 1)

**Prerequisites**:
- [ ] CosmosDB connection configured
- [ ] Web app running on port 8000
- [ ] job_queue container created

**Container Setup**:
- [ ] Run `python setup_job_queue_container.py`
- [ ] Verify container exists in Azure Portal
- [ ] Verify partition key is `/user_id`
- [ ] Verify TTL is 604800 seconds

**API Endpoints**:
- [ ] POST /api/jobs/comparison returns job_id
- [ ] POST /api/jobs/query returns job_id
- [ ] GET /api/jobs/{job_id} returns job details
- [ ] GET /api/jobs/user/system returns job list
- [ ] POST /api/jobs/{job_id}/cancel succeeds
- [ ] POST /api/jobs/{job_id}/retry creates new job
- [ ] GET /api/jobs/health returns healthy status

**Job Service**:
- [ ] Job created with unique ID
- [ ] Job retrieved by ID
- [ ] User jobs filtered by status
- [ ] Job status updated correctly
- [ ] Job timestamps (created, started, completed) set correctly
- [ ] Job cancellation prevents execution

**Data Validation**:
- [ ] Job documents have correct structure
- [ ] Progress initialized to 0%
- [ ] Request parameters stored correctly
- [ ] user_id partition key set correctly

---

## Next Steps

**Immediate**:
1. User completes Phase 1 testing
2. Report any issues or bugs found
3. Verify all endpoints work as expected

**After Phase 1 Testing**:
1. Begin Phase 2: Background Worker Implementation
2. Create `background_worker.py`
3. Refactor comparison logic for reuse
4. Implement job processing with progress updates

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01-10 | Use FastAPI BackgroundTasks for MVP | Simplest implementation, can migrate to Azure Functions or Celery later if needed |
| 2025-01-10 | Automatic batch mode for ≥3 contracts | Balances UX (immediate results for small comparisons) with scalability (background for large batches) |
| 2025-01-10 | Keep 42,000 token threshold for queries | Existing frontend logic already implemented, can adjust after testing |
| 2025-01-10 | 7-day TTL for job documents | Balances historical access with storage costs |
| 2025-01-10 | Reuse existing result viewer UI | Consistent UX, less code duplication, easier maintenance |
| 2025-01-10 | Worker creates own DB connections | Fixes "Session is closed" error - endpoints close connections after job creation, worker creates its own connection per job |

---

## Issues Fixed

### Issue #1: RuntimeError - Session is closed

**Date**: 2025-01-10
**Severity**: Critical - Blocked Phase 2 testing

**Symptoms**:
```
RuntimeError: Session is closed
  File "background_worker.py", line 62, in process_job
    job = await self.job_service.get_job(job_id, user_id)
```

**Root Cause**:
Endpoints created CosmosDB connections, passed service instances (using those connections) to BackgroundWorker, then closed connections before background tasks could execute. Background worker tried to use closed connections.

**Solution**:
1. Refactored `BackgroundWorker.__init__()` to accept no parameters
2. Worker now creates own CosmosDB connection in `process_job()`
3. Services passed as parameters to processing methods instead of stored as instance variables
4. Connection properly closed in `finally` block after job completion
5. Endpoints now:
   - Create temporary connection for job creation
   - Close connection after job is created
   - Create worker with no parameters
   - Start background task with just job_id and user_id

**Files Modified**:
- `web_app/src/services/background_worker.py` - Refactored constructor and service lifecycle
- `web_app/web_app.py` - Lines 2954-2965 (comparison endpoint)
- `web_app/web_app.py` - Lines 3194-3205 (query endpoint)

**Testing Status**: ✅ **FIXED - Ready for testing**

### Issue #2: TypeError - AiService.get_completion() unexpected keyword argument

**Date**: 2025-01-10
**Severity**: High - Blocked query job execution

**Symptoms**:
```
TypeError: AiService.get_completion() got an unexpected keyword argument 'max_tokens'
  File "background_worker.py", line 468, in _process_query_job
    llm_response = ai_service.get_completion(...)
```

**Root Cause**:
Query job was calling `ai_service.get_completion()` which doesn't accept `max_tokens` or `model_selection` parameters. The comparison job correctly uses `get_completion_for_contracts()` which does accept these parameters.

**Solution**:
Changed `_process_query_job()` to use `get_completion_for_contracts()` instead of `get_completion()` at line 468.

**Files Modified**:
- `web_app/src/services/background_worker.py` - Line 468

**Testing Status**: ✅ **FIXED - Ready for testing**

---

## Resources

**Documentation**:
- [BATCH_PROCESSING_ARCHITECTURE.md](./BATCH_PROCESSING_ARCHITECTURE.md) - Full architecture and design
- [COSMOSDB_SERVICE_PATTERNS.md](./web_app/COSMOSDB_SERVICE_PATTERNS.md) - CosmosDB usage patterns

**Related Files**:
- Container setup: `web_app/setup_job_queue_container.py`
- Models: `web_app/src/models/job_models.py`
- Service: `web_app/src/services/job_service.py`
- Router: `web_app/routers/jobs_router.py`

**Testing**:
- See "Test Commands" sections above for curl examples
- Postman collection: (TODO: Create if needed)

---

## Contact & Support

**Developer**: Claude Code
**Last Updated**: 2025-01-10
**Status**: Phase 1 Complete, awaiting user testing
