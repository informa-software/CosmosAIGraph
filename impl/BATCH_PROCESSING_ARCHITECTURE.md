# Batch Processing Architecture Plan

## Current Compare Contracts Processing Flow

### 1. Frontend Initiation (Angular)
**File**: `query-builder/src/app/contract-workbench/contract-workbench.ts`

**User Action**: Clicks "Generate Comparison" button

**Processing Steps**:

```typescript
generateComparison() → runComparison() → contractService.compareContracts()
```

1. **Validation** (lines 924-954):
   - Verify standard contract selected
   - Verify at least one comparison contract selected
   - Normalize contract IDs (ensure `contract_` prefix)
   - Filter out standard contract from comparison list

2. **Request Preparation** (lines 965-978):
   ```typescript
   {
     standardContractId: "contract_xxx",
     compareContractIds: ["contract_yyy", "contract_zzz"],
     comparisonMode: "clauses" | "full",
     selectedClauses: ["Indemnity", "Payment Terms"] | "all",
     modelSelection: "primary" | "secondary",
     userEmail: "system"
   }
   ```

3. **UI State Management** (lines 983-984):
   - Set `isLoadingComparison = true`
   - Show comparison modal
   - **SYNCHRONOUS BLOCKING**: User waits for entire operation

4. **API Call** (`contract.service.ts:391-408`):
   - `POST /api/compare-contracts`
   - Observable subscription awaits response
   - **NO PROGRESS UPDATES** during processing

5. **Response Handling** (lines 987-1003):
   - Success: Display results in modal, switch to comparison tab
   - Error: Show toast notification
   - Set `isLoadingComparison = false`

### 2. Backend Processing (Python/FastAPI)
**File**: `web_app/web_app.py`

**Endpoint**: `POST /api/compare-contracts` (lines 2829-3047)

#### Processing Steps:

**A. Request Validation & Data Retrieval** (lines 2850-2931):
1. Parse request body
2. Validate contract IDs
3. Initialize CosmosNoSQLService
4. Call `retrieve_comparison_data()` to fetch:
   - Standard contract data (full text or clauses)
   - Comparison contract data (full text or clauses)
   - Clause cache for enhancement

**B. LLM Prompt Creation** (lines 2955-2980):
1. Create comparison prompt based on mode (full vs clauses)
2. Check token limits (max ~100,000 chars for full mode)
3. Truncate if necessary (simple truncation strategy)

**C. AI Processing** (lines 2982-2995):
1. Track start time
2. Call `ai_svc.get_completion_for_contracts()`:
   - System prompt: "You are a legal contract analysis expert..."
   - User prompt: Formatted comparison request
   - Max tokens: 6000
   - Model selection: primary/secondary
   - **LLM TRACKING**: Automatically tracked via `llm_tracker`

**D. Response Processing** (lines 2998-3023):
1. Parse JSON response from LLM
2. Handle parse errors gracefully
3. If clause mode: Enhance response with full clause texts
4. Calculate elapsed time

**E. Response Return** (lines 3025-3039):
```json
{
  "success": true,
  "standardContractId": "contract_xxx",
  "compareContractIds": ["contract_yyy", "contract_zzz"],
  "comparisonMode": "clauses",
  "selectedClauses": ["Indemnity"],
  "results": {
    "comparisons": [/* detailed comparison results */]
  }
}
```

**TOTAL PROCESSING TIME**:
- Clause mode: 5-15 seconds (2-5 contracts)
- Full mode: 10-30 seconds (2-5 contracts)
- **BLOCKING**: HTTP connection held open entire time

### 3. Current Data Storage

#### A. LLM Usage Tracking (Automatic)
**Container**: `model_usage`
**Service**: `llm_usage_tracker.py`

Tracked automatically during `ai_svc.get_completion_for_contracts()`:
```json
{
  "id": "uuid",
  "type": "model_usage",
  "api_type": "completion",
  "user_email": "system",
  "operation": "contract_comparison",
  "model": "gpt-4.1-2025-04-14",
  "prompt_tokens": 5000,
  "completion_tokens": 1500,
  "total_tokens": 6500,
  "estimated_cost": 0.195,
  "elapsed_time": 12.5,
  "timestamp": "2025-01-10T...",
  "success": true
}
```

#### B. Analysis Results Storage (Optional, User-Initiated)
**Container**: `analysis_results`
**Endpoint**: `POST /api/analysis-results/comparison`
**Trigger**: User clicks "Save Results" button AFTER comparison completes

**Saved Data**:
```json
{
  "id": "result_uuid",
  "type": "comparison",
  "user_id": "system",
  "standard_contract_id": "contract_xxx",
  "compare_contract_ids": ["contract_yyy"],
  "comparison_mode": "clauses",
  "selected_clauses": ["Indemnity"],
  "results": {/* full comparison response */},
  "metadata": {
    "title": "Comparison: Contract A vs 2 contract(s)",
    "description": "clauses comparison"
  },
  "created_date": "2025-01-10T...",
  "modified_date": "2025-01-10T..."
}
```

**Purpose**: PDF generation, historical tracking, user retrieval

**Current Limitations**:
- ❌ No automatic saving
- ❌ Results lost if user closes browser before saving
- ❌ No way to resume/retrieve ongoing comparisons

---

## Current Query Contracts Processing Flow

### 1. Frontend Initiation
**File**: `query-builder/src/app/contract-workbench/contract-workbench.ts`

**User Action**: Types question and clicks search/ask

**Processing Steps**:
1. Validate question and selected contracts
2. Call `contractService.queryContractsStreaming()`
3. **STREAMING RESPONSE**: Progressive updates via SSE
4. Display chunks as they arrive

### 2. Backend Processing
**Endpoint**: `POST /api/query_contracts_stream` (inferred from service)

**Processing**:
1. Retrieve full text of selected contracts
2. Truncate if needed to fit token limits
3. Send to LLM with streaming enabled
4. Stream response chunks back to client
5. Track usage in `model_usage` collection

**Advantages over Comparison**:
- ✅ Streaming provides progress feedback
- ✅ User sees partial results immediately
- ✅ Better UX for long operations

---

## UX Integration: Batch Mode & Result Viewing

### Existing Token Threshold Detection (Query Contracts)

**File**: `query-builder/src/app/contract-workbench/contract-workbench.ts`

The frontend **already implements** automatic batch mode detection:

**Token Budget Configuration** (lines 38-39):
```typescript
readonly TOKEN_BUDGET = 50000;  // 50K tokens for testing/demo
readonly RESERVED_TOKENS = 8000;  // Reserve for question, answer, and overhead
// Available budget: 42,000 tokens
```

**Computed Properties** (lines 132-163):
```typescript
get availableTokenBudget(): number {
  return this.TOKEN_BUDGET - this.RESERVED_TOKENS;  // 42,000 tokens
}

get usedTokens(): number {
  return this.selectedContractsForQuestion.reduce((total, contractId) => {
    const contract = this.allContracts.find(c => c.id === contractId);
    return total + (contract?.text_tokens || 0);
  }, 0);
}

get isTokenLimitExceeded(): boolean {
  return this.usedTokens > this.availableTokenBudget;
}
```

**Automatic Warning Toast** (lines 1114-1120):
```typescript
if (this.usedTokens > this.availableTokenBudget) {
  this.toastService.warning(
    'Token Budget Exceeded',
    `Your query will be processed in the background and you will be notified when complete. ` +
    `Token usage: ${this.formatTokens(this.usedTokens)} / ${this.formatTokens(this.availableTokenBudget)}`
  );
}
```

**Current State**:
- ✅ Token threshold detection implemented
- ✅ Warning message promises background processing
- ❌ Actual background processing **not yet implemented**
- ❌ Completion notification **not yet implemented**

### Proposed UX Flow: Results Viewing & Navigation

#### 1. Unified Results Viewer

**Design Decision**: **YES**, use the same UI components to display results regardless of whether they came from real-time or batch processing.

**Rationale**:
- ✅ Consistent user experience
- ✅ Single codebase for result rendering
- ✅ Easier maintenance
- ✅ Results are identical in structure

**Implementation**:
```typescript
// contract-workbench.component.ts

// Real-time results (existing)
this.contractService.compareContracts(request).subscribe({
  next: (response) => {
    this.comparisonResults = response;  // Display in UI
    this.activeTab = 'comparison';
  }
});

// Batch results (new)
viewBatchResults(job: BatchJob) {
  if (job.result_id) {
    this.analysisResultsService.getComparisonResult(job.result_id).subscribe({
      next: (savedResult) => {
        // Load saved results into same UI components
        this.comparisonResults = savedResult.results;
        this.activeTab = 'comparison';
        this.showJobMonitor = false;  // Hide job panel
      }
    });
  }
}
```

**UI Components Reused**:
- Comparison results modal
- Clause-by-clause analysis cards
- Risk assessment displays
- Summary statistics
- Export/PDF buttons

#### 2. Navigation from Job Monitor to Results

**Design Decision**: **YES**, users can navigate directly from the batch job monitor to view results.

**Implementation Approach**:

**Option A: Sidebar Job Panel** (Recommended)
```html
<!-- Collapsible job status panel in contract-workbench -->
<div class="job-monitor-sidebar" [class.expanded]="showJobMonitor">
  <div class="job-monitor-header">
    <h3>Background Jobs</h3>
    <button (click)="toggleJobMonitor()">
      {{ showJobMonitor ? 'Hide' : 'Show' }}
    </button>
  </div>

  <div class="job-list">
    <div *ngFor="let job of activeJobs" class="job-card">
      <div class="job-header">
        <h4>{{ getJobTitle(job) }}</h4>
        <span class="status-badge" [class]="job.status">
          {{ job.status }}
        </span>
      </div>

      <!-- Progress bar for active jobs -->
      <div *ngIf="job.status === 'processing'" class="progress-bar">
        <div class="progress-fill" [style.width.%]="job.progress.percentage"></div>
        <span class="progress-text">{{ job.progress.message }}</span>
      </div>

      <!-- Action buttons -->
      <div class="job-actions">
        <button
          *ngIf="job.status === 'completed'"
          (click)="viewJobResults(job)"
          class="btn-primary">
          View Results →
        </button>

        <button
          *ngIf="job.status === 'queued'"
          (click)="cancelJob(job)"
          class="btn-secondary">
          Cancel
        </button>

        <button
          *ngIf="job.status === 'failed'"
          (click)="retryJob(job)"
          class="btn-warning">
          Retry
        </button>
      </div>

      <small class="job-timestamp">
        {{ getJobTimestamp(job) }}
      </small>
    </div>
  </div>
</div>
```

**TypeScript Implementation**:
```typescript
export class ContractWorkbenchComponent {
  showJobMonitor = true;
  activeJobs: BatchJob[] = [];

  ngOnInit() {
    // Load user's active jobs
    this.loadActiveJobs();

    // Subscribe to job updates via SSE or polling
    this.subscribeToJobUpdates();
  }

  viewJobResults(job: BatchJob) {
    if (!job.result_id) {
      this.toastService.error('No Results', 'Job results are not available.');
      return;
    }

    // Determine job type and load appropriate results
    if (job.job_type === 'contract_comparison') {
      this.analysisResultsService.getComparisonResult(job.result_id).subscribe({
        next: (savedResult) => {
          // Populate the comparison UI with saved results
          this.comparisonResults = savedResult.results;
          this.standardContractId = savedResult.standard_contract_id;
          this.activeTab = 'comparison';
          this.showComparisonModal = true;

          this.toastService.success(
            'Results Loaded',
            'Batch comparison results loaded successfully.'
          );
        },
        error: (error) => {
          this.toastService.error(
            'Load Failed',
            'Failed to load batch results.'
          );
        }
      });
    } else if (job.job_type === 'contract_query') {
      this.analysisResultsService.getQueryResult(job.result_id).subscribe({
        next: (savedResult) => {
          // Populate the query results UI
          this.answer = savedResult.results.answer_summary;
          this.question = savedResult.query_text;
          this.activeTab = 'question';

          this.toastService.success(
            'Results Loaded',
            'Batch query results loaded successfully.'
          );
        }
      });
    }
  }

  loadActiveJobs() {
    const userId = 'system';  // TODO: Replace with actual user

    this.jobService.getUserJobs(userId, ['queued', 'processing', 'completed'])
      .subscribe({
        next: (response) => {
          this.activeJobs = response.jobs;
        }
      });
  }

  subscribeToJobUpdates() {
    // Option 1: Server-Sent Events for real-time updates
    this.activeJobs.forEach(job => {
      if (job.status === 'processing' || job.status === 'queued') {
        this.jobService.streamJobProgress(job.id).subscribe({
          next: (event) => {
            this.updateJobInList(event);
          }
        });
      }
    });

    // Option 2: Polling (simpler fallback)
    setInterval(() => {
      this.refreshActiveJobs();
    }, 10000);  // Poll every 10 seconds
  }
}
```

**Option B: Dedicated Job History Page**
- Separate route: `/job-history`
- Full-page view of all jobs
- Advanced filtering and search
- Better for power users managing many jobs

**Recommended**: Use **Option A** (sidebar) for quick access, with link to full history page.

#### 3. Toast Notifications on Job Completion

**Design Decision**: **YES**, users receive toast notifications when background jobs complete.

**Implementation Strategies**:

**Strategy 1: Server-Sent Events (SSE)** (Recommended)
```typescript
// job-notification.service.ts
@Injectable({ providedIn: 'root' })
export class JobNotificationService {
  private eventSource: EventSource | null = null;

  constructor(
    private toastService: ToastService,
    private router: Router
  ) {}

  subscribeToUserJobs(userId: string) {
    // Connect to SSE endpoint
    this.eventSource = new EventSource(
      `https://localhost:8000/api/jobs/user/${userId}/stream`
    );

    this.eventSource.addEventListener('job_completed', (event) => {
      const job = JSON.parse(event.data);

      this.toastService.success(
        'Job Completed',
        `${this.getJobTypeLabel(job.job_type)} has finished. Click to view results.`,
        {
          duration: 10000,  // 10 seconds
          action: {
            label: 'View Results',
            onClick: () => this.navigateToResults(job)
          }
        }
      );
    });

    this.eventSource.addEventListener('job_failed', (event) => {
      const job = JSON.parse(event.data);

      this.toastService.error(
        'Job Failed',
        `${this.getJobTypeLabel(job.job_type)} encountered an error: ${job.error_message}`,
        {
          duration: 15000,
          action: {
            label: 'Retry',
            onClick: () => this.retryJob(job.id)
          }
        }
      );
    });
  }

  navigateToResults(job: BatchJob) {
    // Navigate to workbench and auto-load results
    this.router.navigate(['/'], {
      queryParams: {
        loadJob: job.id,
        resultId: job.result_id
      }
    });
  }

  getJobTypeLabel(jobType: string): string {
    return jobType === 'contract_comparison'
      ? 'Contract comparison'
      : 'Contract query';
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

**Strategy 2: Browser Notifications** (Enhanced UX)
```typescript
// Request permission on app load
if ('Notification' in window && Notification.permission === 'default') {
  Notification.requestPermission();
}

// Send notification when job completes
this.eventSource.addEventListener('job_completed', (event) => {
  const job = JSON.parse(event.data);

  // Toast notification (in-app)
  this.toastService.success('Job Completed', '...');

  // Browser notification (even when tab is not active)
  if (Notification.permission === 'granted') {
    const notification = new Notification('Contract Analysis Complete', {
      body: `Your ${this.getJobTypeLabel(job.job_type)} has finished processing.`,
      icon: '/assets/logo.png',
      tag: job.id,
      requireInteraction: true
    });

    notification.onclick = () => {
      window.focus();
      this.navigateToResults(job);
      notification.close();
    };
  }
});
```

**Strategy 3: Polling Fallback**
```typescript
// For browsers that don't support SSE
pollForJobUpdates() {
  setInterval(() => {
    this.jobService.getUserJobs('system', ['processing', 'queued']).subscribe({
      next: (response) => {
        // Check for newly completed jobs
        response.jobs.forEach(job => {
          if (this.wasJustCompleted(job)) {
            this.showCompletionNotification(job);
          }
        });
      }
    });
  }, 15000);  // Poll every 15 seconds
}
```

#### 4. Visual Indicators

**Job Status Badge in Navigation**:
```html
<!-- Show active job count in navigation bar -->
<nav class="top-nav">
  <button (click)="showJobMonitor = !showJobMonitor" class="job-indicator">
    <span class="icon">📊</span>
    <span class="job-count" *ngIf="activeJobCount > 0">
      {{ activeJobCount }}
    </span>
  </button>
</nav>
```

**Real-time Progress in Job Cards**:
```html
<div class="job-card processing">
  <!-- Animated progress bar -->
  <div class="progress-bar">
    <div class="progress-fill animate-pulse"
         [style.width.%]="job.progress.percentage">
    </div>
  </div>

  <!-- Step-by-step progress -->
  <div class="progress-steps">
    <div class="step" [class.active]="job.progress.current_step === 'retrieving_data'">
      1. Retrieving data
    </div>
    <div class="step" [class.active]="job.progress.current_step === 'calling_llm'">
      2. AI Analysis
    </div>
    <div class="step" [class.active]="job.progress.current_step === 'processing_results'">
      3. Processing results
    </div>
  </div>

  <!-- Estimated time remaining -->
  <small *ngIf="job.progress.estimated_time_remaining">
    Estimated time: {{ formatTime(job.progress.estimated_time_remaining) }}
  </small>
</div>
```

### Summary: UX Integration Decisions

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Same UI for batch/real-time results?** | ✅ YES | Reuse existing comparison/query result components |
| **Navigate from job monitor to results?** | ✅ YES | "View Results" button loads `result_id` into existing UI |
| **Toast notification on completion?** | ✅ YES | SSE + toast with action button + optional browser notification |
| **Token threshold already implemented?** | ✅ YES | Lines 1114-1120 show warning, batch processing needs implementation |

**Key Benefits**:
- ✅ Consistent UX between real-time and batch modes
- ✅ Seamless navigation from job status to results
- ✅ Multi-channel notifications (toast + browser)
- ✅ Reuses existing UI code (lower maintenance)
- ✅ Leverages existing token budget detection logic

---

## Proposed Batch Processing Architecture

### Design Goals

1. **Non-Blocking Operations**: User can submit job and continue working
2. **Progress Tracking**: Real-time status updates
3. **Job Management**: View, cancel, retry jobs
4. **Result Persistence**: Automatic saving of all results
5. **Scalability**: Handle multiple concurrent jobs
6. **Reusability**: Apply to both Compare and Query operations

### Architecture Components

#### 1. Job Queue System

**CosmosDB Container**: `job_queue`

**Job Document Structure**:
```json
{
  "id": "job_uuid",
  "type": "batch_job",
  "user_id": "system",
  "job_type": "contract_comparison" | "contract_query",
  "status": "queued" | "processing" | "completed" | "failed" | "cancelled",
  "priority": 1-10,

  // Request parameters
  "request": {
    // For comparisons
    "standardContractId": "contract_xxx",
    "compareContractIds": ["contract_yyy", "contract_zzz"],
    "comparisonMode": "clauses",
    "selectedClauses": ["Indemnity"],
    "modelSelection": "primary",

    // For queries
    "question": "What are the payment terms?",
    "contract_ids": ["contract_xxx", "contract_yyy"]
  },

  // Progress tracking
  "progress": {
    "current_step": "retrieving_data" | "generating_prompt" | "calling_llm" | "processing_results",
    "current_item": 1,
    "total_items": 5,
    "percentage": 20,
    "message": "Comparing contract 1 of 5...",
    "estimated_time_remaining": 45  // seconds
  },

  // Results
  "result_id": "result_uuid",  // Links to analysis_results container
  "error_message": null,

  // Metadata
  "created_date": "2025-01-10T12:00:00Z",
  "started_date": "2025-01-10T12:00:05Z",
  "completed_date": "2025-01-10T12:00:50Z",
  "elapsed_time": 45.2,

  // Partition key
  "partition_key": "system"  // user_id for partitioning
}
```

**Index Policy**:
- Partition key: `/user_id`
- Indexed: `status`, `job_type`, `created_date`, `priority`
- TTL: 7 days for completed/failed jobs (configurable)

#### 2. Background Worker Service

**Implementation Options**:

**Option A: FastAPI Background Tasks** (Simplest)
```python
from fastapi import BackgroundTasks

@app.post("/api/compare-contracts-batch")
async def compare_contracts_batch(request: Request, background_tasks: BackgroundTasks):
    # Create job record
    job_id = await job_service.create_job(...)

    # Queue background task
    background_tasks.add_task(process_comparison_job, job_id)

    # Return immediately
    return {"job_id": job_id, "status": "queued"}
```

**Pros**:
- Simple implementation
- No additional infrastructure
- Built into FastAPI

**Cons**:
- Limited to single server
- No job persistence across restarts
- No advanced scheduling

**Option B: Azure Functions** (Recommended for Production)
- Durable Functions for orchestration
- Automatic scaling
- Better monitoring/logging
- Queue-triggered execution

**Option C: Celery** (If self-hosting)
- Distributed task queue
- Redis/RabbitMQ backend
- Advanced features (retries, chaining, etc.)

**Recommendation**: Start with Option A, migrate to Option B for production

#### 3. Progress Tracking Mechanism

**WebSocket Connection** (Real-time updates):

```typescript
// Angular Component
export class ContractWorkbenchComponent {
  private jobSocket: WebSocket;

  startBatchComparison() {
    // 1. Submit job
    this.contractService.submitBatchJob(request).subscribe(response => {
      const jobId = response.job_id;

      // 2. Connect to WebSocket for updates
      this.connectJobSocket(jobId);

      // 3. Show job in UI
      this.activeJobs.push({
        id: jobId,
        status: 'queued',
        progress: 0
      });
    });
  }

  connectJobSocket(jobId: string) {
    this.jobSocket = new WebSocket(`wss://localhost:8000/ws/jobs/${jobId}`);

    this.jobSocket.onmessage = (event) => {
      const update = JSON.parse(event.data);
      this.updateJobProgress(jobId, update);
    };
  }
}
```

**Backend WebSocket Endpoint**:
```python
from fastapi import WebSocket

@app.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()

    try:
        while True:
            # Poll job status from CosmosDB
            job = await job_service.get_job(job_id)

            # Send update to client
            await websocket.send_json({
                "status": job["status"],
                "progress": job["progress"],
                "current_step": job["progress"]["current_step"],
                "message": job["progress"]["message"]
            })

            # Exit if job finished
            if job["status"] in ["completed", "failed", "cancelled"]:
                break

            # Poll every 2 seconds
            await asyncio.sleep(2)

    finally:
        await websocket.close()
```

**Alternative: Server-Sent Events (SSE)** (Simpler):
```python
from sse_starlette.sse import EventSourceResponse

@app.get("/api/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    async def event_generator():
        while True:
            job = await job_service.get_job(job_id)

            yield {
                "event": "progress",
                "data": json.dumps({
                    "status": job["status"],
                    "progress": job["progress"]
                })
            }

            if job["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())
```

#### 4. Job Processing Worker

**Core Worker Function**:
```python
async def process_comparison_job(job_id: str):
    """
    Background worker for contract comparison jobs
    """
    try:
        # 1. Update status to processing
        await job_service.update_job_status(job_id, "processing")

        # 2. Get job details
        job = await job_service.get_job(job_id)
        request = job["request"]

        # 3. Initialize services
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()

        # 4. Process with progress updates
        total_contracts = len(request["compareContractIds"])

        # Update: Retrieving data
        await job_service.update_progress(job_id, {
            "current_step": "retrieving_data",
            "percentage": 10,
            "message": "Retrieving contract data..."
        })

        standard_data, comparison_data, clause_cache = await retrieve_comparison_data(
            nosql_svc,
            request["standardContractId"],
            request["compareContractIds"],
            request["comparisonMode"],
            request.get("selectedClauses")
        )

        # Update: Generating prompt
        await job_service.update_progress(job_id, {
            "current_step": "generating_prompt",
            "percentage": 30,
            "message": "Preparing AI analysis..."
        })

        llm_prompt = create_comparison_prompt(
            standard_data,
            comparison_data,
            request["comparisonMode"]
        )

        # Update: Calling LLM
        await job_service.update_progress(job_id, {
            "current_step": "calling_llm",
            "percentage": 50,
            "message": f"Analyzing {total_contracts} contracts..."
        })

        llm_response = ai_svc.get_completion_for_contracts(
            user_prompt=llm_prompt,
            system_prompt="You are a legal contract analysis expert...",
            max_tokens=6000,
            model_selection=request["modelSelection"]
        )

        # Update: Processing results
        await job_service.update_progress(job_id, {
            "current_step": "processing_results",
            "percentage": 80,
            "message": "Formatting results..."
        })

        # Parse and enhance results
        comparison_results = json.loads(llm_response)
        if request["comparisonMode"] == "clauses":
            comparison_results = await enhance_comparison_response(
                comparison_results,
                clause_cache
            )

        # 5. AUTOMATICALLY SAVE RESULTS to analysis_results container
        result_id = await analysis_results_service.save_comparison_result(
            SaveComparisonRequest(
                user_id=job["user_id"],
                standard_contract_id=request["standardContractId"],
                compare_contract_ids=request["compareContractIds"],
                comparison_mode=request["comparisonMode"],
                selected_clauses=request.get("selectedClauses"),
                results=comparison_results,
                metadata={
                    "title": f"Batch Comparison: {request['standardContractId']}",
                    "description": f"{request['comparisonMode']} comparison",
                    "job_id": job_id
                }
            )
        )

        # 6. Update job as completed
        await job_service.complete_job(job_id, result_id)

        # 7. Clean up
        await nosql_svc.close()

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        await job_service.fail_job(job_id, str(e))
```

**Progress Update Granularity**:
- For multi-contract comparisons: Update after each contract
- Include estimated time remaining based on avg time per contract
- Send heartbeat updates every 5 seconds even if no progress

#### 5. Angular UI Components

**Job Status Dashboard**:
```typescript
// New component: job-status-panel.component.ts
export class JobStatusPanelComponent {
  activeJobs: BatchJob[] = [];
  completedJobs: BatchJob[] = [];

  ngOnInit() {
    // Load user's jobs
    this.loadJobs();

    // Auto-refresh every 5 seconds
    interval(5000).subscribe(() => this.loadJobs());
  }

  loadJobs() {
    this.jobService.getUserJobs('system').subscribe(jobs => {
      this.activeJobs = jobs.filter(j =>
        ['queued', 'processing'].includes(j.status)
      );
      this.completedJobs = jobs.filter(j =>
        ['completed', 'failed'].includes(j.status)
      );
    });
  }

  viewResults(job: BatchJob) {
    if (job.result_id) {
      this.router.navigate(['/results', job.result_id]);
    }
  }

  cancelJob(job: BatchJob) {
    this.jobService.cancelJob(job.id).subscribe();
  }

  retryJob(job: BatchJob) {
    this.jobService.retryJob(job.id).subscribe();
  }
}
```

**Job Progress Display**:
```html
<!-- Job status card -->
<div *ngFor="let job of activeJobs" class="job-card">
  <div class="job-header">
    <h4>{{ getJobTitle(job) }}</h4>
    <span class="status-badge" [class]="job.status">{{ job.status }}</span>
  </div>

  <div class="progress-bar">
    <div class="progress-fill" [style.width.%]="job.progress.percentage"></div>
  </div>

  <p class="progress-message">{{ job.progress.message }}</p>

  <div class="job-actions">
    <button *ngIf="job.status === 'queued'" (click)="cancelJob(job)">
      Cancel
    </button>
    <button *ngIf="job.status === 'completed'" (click)="viewResults(job)">
      View Results
    </button>
  </div>
</div>
```

### API Endpoints Summary

#### Batch Processing Endpoints

**1. Submit Job**
```
POST /api/jobs/comparison
Body: { request: ComparisonRequest, priority: 5 }
Response: { job_id: "uuid", status: "queued" }
```

**2. Submit Query Job**
```
POST /api/jobs/query
Body: { question: "...", contract_ids: [...], priority: 5 }
Response: { job_id: "uuid", status: "queued" }
```

**3. Get Job Status**
```
GET /api/jobs/{job_id}
Response: { id, status, progress, result_id, ... }
```

**4. Get User Jobs**
```
GET /api/jobs/user/{user_id}?status=queued,processing&limit=50
Response: { jobs: [...], total: 123 }
```

**5. Stream Job Progress**
```
GET /api/jobs/{job_id}/stream (SSE)
Events: progress, completed, failed
```

**6. Cancel Job**
```
POST /api/jobs/{job_id}/cancel
Response: { success: true }
```

**7. Retry Failed Job**
```
POST /api/jobs/{job_id}/retry
Response: { new_job_id: "uuid" }
```

---

## Comparison: Real-time vs Batch Mode

### Current Real-time Mode
**Pros**:
- ✅ Immediate results
- ✅ Simple implementation
- ✅ No additional infrastructure

**Cons**:
- ❌ Blocking operation
- ❌ No progress visibility
- ❌ Results lost if browser closes
- ❌ HTTP timeout issues for long operations
- ❌ Can't compare many contracts at once
- ❌ Single-threaded processing

### Proposed Batch Mode
**Pros**:
- ✅ Non-blocking - user continues working
- ✅ Real-time progress updates
- ✅ Automatic result persistence
- ✅ Can handle large batches (10s-100s of contracts)
- ✅ Resilient to browser/network issues
- ✅ Job history and retry capability
- ✅ Scalable with multiple workers
- ✅ Better resource management

**Cons**:
- ❌ More complex implementation
- ❌ Requires additional infrastructure (workers, queue)
- ❌ Slight delay before results available
- ❌ Needs job management UI

---

## Implementation Phases

### Phase 1: Job Queue Infrastructure (Week 1-2)
1. Create `job_queue` CosmosDB container
2. Implement JobService for CRUD operations
3. Add job submission endpoints
4. Basic job listing/status endpoints

### Phase 2: Background Worker (Week 2-3)
1. Implement FastAPI background task worker
2. Port comparison logic to async job processor
3. Add progress tracking updates
4. Automatic result saving

### Phase 3: Progress Tracking (Week 3-4)
1. Implement SSE or WebSocket for progress updates
2. Add estimated time remaining calculation
3. Heartbeat mechanism

### Phase 4: Angular UI (Week 4-5)
1. Job submission from Compare page
2. Job status panel component
3. Job list/history view
4. Result viewing integration
5. Cancel/retry functionality

### Phase 5: Query Contracts Integration (Week 5-6)
1. Adapt architecture for query operations
2. Batch query processing
3. UI integration

### Phase 6: Advanced Features (Week 6+)
1. Job prioritization
2. Scheduled jobs
3. Job templates
4. Bulk operations
5. Email notifications on completion

---

## Storage Requirements

### CosmosDB Containers

**1. job_queue** (New)
- Partition key: `/user_id`
- Estimated size: 1KB per job
- Retention: 7 days (auto-delete via TTL)
- Throughput: 400 RU/s (autoscale)

**2. analysis_results** (Existing)
- Will store ALL batch job results automatically
- Current manual save becomes automatic
- Estimated growth: 50-500KB per comparison

**3. model_usage** (Existing)
- No changes
- Continues automatic LLM tracking

### Cost Estimation

**Assuming 100 jobs/day**:
- Job queue storage: ~100KB/day
- Analysis results: ~5-50MB/day
- Total additional cost: ~$5-10/month

---

## Benefits Summary

### For Users
1. **Non-blocking**: Submit job, continue working, get notified
2. **Transparency**: See exactly what's happening in real-time
3. **Reliability**: Results automatically saved, never lost
4. **Scale**: Compare 10s or 100s of contracts effortlessly
5. **History**: View all past comparisons

### For System
1. **Resource Management**: Better control over concurrent operations
2. **Monitoring**: Track all jobs, identify bottlenecks
3. **Scalability**: Easy to add more workers
4. **Resilience**: Jobs persist across restarts
5. **Analytics**: Rich data on usage patterns

### For Development
1. **Separation of Concerns**: Clean job/worker architecture
2. **Testability**: Jobs can be tested independently
3. **Extensibility**: Easy to add new job types
4. **Reusability**: Same infrastructure for Compare & Query

---

## Migration Strategy

### Dual Mode Support
Keep both modes during transition:

```typescript
// Angular component
runComparison() {
  if (this.processingMode === 'realtime') {
    // Existing synchronous call
    this.contractService.compareContracts(request).subscribe(...)
  } else {
    // New batch mode
    this.contractService.submitBatchJob(request).subscribe(...)
  }
}
```

**Transition Plan**:
1. **Week 1-4**: Batch mode available as opt-in
2. **Week 5-6**: Make batch mode default, keep real-time as fallback
3. **Week 7+**: Phase out real-time mode for multi-contract comparisons
4. **Real-time mode preserved for**: Single contract operations, clause library comparisons

---

## Risk Mitigation

### Potential Issues

**1. Worker Failures**
- **Mitigation**: Job retry mechanism, dead letter queue
- **Implementation**: Max 3 retries with exponential backoff

**2. Stale Progress**
- **Mitigation**: Heartbeat mechanism, timeout detection
- **Implementation**: Update job every 5s, mark stale if >30s no update

**3. Result Storage Failures**
- **Mitigation**: Transactional job completion, rollback on failure
- **Implementation**: Store result first, then mark job complete

**4. Scale/Performance**
- **Mitigation**: Rate limiting, queue depth monitoring
- **Implementation**: Max 10 concurrent jobs per user, 100 system-wide

**5. Cost Overruns**
- **Mitigation**: Job quotas, cost tracking
- **Implementation**: Daily job limit per user, cost alerts

---

## Testing Strategy

### Unit Tests
- JobService CRUD operations
- Worker processing logic
- Progress calculation
- Error handling

### Integration Tests
- End-to-end job submission → completion
- WebSocket/SSE connection handling
- Result retrieval after completion
- Cancellation/retry flows

### Load Tests
- 100 concurrent jobs
- 1000 jobs/hour sustained
- Worker failure scenarios
- Database connection pool stress

---

## Monitoring & Observability

### Metrics to Track
1. **Job Metrics**:
   - Jobs queued/processing/completed/failed (count)
   - Average job duration by type
   - Queue depth over time
   - Worker utilization

2. **Performance Metrics**:
   - Time to first progress update
   - LLM call duration
   - Database operation latency
   - WebSocket connection count

3. **Business Metrics**:
   - Jobs per user per day
   - Most common job types
   - Average contracts per comparison
   - Cost per job

### Alerts
- Queue depth > 100
- Job failure rate > 5%
- Average job duration > 2x baseline
- Worker down/unresponsive

---

## Conclusion

This batch processing architecture provides:
1. **Better UX**: Non-blocking, transparent, reliable
2. **Scalability**: Handle large workloads efficiently
3. **Maintainability**: Clean separation of concerns
4. **Extensibility**: Easy to add new job types
5. **Cost Efficiency**: Better resource utilization

**Recommended Next Steps**:
1. Review and approve architecture
2. Create detailed implementation tickets
3. Set up development environment for testing
4. Start with Phase 1 implementation
