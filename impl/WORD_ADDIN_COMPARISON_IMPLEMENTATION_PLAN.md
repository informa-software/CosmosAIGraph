# Word Add-in Contract Comparison Implementation Plan

## Executive Summary

This plan outlines the implementation of Contract Comparison functionality in the Word Add-in, adding two comparison modes:
1. **Compare with Original** - Available only when Track Changes is enabled and changes exist
2. **Compare with Standard** - Always available, user selects standard contract from CosmosDB

Both modes will support full contract and clause-by-clause comparison, matching the web application functionality.

---

## 1. Current State Analysis

### Existing Functionality (Must Preserve)
- ✅ Compliance tab with rule set evaluation
- ✅ Track Changes detection (`isTrackChangesEnabled()`)
- ✅ Original text extraction (`extractOriginalText()`)
- ✅ Revised text extraction (`extractRevisedText()`)
- ✅ Dual compliance evaluation (original vs revised)
- ✅ Tab-based UI (`activeTab: 'compliance' | 'comparison'`)
- ✅ Session tracking with backend

### Existing Services & Patterns
- **TrackChangesService**: Handles track changes detection and text extraction
- **WordService**: Word API interactions, document manipulation
- **ApiService**: HTTP communication with FastAPI backend
- **Component Structure**: Tab-based with detail views

---

## 2. Architecture Overview

### 2.1 Frontend Components (Word Add-in)

```
word-addin.component.ts
├── Compliance Tab (existing - DO NOT MODIFY)
└── Comparison Tab (NEW)
    ├── Compare with Original (conditional)
    │   ├── Full Contract mode
    │   └── Clause by Clause mode
    └── Compare with Standard (always available)
        ├── Standard contract selector (dropdown)
        ├── Full Contract mode
        └── Clause by Clause mode
            └── Clause selection from standard contract
```

### 2.2 Backend API Changes

**New Endpoint Required:**
```
POST /api/compare_contracts_text
```

**Purpose**: Accept raw text content instead of contract IDs

**Request Model:**
```typescript
{
  standardContractId?: string,        // ID for standard contract
  standardContractText?: string,      // OR text for Word document as standard
  compareContractIds?: string[],      // IDs for comparison contracts
  compareContractTexts?: string[],    // OR texts for Word document comparisons
  comparisonMode: 'full' | 'clauses',
  selectedClauses?: string[] | 'all'
}
```

**Response**: Same as existing `/api/compare_contracts` endpoint

---

## 3. Detailed Implementation Plan

### Phase 1: Backend API Enhancement

#### 3.1.1 Create New Endpoint
**File**: `web_app/routers/comparison_router.py` (NEW or add to existing router)

**Implementation**:
```python
@router.post("/compare_contracts_text")
async def compare_contracts_with_text(request: CompareContractsTextRequest):
    """
    Compare contracts accepting either contract IDs or raw text
    Allows Word Add-in to pass document text directly
    """
    # Convert text to temporary contract objects
    # Call existing comparison logic
    # Return standard comparison response
```

#### 3.1.2 Update Comparison Service
**File**: `web_app/src/services/comparison_service.py` (or similar)

**Changes**:
- Accept optional text parameters alongside contract IDs
- Create temporary contract documents from text
- Process comparison as normal
- Clean up temporary documents after comparison

**Implementation Notes**:
- Use existing contract comparison logic
- Create temporary contract IDs like `word_standard_{timestamp}`, `word_compare_{timestamp}`
- Store temporarily in memory or with short TTL in CosmosDB
- Reuse all existing comparison algorithms

---

### Phase 2: Frontend Models & Services

#### 3.2.1 Create Comparison Models
**File**: `office-addin/src/app/models/comparison.models.ts` (NEW)

```typescript
export interface ContractComparisonRequest {
  standardContractId?: string;
  standardContractText?: string;
  compareContractIds?: string[];
  compareContractTexts?: string[];
  comparisonMode: 'full' | 'clauses';
  selectedClauses?: string[] | 'all';
}

export interface ContractComparisonResponse {
  // Match existing web app response structure
  success: boolean;
  results: {
    comparisons: ContractComparison[];
  };
  error?: string;
}

export interface ContractComparison {
  compared_contract_id: string;
  overall_similarity_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  critical_findings: Finding[];
  missing_clauses: MissingClause[];
  additional_clauses: AdditionalClause[];
  clause_comparisons: ClauseComparison[];
}

export interface Finding {
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  clause_type?: string;
}

export interface MissingClause {
  clause_type: string;
  importance: string;
  recommendation: string;
}

export interface AdditionalClause {
  clause_type: string;
  content_preview: string;
}

export interface ClauseComparison {
  clause_type: string;
  similarity_score: number;
  standard_content: string;
  compared_content: string;
  differences: string[];
  risk_assessment: string;
}
```

#### 3.2.2 Extend API Service
**File**: `office-addin/src/app/services/api.service.ts`

**Add Methods**:
```typescript
/**
 * Get all contracts for standard selection
 */
async getContracts(): Promise<Contract[]> {
  const url = `${this.API_BASE_URL}/api/contracts`;
  return firstValueFrom(
    this.http.get<{ contracts: Contract[] }>(url)
      .pipe(retry(2), catchError(this.handleError))
  ).then(response => response.contracts);
}

/**
 * Get contract by ID (for clause extraction)
 */
async getContract(contractId: string): Promise<Contract> {
  const url = `${this.API_BASE_URL}/api/contracts/${contractId}`;
  return firstValueFrom(
    this.http.get<Contract>(url)
      .pipe(retry(2), catchError(this.handleError))
  );
}

/**
 * Compare contracts with text support
 */
async compareContractsWithText(request: ContractComparisonRequest): Promise<ContractComparisonResponse> {
  const url = `${this.API_BASE_URL}/api/compare_contracts_text`;
  return firstValueFrom(
    this.http.post<ContractComparisonResponse>(url, request, this.httpOptions)
      .pipe(catchError(this.handleError))
  );
}
```

---

### Phase 3: Component Implementation

#### 3.3.1 Component State Management
**File**: `office-addin/src/app/word-addin/word-addin.component.ts`

**Add State Variables**:
```typescript
// Comparison tab state
comparisonMode: 'original' | 'standard' = 'standard';
comparisonType: 'full' | 'clauses' = 'full';

// Standard contract selection
contracts: Contract[] = [];
selectedStandardContractId: string = '';
selectedStandardContract: Contract | null = null;
loadingContracts = false;
contractsError: string | null = null;

// Clause selection
availableClauses: string[] = [];
selectedClauses: string[] = [];

// Comparison execution
isComparing = false;
comparisonProgress = 0;
comparisonError: string | null = null;

// Comparison results
comparisonResults: ContractComparisonResponse | null = null;
showComparisonResults = false;
expandedComparisonId: string | null = null;
```

#### 3.3.2 Component Methods

**Contract Loading**:
```typescript
async loadContracts(): Promise<void> {
  this.loadingContracts = true;
  this.contractsError = null;

  try {
    this.contracts = await this.apiService.getContracts();
    console.log(`Loaded ${this.contracts.length} contracts`);
  } catch (error) {
    this.contractsError = `Failed to load contracts: ${error.message}`;
    console.error('Error loading contracts:', error);
  } finally {
    this.loadingContracts = false;
  }
}
```

**Standard Contract Selection**:
```typescript
async selectStandardContract(contractId: string): Promise<void> {
  this.selectedStandardContractId = contractId;

  try {
    // Fetch full contract details to get available clauses
    this.selectedStandardContract = await this.apiService.getContract(contractId);

    // Extract available clause types
    if (this.selectedStandardContract.clauses) {
      this.availableClauses = Object.keys(this.selectedStandardContract.clauses);
    }

    // Default to all clauses selected
    this.selectedClauses = [...this.availableClauses];
  } catch (error) {
    console.error('Error fetching contract details:', error);
    this.showNotification('Failed to load contract details', 'error');
  }
}
```

**Compare with Original**:
```typescript
async compareWithOriginal(): Promise<void> {
  if (!this.trackChangesEnabled) {
    this.showNotification('Track changes must be enabled', 'warning');
    return;
  }

  this.isComparing = true;
  this.comparisonError = null;
  this.comparisonProgress = 0;

  try {
    // Extract original and revised text
    this.comparisonProgress = 20;
    const originalText = await this.trackChangesService.extractOriginalText();

    this.comparisonProgress = 40;
    const revisedText = await this.trackChangesService.extractRevisedText();

    // Create comparison request
    const request: ContractComparisonRequest = {
      standardContractText: originalText,
      compareContractTexts: [revisedText],
      comparisonMode: this.comparisonType,
      selectedClauses: this.comparisonType === 'clauses'
        ? (this.selectedClauses.length === this.availableClauses.length ? 'all' : this.selectedClauses)
        : undefined
    };

    // Submit comparison
    this.comparisonProgress = 60;
    this.comparisonResults = await this.apiService.compareContractsWithText(request);

    this.comparisonProgress = 100;
    this.showComparisonResults = true;

    console.log('Comparison complete');
  } catch (error) {
    this.comparisonError = error.message;
    console.error('Comparison error:', error);
  } finally {
    this.isComparing = false;
  }
}
```

**Compare with Standard**:
```typescript
async compareWithStandard(): Promise<void> {
  if (!this.selectedStandardContractId) {
    this.showNotification('Please select a standard contract', 'warning');
    return;
  }

  this.isComparing = true;
  this.comparisonError = null;
  this.comparisonProgress = 0;

  try {
    // Extract current document text
    this.comparisonProgress = 30;
    const currentText = this.trackChangesEnabled
      ? await this.trackChangesService.extractRevisedText()
      : await this.wordService.getDocumentText();

    // Create comparison request
    const request: ContractComparisonRequest = {
      standardContractId: this.selectedStandardContractId,
      compareContractTexts: [currentText],
      comparisonMode: this.comparisonType,
      selectedClauses: this.comparisonType === 'clauses'
        ? (this.selectedClauses.length === this.availableClauses.length ? 'all' : this.selectedClauses)
        : undefined
    };

    // Submit comparison
    this.comparisonProgress = 70;
    this.comparisonResults = await this.apiService.compareContractsWithText(request);

    this.comparisonProgress = 100;
    this.showComparisonResults = true;

    console.log('Comparison complete');
  } catch (error) {
    this.comparisonError = error.message;
    console.error('Comparison error:', error);
  } finally {
    this.isComparing = false;
  }
}
```

---

### Phase 4: UI Template

#### 3.4.1 Comparison Tab Template
**File**: `office-addin/src/app/word-addin/word-addin.component.html`

**Structure**:
```html
<!-- Comparison Tab -->
<div *ngIf="activeTab === 'comparison'" class="tab-content">

  <!-- Mode Selection -->
  <div class="comparison-mode-selector">
    <button
      [class.active]="comparisonMode === 'original'"
      [disabled]="!trackChangesEnabled || !hasTrackChanges()"
      (click)="comparisonMode = 'original'">
      Compare with Original
    </button>
    <button
      [class.active]="comparisonMode === 'standard'"
      (click)="comparisonMode = 'standard'">
      Compare with Standard
    </button>
  </div>

  <!-- Compare with Original View -->
  <div *ngIf="comparisonMode === 'original'" class="comparison-view">
    <div class="info-banner">
      <p>Compare the original document (before tracked changes) with the current version.</p>
    </div>

    <!-- Comparison Type -->
    <div class="comparison-type-selector">
      <label><input type="radio" [(ngModel)]="comparisonType" value="full"> Full Contract</label>
      <label><input type="radio" [(ngModel)]="comparisonType" value="clauses"> Clause by Clause</label>
    </div>

    <button class="btn-primary" (click)="compareWithOriginal()" [disabled]="isComparing">
      <span *ngIf="!isComparing">Compare Documents</span>
      <span *ngIf="isComparing">Comparing... {{comparisonProgress}}%</span>
    </button>
  </div>

  <!-- Compare with Standard View -->
  <div *ngIf="comparisonMode === 'standard'" class="comparison-view">

    <!-- Standard Contract Selector -->
    <div class="standard-selector">
      <label>Select Standard Contract:</label>
      <select
        [(ngModel)]="selectedStandardContractId"
        (change)="selectStandardContract($event.target.value)"
        [disabled]="loadingContracts || isComparing">
        <option value="">-- Select a Contract --</option>
        <option *ngFor="let contract of contracts" [value]="contract.id">
          {{ contract.title }}
        </option>
      </select>
    </div>

    <!-- Comparison Type -->
    <div class="comparison-type-selector" *ngIf="selectedStandardContractId">
      <label><input type="radio" [(ngModel)]="comparisonType" value="full"> Full Contract</label>
      <label><input type="radio" [(ngModel)]="comparisonType" value="clauses"> Clause by Clause</label>
    </div>

    <!-- Clause Selection (if clause-by-clause mode) -->
    <div class="clause-selector" *ngIf="comparisonType === 'clauses' && availableClauses.length > 0">
      <label>Select Clauses to Compare:</label>
      <div class="clause-list">
        <label *ngFor="let clause of availableClauses">
          <input type="checkbox"
            [checked]="selectedClauses.includes(clause)"
            (change)="toggleClause(clause)">
          {{ clause }}
        </label>
      </div>
    </div>

    <button
      class="btn-primary"
      (click)="compareWithStandard()"
      [disabled]="!selectedStandardContractId || isComparing">
      <span *ngIf="!isComparing">Compare with Standard</span>
      <span *ngIf="isComparing">Comparing... {{comparisonProgress}}%</span>
    </button>
  </div>

  <!-- Error Display -->
  <div *ngIf="comparisonError" class="error-message">
    <p>{{ comparisonError }}</p>
    <button (click)="comparisonError = null">Dismiss</button>
  </div>

  <!-- Results Display -->
  <div *ngIf="showComparisonResults && comparisonResults" class="comparison-results">
    <!-- Results visualization matching web app format -->
    <div *ngFor="let comparison of comparisonResults.results.comparisons" class="comparison-card">
      <div class="comparison-header">
        <h3>Comparison Results</h3>
        <div class="risk-badge" [class]="'risk-' + comparison.risk_level">
          {{ comparison.risk_level }}
        </div>
      </div>

      <div class="similarity-score">
        <label>Overall Similarity:</label>
        <span>{{ comparison.overall_similarity_score }}%</span>
      </div>

      <!-- Critical Findings -->
      <div *ngIf="comparison.critical_findings.length > 0" class="findings-section">
        <h4>Critical Findings ({{ comparison.critical_findings.length }})</h4>
        <div *ngFor="let finding of comparison.critical_findings" class="finding-item">
          <div class="finding-title">{{ finding.title }}</div>
          <div class="finding-description">{{ finding.description }}</div>
        </div>
      </div>

      <!-- Missing Clauses -->
      <div *ngIf="comparison.missing_clauses.length > 0" class="missing-clauses-section">
        <h4>Missing Clauses ({{ comparison.missing_clauses.length }})</h4>
        <div *ngFor="let clause of comparison.missing_clauses" class="clause-item">
          <div class="clause-type">{{ clause.clause_type }}</div>
          <div class="clause-recommendation">{{ clause.recommendation }}</div>
          <!-- Button to insert from clause library (Phase 2 feature) -->
        </div>
      </div>

      <!-- Clause Comparisons (if clause mode) -->
      <div *ngIf="comparisonType === 'clauses' && comparison.clause_comparisons" class="clause-comparisons">
        <h4>Clause Details</h4>
        <div *ngFor="let clauseComp of comparison.clause_comparisons" class="clause-comparison-item">
          <div class="clause-header" (click)="toggleClauseComparison(clauseComp.clause_type)">
            <span>{{ clauseComp.clause_type }}</span>
            <span class="similarity">{{ clauseComp.similarity_score }}%</span>
          </div>
          <div *ngIf="isClauseComparisonExpanded(clauseComp.clause_type)" class="clause-details">
            <div class="clause-content">
              <div class="standard-content">
                <label>Standard:</label>
                <p>{{ clauseComp.standard_content }}</p>
              </div>
              <div class="compared-content">
                <label>Your Document:</label>
                <p>{{ clauseComp.compared_content }}</p>
              </div>
            </div>
            <div *ngIf="clauseComp.differences.length > 0" class="differences">
              <label>Key Differences:</label>
              <ul>
                <li *ngFor="let diff of clauseComp.differences">{{ diff }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

## 4. Implementation Sequence

### Sprint 1: Backend Foundation (2-3 days)
1. ✅ Create `CompareContractsTextRequest` model
2. ✅ Create `POST /api/compare_contracts_text` endpoint
3. ✅ Update comparison service to handle text inputs
4. ✅ Test endpoint with Postman/curl
5. ✅ Write unit tests for new endpoint

### Sprint 2: Frontend Services (2 days)
1. ✅ Create `comparison.models.ts`
2. ✅ Add contract fetching methods to API service
3. ✅ Add `compareContractsWithText()` to API service
4. ✅ Test service methods with backend

### Sprint 3: Component Logic (3-4 days)
1. ✅ Add state variables to component
2. ✅ Implement `loadContracts()`
3. ✅ Implement `selectStandardContract()`
4. ✅ Implement `compareWithOriginal()`
5. ✅ Implement `compareWithStandard()`
6. ✅ Add clause selection logic
7. ✅ Test all methods in isolation

### Sprint 4: UI Implementation (2-3 days)
1. ✅ Create Comparison tab template
2. ✅ Add mode selector UI
3. ✅ Add standard contract dropdown
4. ✅ Add comparison type radio buttons
5. ✅ Add clause selection checkboxes
6. ✅ Style components to match existing add-in
7. ✅ Test responsiveness in task pane

### Sprint 5: Results Display (3-4 days)
1. ✅ Create results display template
2. ✅ Implement expandable sections
3. ✅ Add risk badges and similarity scores
4. ✅ Display critical findings
5. ✅ Display missing clauses
6. ✅ Display clause comparisons (if clause mode)
7. ✅ Style to match web app results

### Sprint 6: Testing & Refinement (2-3 days)
1. ✅ End-to-end testing of both comparison modes
2. ✅ Test with various document sizes
3. ✅ Test error scenarios (no network, large documents)
4. ✅ Performance testing
5. ✅ Cross-browser testing (Word Online vs Desktop)
6. ✅ Regression testing (ensure Compliance tab still works)

---

## 5. Testing Strategy

### 5.1 Unit Tests
- Backend endpoint with various input combinations
- Service methods for text handling
- Component methods in isolation

### 5.2 Integration Tests
- Full flow: Compare with Original
- Full flow: Compare with Standard (Full Contract)
- Full flow: Compare with Standard (Clause by Clause)
- Contract loading and selection
- Clause selection and filtering

### 5.3 User Acceptance Tests
| Test Case | Expected Result |
|-----------|----------------|
| Open Comparison tab without track changes | Only "Compare with Standard" enabled |
| Enable track changes with changes | Both comparison modes available |
| Select standard contract | Clauses populate for clause mode |
| Compare with Original (Full) | Shows overall similarity and findings |
| Compare with Original (Clauses) | Shows clause-by-clause breakdown |
| Compare with Standard (Full) | Shows comparison against selected contract |
| Compare with Standard (Clauses) | Shows only selected clauses |
| Large document (>1MB) | Shows "Coming Soon" error |
| Network error | Shows appropriate error message |
| Switch tabs during comparison | Maintains state, doesn't break |

### 5.4 Regression Tests
- Compliance tab still loads rule sets
- Track changes detection still works
- Original/revised text extraction still works
- Compliance evaluation still works
- Session tracking still works

---

## 6. Error Handling

### 6.1 User-Facing Errors
```typescript
// Document too large
if (documentText.length > 1000000) {  // 1MB limit
  throw new Error('Coming Soon: Support for large documents is in development.');
}

// No standard contract selected
if (!selectedStandardContractId && comparisonMode === 'standard') {
  this.showNotification('Please select a standard contract first', 'warning');
  return;
}

// Track changes not enabled
if (comparisonMode === 'original' && !trackChangesEnabled) {
  this.showNotification('Track changes must be enabled for this comparison mode', 'warning');
  return;
}

// No changes detected
if (comparisonMode === 'original' && !hasTrackChanges()) {
  this.showNotification('No tracked changes found in document', 'info');
  return;
}
```

### 6.2 Network Errors
```typescript
catch (error) {
  if (error.status === 0) {
    this.comparisonError = 'Unable to connect to server. Please check your connection.';
  } else if (error.status === 500) {
    this.comparisonError = 'Server error occurred. Please try again later.';
  } else {
    this.comparisonError = error.message || 'An unexpected error occurred';
  }
}
```

---

## 7. Risk Mitigation

### 7.1 Regression Risks
**Risk**: Breaking existing Compliance tab functionality

**Mitigation**:
- ✅ Zero changes to existing Compliance tab code
- ✅ New comparison code in separate methods
- ✅ Shared services (TrackChangesService) unchanged
- ✅ Comprehensive regression testing before merge

### 7.2 Performance Risks
**Risk**: Large documents causing timeouts or crashes

**Mitigation**:
- ✅ Document size limit (1MB) with clear error message
- ✅ Progress indicators during comparison
- ✅ Timeout handling with retry logic
- ✅ Coming Soon message for oversized documents

### 7.3 API Compatibility Risks
**Risk**: Backend API changes breaking add-in

**Mitigation**:
- ✅ New endpoint, existing endpoints unchanged
- ✅ API versioning if needed
- ✅ Graceful degradation if endpoint unavailable
- ✅ Clear error messages for API mismatches

---

## 8. Success Criteria

### 8.1 Functional Requirements
- ✅ Both comparison modes working correctly
- ✅ Track Changes detection working
- ✅ Standard contract selection working
- ✅ Full contract comparison working
- ✅ Clause-by-clause comparison working
- ✅ Results display matching web app format
- ✅ No regression in existing functionality

### 8.2 Non-Functional Requirements
- ✅ Response time: < 10 seconds for typical documents
- ✅ Error messages: Clear and actionable
- ✅ UI: Consistent with existing add-in styling
- ✅ Code quality: Follows existing patterns
- ✅ Documentation: Inline comments and README updates

### 8.3 User Experience
- ✅ Intuitive mode selection
- ✅ Clear indication when comparison modes are unavailable
- ✅ Progress feedback during long operations
- ✅ Results easy to understand and navigate
- ✅ Smooth transitions between tabs

---

## 9. Future Enhancements (Out of Scope)

1. **Clause Library Integration**: Insert missing clauses from library
2. **Background Processing**: Support for very large documents
3. **Multiple Document Comparison**: Compare current doc against multiple standards
4. **Export Results**: Save comparison results as PDF/Word
5. **Revision History**: Track comparison history within session
6. **AI Suggestions**: Automatic recommendations for improvements

---

## 10. Acceptance Checklist

Before marking implementation complete:

- [ ] Backend endpoint implemented and tested
- [ ] Frontend services implemented and tested
- [ ] Component logic implemented and tested
- [ ] UI template completed and styled
- [ ] Both comparison modes working end-to-end
- [ ] Full contract and clause modes both working
- [ ] Error handling tested and working
- [ ] Large document handling implemented
- [ ] No regressions in Compliance tab
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] User acceptance testing completed
- [ ] Code reviewed and approved
- [ ] Documentation updated

---

## 11. Open Questions for Review

1. **API Endpoint Location**: Create new router file or add to existing contracts router?
2. **Temporary Contract Storage**: Store temporarily in CosmosDB with TTL or purely in-memory?
3. **Document Size Limit**: Is 1MB appropriate, or should it be higher/lower?
4. **Clause Library Integration Timing**: Should we stub out the "Insert Clause" button now for future use?
5. **Session Tracking**: Should we track comparison sessions similar to compliance evaluations?
6. **Result Persistence**: Should comparison results be saved for later retrieval?

---

## End of Implementation Plan

**Estimated Total Effort**: 15-20 development days
**Complexity**: Medium-High
**Risk Level**: Low (minimal impact on existing functionality)
**Priority**: High
