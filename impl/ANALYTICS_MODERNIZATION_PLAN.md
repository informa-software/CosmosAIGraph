# Analytics Page Modernization Plan

## Current State Analysis

### Backend Endpoints

#### OLD Endpoints (Need Update)
These endpoints use the old data format and need to be updated:

1. **`/api/analytics/usage-summary`** (lines 47-141)
   - ❌ Queries `c.tokens` (old format)
   - ❌ Only shows model-level breakdowns
   - ❌ Doesn't differentiate between operation types
   - ❌ Missing prompt/completion token split
   - ⚠️ Used by Angular UI

2. **`/api/analytics/cost-savings`** (lines 144-247)
   - ❌ Queries `c.tokens` (old format)
   - ❌ Hardcoded to only analyze "gpt-4.1" model
   - ❌ Doesn't account for different operation types
   - ⚠️ Used by Angular UI

3. **`/api/analytics/usage-timeline`** (lines 250-330)
   - ❌ Queries `c.tokens` (old format)
   - ❌ Only groups by date+model
   - ❌ No operation type visibility
   - ⚠️ Used by Angular UI

#### NEW Endpoints (Already Correct)
These endpoints use the new data format correctly:

1. **`/api/analytics/operation-breakdown`** (line 333+)
   - ✅ Uses `c.api_type = 'completion'`
   - ✅ Groups by operation type
   - ✅ Uses `c.prompt_tokens`, `c.completion_tokens`, `c.total_tokens`
   - ✅ Calculates success rates
   - ❌ NOT used by Angular UI yet

2. **`/api/analytics/token-efficiency`** (added earlier)
   - ✅ Analyzes prompt vs completion token ratios
   - ✅ Provides optimization recommendations
   - ❌ NOT used by Angular UI yet

3. **`/api/analytics/error-analysis`** (added earlier)
   - ✅ Tracks success/failure rates
   - ✅ Analyzes error patterns
   - ❌ NOT used by Angular UI yet

### Frontend (Angular)

#### Current Analytics Page
**File**: `query-builder/src/app/analytics/analytics.component.ts`

**What It Shows** (Contract Comparison Only):
- Summary cards: Total operations, tokens, cost, potential savings
- Model breakdown: GPT-4.1 vs GPT-4.1-mini
- Cost savings analysis
- Daily timeline

**What It's Missing**:
- ❌ No visibility into different operation types (compliance, clause comparison, SPARQL generation, etc.)
- ❌ No token efficiency metrics (prompt vs completion ratios)
- ❌ No error rate tracking
- ❌ No per-operation performance metrics
- ❌ No success rate visibility
- ❌ Limited to only "contract_comparison" operations

## Data Format Comparison

### OLD Format (deprecated)
```json
{
  "id": "uuid",
  "type": "model_usage",
  "user_email": "user@example.com",
  "model": "gpt-4.1",
  "operation": "contract_comparison",
  "tokens": 5000,              // ❌ Single field, estimated
  "elapsed_time": 2.5,
  "timestamp": "2024-01-01T12:00:00",
  "estimated_cost": 0.15
}
```

### NEW Format (current)
```json
{
  "id": "uuid",
  "type": "model_usage",
  "api_type": "completion",      // ✅ NEW: completion/embedding
  "user_email": "system",
  "operation": "compliance_evaluation",  // ✅ 11 operation types
  "operation_details": {         // ✅ NEW: Context-specific metadata
    "rule_count": 2,
    "contract_length": 12345,
    "batch_evaluation": true
  },
  "model": "gpt-4",
  "prompt_tokens": 3000,        // ✅ NEW: Actual from API
  "completion_tokens": 2000,    // ✅ NEW: Actual from API
  "total_tokens": 5000,         // ✅ NEW: Calculated
  "elapsed_time": 2.345,
  "timestamp": "2024-01-01T12:00:00.123456",
  "estimated_cost": 0.15,
  "success": true,               // ✅ NEW: Success tracking
  "error_message": null          // ✅ NEW: Error details
}
```

## Tracked Operations

The new system tracks **11 operation types**:

1. `sparql_generation` - Natural language → SPARQL query generation
2. `contract_comparison` - Contract-to-contract comparisons
3. `compliance_evaluation` - Compliance rule evaluations
4. `compliance_recommendation` - Compliance fix recommendations
5. `clause_comparison` - Clause library comparisons
6. `clause_suggestion` - Clause library suggestions
7. `query_planning` - Query planning and execution
8. `rag_embedding` - RAG vector embeddings
9. `generic_completion` - Generic AI completions
10. `word_addin_evaluation` - Word Add-in evaluations
11. `word_addin_comparison` - Word Add-in track changes

## Modernization Plan

### Phase 1: Update Backend Endpoints

#### Step 1.1: Update `/api/analytics/usage-summary`
**Changes needed**:
```python
# OLD query
SELECT c.model, c.tokens, c.estimated_cost, c.elapsed_time
WHERE c.type = 'model_usage'

# NEW query
SELECT c.model, c.operation, c.api_type,
       c.prompt_tokens, c.completion_tokens, c.total_tokens,
       c.estimated_cost, c.elapsed_time, c.success
WHERE c.type = 'model_usage'
  AND c.api_type = 'completion'  # Separate completions from embeddings
```

**New response structure**:
```json
{
  "period_days": 30,
  "start_date": "...",
  "end_date": "...",
  "user_email": "system",
  "operations": [                    // NEW: Group by operation instead of just model
    {
      "operation": "contract_comparison",
      "operation_name": "Contract Comparison",
      "total_count": 50,
      "success_count": 48,
      "success_rate": 96.0,
      "total_prompt_tokens": 150000,
      "total_completion_tokens": 100000,
      "total_tokens": 250000,
      "total_cost": 7.50,
      "avg_time": 2.5,
      "models_used": ["gpt-4", "gpt-4.1-mini"]
    },
    {
      "operation": "compliance_evaluation",
      // ...similar structure
    }
  ],
  "models": [                        // KEEP: Model-level summary
    {
      "model": "gpt-4",
      "total_operations": 100,
      "total_tokens": 500000,
      "total_cost": 15.00,
      "avg_time": 2.3
    }
  ],
  "totals": {
    "total_operations": 150,
    "total_prompt_tokens": 300000,
    "total_completion_tokens": 200000,
    "total_tokens": 500000,
    "total_cost": 15.00,
    "success_rate": 95.5
  }
}
```

#### Step 1.2: Update `/api/analytics/cost-savings`
**Changes needed**:
```python
# OLD: Only analyze gpt-4.1 → gpt-4.1-mini
WHERE c.model = 'gpt-4.1'

# NEW: Analyze all expensive models
WHERE c.model IN ('gpt-4', 'gpt-4.1', 'gpt-4o')
  AND c.api_type = 'completion'

# Calculate savings per operation type
# Show which operations have highest savings potential
```

#### Step 1.3: Update `/api/analytics/usage-timeline`
**Changes needed**:
```python
# Group by (date, model) only - one row per day per model
# Simplified for better user experience
key = (date, model)

# Aggregates all operation types for each day/model combination
```

### Phase 2: Enhance Angular Frontend

#### Step 2.1: Add Operation Type Breakdown Section
**New component section** after model breakdown:

```html
<!-- Operation Breakdown -->
<div class="section-card">
  <div class="section-header">
    <h2>📋 Operation Type Breakdown</h2>
    <p class="section-subtitle">Usage by operation type</p>
  </div>

  <div class="operation-grid">
    <div *ngFor="let op of operationBreakdown" class="operation-card">
      <div class="operation-header">
        <span class="operation-icon">{{ getOperationIcon(op.operation) }}</span>
        <h3>{{ op.operation_name }}</h3>
      </div>

      <div class="operation-stats">
        <div class="stat-row">
          <span>Operations:</span>
          <span class="stat-value">{{ formatNumber(op.total_count) }}</span>
        </div>
        <div class="stat-row">
          <span>Success Rate:</span>
          <span class="stat-value" [class]="getSuccessRateClass(op.success_rate)">
            {{ op.success_rate.toFixed(1) }}%
          </span>
        </div>
        <div class="stat-row">
          <span>Tokens:</span>
          <span class="stat-value">{{ formatNumber(op.total_tokens) }}</span>
        </div>
        <div class="stat-row">
          <span>Cost:</span>
          <span class="stat-value">{{ formatCurrency(op.total_cost) }}</span>
        </div>
        <div class="stat-row">
          <span>Avg Time:</span>
          <span class="stat-value">{{ formatTime(op.avg_time) }}</span>
        </div>
      </div>
    </div>
  </div>
</div>
```

#### Step 2.2: Add Token Efficiency Section
**New component section**:

```html
<!-- Token Efficiency Analysis -->
<div class="section-card">
  <div class="section-header">
    <h2>⚡ Token Efficiency</h2>
    <p class="section-subtitle">Prompt vs completion token analysis</p>
  </div>

  <div class="efficiency-grid">
    <div *ngFor="let op of tokenEfficiency" class="efficiency-card">
      <h4>{{ op.operation_name }}</h4>

      <div class="token-ratio-bar">
        <div class="prompt-portion"
             [style.width.%]="op.prompt_percentage">
          <span>Prompt {{ op.prompt_percentage.toFixed(0) }}%</span>
        </div>
        <div class="completion-portion"
             [style.width.%]="op.completion_percentage">
          <span>Completion {{ op.completion_percentage.toFixed(0) }}%</span>
        </div>
      </div>

      <div class="efficiency-details">
        <div class="detail-row">
          <span>Prompt Tokens:</span>
          <span>{{ formatNumber(op.avg_prompt_tokens) }}</span>
        </div>
        <div class="detail-row">
          <span>Completion Tokens:</span>
          <span>{{ formatNumber(op.avg_completion_tokens) }}</span>
        </div>
        <div class="detail-row">
          <span>Efficiency:</span>
          <span [class]="getEfficiencyClass(op.efficiency_rating)">
            {{ op.efficiency_rating }}
          </span>
        </div>
      </div>

      <div class="recommendation-note" *ngIf="op.recommendation">
        💡 {{ op.recommendation }}
      </div>
    </div>
  </div>
</div>
```

#### Step 2.3: Add Error Tracking Section
**New component section**:

```html
<!-- Error Analysis -->
<div class="section-card" *ngIf="errorAnalysis && errorAnalysis.total_errors > 0">
  <div class="section-header">
    <h2>⚠️ Error Analysis</h2>
    <p class="section-subtitle">Failed operations and error patterns</p>
  </div>

  <div class="error-summary">
    <div class="error-stat">
      <h3>{{ errorAnalysis.total_errors }}</h3>
      <p>Total Errors</p>
    </div>
    <div class="error-stat">
      <h3>{{ errorAnalysis.error_rate.toFixed(1) }}%</h3>
      <p>Error Rate</p>
    </div>
    <div class="error-stat">
      <h3>{{ errorAnalysis.most_reliable_operation }}</h3>
      <p>Most Reliable</p>
    </div>
  </div>

  <div class="error-list">
    <div *ngFor="let pattern of errorAnalysis.error_patterns" class="error-item">
      <div class="error-operation">{{ pattern.operation_name }}</div>
      <div class="error-count">{{ pattern.count }} errors</div>
      <div class="error-rate">{{ pattern.error_rate.toFixed(1) }}% failure rate</div>
      <div class="error-message">{{ pattern.common_error }}</div>
    </div>
  </div>
</div>
```

#### Step 2.4: Update TypeScript Service
**File**: `user-preferences.service.ts`

Add new interfaces and methods:

```typescript
export interface OperationBreakdown {
  operation: string;
  operation_name: string;
  total_count: number;
  success_count: number;
  success_rate: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost: number;
  avg_time: number;
  models_used: string[];
}

export interface TokenEfficiency {
  operation: string;
  operation_name: string;
  total_operations: number;
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
  prompt_percentage: number;
  completion_percentage: number;
  efficiency_rating: string;
  recommendation: string;
}

export interface ErrorAnalysis {
  period_days: number;
  user_email: string;
  total_operations: number;
  total_errors: number;
  error_rate: number;
  most_reliable_operation: string;
  error_patterns: ErrorPattern[];
}

export interface ErrorPattern {
  operation: string;
  operation_name: string;
  count: number;
  error_rate: number;
  common_error: string;
}

// Add new methods
getOperationBreakdown(userEmail: string, days: number): Observable<any> {
  const params = new HttpParams()
    .set('user_email', userEmail)
    .set('days', days.toString());

  return this.http.get(`${this.analyticsUrl}/operation-breakdown`, { params });
}

getTokenEfficiency(userEmail: string, days: number): Observable<TokenEfficiency[]> {
  const params = new HttpParams()
    .set('user_email', userEmail)
    .set('days', days.toString());

  return this.http.get<TokenEfficiency[]>(`${this.analyticsUrl}/token-efficiency`, { params });
}

getErrorAnalysis(userEmail: string, days: number): Observable<ErrorAnalysis> {
  const params = new HttpParams()
    .set('user_email', userEmail)
    .set('days', days.toString());

  return this.http.get<ErrorAnalysis>(`${this.analyticsUrl}/error-analysis`, { params });
}
```

### Phase 3: Visual Enhancements

#### Add Operation Type Icons
```typescript
getOperationIcon(operation: string): string {
  const icons = {
    'sparql_generation': '🔍',
    'contract_comparison': '📄',
    'compliance_evaluation': '✅',
    'compliance_recommendation': '💡',
    'clause_comparison': '📋',
    'clause_suggestion': '🎯',
    'query_planning': '🗺️',
    'rag_embedding': '🔢',
    'generic_completion': '🤖',
    'word_addin_evaluation': '📝',
    'word_addin_comparison': '🔄'
  };
  return icons[operation] || '📊';
}
```

#### Add Success Rate Color Coding
```typescript
getSuccessRateClass(rate: number): string {
  if (rate >= 99) return 'success-excellent';  // Green
  if (rate >= 95) return 'success-good';       // Light green
  if (rate >= 90) return 'success-fair';       // Yellow
  if (rate >= 80) return 'success-poor';       // Orange
  return 'success-critical';                    // Red
}
```

## Implementation Priority

### High Priority (Do First)
1. ✅ Update `/api/analytics/usage-summary` to use new data format
2. ✅ Update `/api/analytics/cost-savings` to use new data format
3. ✅ Update `/api/analytics/usage-timeline` to use new data format
4. ✅ Update Angular service to call new endpoints
5. ✅ Add operation breakdown section to UI

### Medium Priority (Do Next)
6. ✅ Add token efficiency visualization
7. ✅ Add error tracking section
8. ✅ Update color schemes and icons

### Low Priority (Nice to Have)
9. ⬜ Add charts/graphs for trends
10. ⬜ Add export functionality (CSV/PDF)
11. ⬜ Add filters (by operation, by model, by date range)
12. ⬜ Add comparison mode (compare two time periods)

## Benefits of Modernization

### Current Analytics (Limited)
- Shows only contract comparison usage
- No visibility into other operations
- No error tracking
- Limited optimization insights
- Single dimension (model-centric)

### Modernized Analytics (Comprehensive)
- ✅ All 11 operation types tracked
- ✅ Token efficiency analysis (prompt vs completion)
- ✅ Error rate tracking and patterns
- ✅ Per-operation performance metrics
- ✅ Success rate visibility
- ✅ Multi-dimensional analysis (operation + model + time)
- ✅ Actionable optimization recommendations
- ✅ Cost optimization across all operation types

## Migration Notes

### Backward Compatibility
- Old format data will not appear in new endpoints (they query `api_type = 'completion'`)
- Need to decide: Archive old data or migrate it?
- Recommendation: **Keep old data for historical analysis, but focus new UI on new format only**

### User Email
- Old data: Mixed user emails
- New data: Currently using `"system"` as user_email
- TODO: Implement proper user authentication and pass actual user email to tracking

### Testing Checklist
- [ ] Test with empty data (no usage records)
- [ ] Test with single operation type
- [ ] Test with multiple operation types
- [ ] Test with failed operations (error tracking)
- [ ] Test with different time periods
- [ ] Test performance with large datasets (1000+ records)
- [ ] Test mobile responsiveness
- [ ] Test accessibility (screen readers, keyboard navigation)
