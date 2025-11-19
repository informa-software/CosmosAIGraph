# Track Changes Integration Analysis for Word Add-in

## Executive Summary

This analysis covers Office.js capabilities for handling track changes, integration with existing compare-contracts functionality, and recommended implementation approach for the Word Add-in.

---

## 1. Office.js Track Changes Capabilities

### Available Features

Office.js provides the following track changes capabilities through the `Word.ChangeTrackingOptions` and `Word.TrackedChange` APIs:

#### Detection & Status
```typescript
// Check if track changes is enabled
const trackChanges = context.document.changeTrackingMode;
// Returns: 'Off' | 'TrackAll' | 'TrackMineOnly'

// Get track changes state
const isTracking = context.document.properties.trackRevisions;
```

#### Access to Tracked Changes
```typescript
// Get all tracked changes (revisions)
const trackedChanges = context.document.body.trackedChanges;
trackedChanges.load('items');
await context.sync();

// Each tracked change has:
- type: 'Inserted' | 'Deleted' | 'Moved' | 'Formatted'
- author: string
- date: Date
- text: string (the changed text)
- range: Word.Range (location in document)
```

#### Accept/Reject Changes
```typescript
// Accept a tracked change
trackedChange.accept();

// Reject a tracked change
trackedChange.reject();

// Accept all changes
trackedChanges.acceptAll();

// Reject all changes
trackedChanges.rejectAll();
```

#### Extract Original vs. Current Text
```typescript
// Get original text (without accepting changes)
const originalRange = trackedChange.getNext();
originalRange.load('text');

// Get current text (with changes applied)
const currentText = body.text;
```

---

## 2. Existing Compare-Contracts Functionality

### Backend API: `/api/compare-contracts`

**Endpoint**: `POST https://localhost:8000/api/compare-contracts`

**Request Structure**:
```typescript
{
  standardContractId: string;         // The baseline/original contract
  compareContractIds: string[];       // Contract(s) to compare against
  comparisonMode: 'clauses' | 'full'; // Compare specific clauses or full text
  selectedClauses?: string[] | 'all'; // Which clause types to compare
}
```

**Response Structure**:
```typescript
{
  success: boolean;
  standardContractId: string;
  compareContractIds: string[];
  comparisonMode: string;
  results: {
    comparisons: [
      {
        contract_id: string;
        overall_similarity_score: number;      // 0-100
        risk_level: 'low' | 'medium' | 'high';
        clause_analyses: ClauseAnalysis[];
        missing_clauses: string[];
        additional_clauses: string[];
        critical_findings: string[];
      }
    ]
  }
}
```

### Capabilities
1. **Full Document Comparison**: Compares entire contract texts
2. **Clause-by-Clause Comparison**: Focuses on specific clause types
3. **Risk Assessment**: Identifies high-risk differences
4. **Similarity Scoring**: Quantifies how similar contracts are
5. **AI-Powered Analysis**: Uses LLM to understand semantic differences

---

## 3. Integration Strategy

### Approach A: Track Changes as Comparison Source (Recommended)

**Workflow**:
1. Detect track changes enabled in Word document
2. Extract two versions:
   - **Original**: Text with all changes rejected
   - **Revised**: Text with all changes accepted
3. Upload both versions to backend as separate "contracts"
4. Use existing `/api/compare-contracts` endpoint
5. Display comparison results in task pane

**Advantages**:
- ✅ Leverages existing, tested compare functionality
- ✅ Provides AI-powered semantic analysis of changes
- ✅ Risk assessment for proposed changes
- ✅ Identifies critical differences
- ✅ No new backend development needed

**Challenges**:
- ⚠️ Need to create temporary contract IDs for comparison
- ⚠️ Must extract clean text versions from tracked changes
- ⚠️ May not preserve exact track changes metadata

### Approach B: Native Track Changes UI

**Workflow**:
1. Show list of tracked changes in task pane
2. Display author, date, type (insert/delete/format)
3. Provide accept/reject buttons per change
4. Optionally show compliance impact of each change

**Advantages**:
- ✅ Direct integration with Word's native features
- ✅ Preserves all track changes metadata
- ✅ Fine-grained control per change

**Challenges**:
- ❌ Doesn't leverage existing compare functionality
- ❌ Limited semantic understanding of changes
- ❌ More UI development needed

### Approach C: Hybrid (Best of Both)

**Workflow**:
1. Detect track changes enabled
2. Show overview of all changes (authors, dates, counts)
3. Provide two analysis options:
   - **Quick Review**: Native track changes list with accept/reject
   - **AI Analysis**: Compare original vs. revised using existing API
4. Display compliance impact for significant changes

**Advantages**:
- ✅ Flexibility for different use cases
- ✅ Leverages existing functionality where it adds value
- ✅ Preserves native Word features

---

## 4. Recommended Implementation: Approach C (Hybrid)

### Phase 1: Detection & Overview (Week 1)

**Files to Create**:
- `office-addin/src/app/services/track-changes.service.ts`
- `office-addin/src/app/models/track-changes.models.ts`

**Features**:
```typescript
// TrackChangesService
- isTrackChangesEnabled(): Promise<boolean>
- getTrackChangesSummary(): Promise<TrackChangesSummary>
- getTrackedChanges(): Promise<TrackedChangeInfo[]>
- extractOriginalText(): Promise<string>
- extractRevisedText(): Promise<string>
```

**UI Component**:
- Add track changes indicator to header
- Show summary: "12 changes by 3 authors"
- Provide mode selector: "Quick Review" vs "AI Analysis"

### Phase 2: Quick Review Mode (Week 1-2)

**Features**:
- List all tracked changes with:
  - Author name
  - Date/time
  - Change type (icon)
  - Text preview
- Accept/Reject buttons per change
- Filter by author, date, type
- Highlight change location in document on click

### Phase 3: AI Analysis Mode (Week 2)

**Features**:
- Extract original + revised versions
- Create temporary comparison request
- Call `/api/compare-contracts` with mode='full'
- Display:
  - Overall risk level
  - Similarity score
  - Critical findings
  - Section-by-section comparison
- Highlight high-risk changes

### Phase 4: Compliance Integration (Week 3)

**Features**:
- Run compliance check on revised version
- Compare compliance results: original vs. revised
- Highlight changes that affect compliance
- Risk scoring per change:
  - Green: No compliance impact
  - Yellow: Minor impact
  - Red: Violates compliance rule

---

## 5. Technical Implementation Details

### Service: TrackChangesService

```typescript
@Injectable({ providedIn: 'root' })
export class TrackChangesService {

  async isTrackChangesEnabled(): Promise<boolean> {
    return Word.run(async (context) => {
      const trackingMode = context.document.changeTrackingMode;
      await context.sync();
      return trackingMode !== Word.ChangeTrackingMode.off;
    });
  }

  async getTrackedChanges(): Promise<TrackedChangeInfo[]> {
    return Word.run(async (context) => {
      const trackedChanges = context.document.body.trackedChanges;
      trackedChanges.load('items');
      trackedChanges.items.forEach(change => {
        change.load('type, author, date, text');
      });
      await context.sync();

      return trackedChanges.items.map(change => ({
        id: change.id,
        type: change.type,
        author: change.author,
        date: change.date,
        text: change.text
      }));
    });
  }

  async extractOriginalText(): Promise<string> {
    return Word.run(async (context) => {
      // Get all tracked changes
      const trackedChanges = context.document.body.trackedChanges;

      // Temporarily reject all changes
      trackedChanges.rejectAll();
      await context.sync();

      // Get text
      const body = context.document.body;
      body.load('text');
      await context.sync();
      const originalText = body.text;

      // Restore changes (undo the reject)
      context.document.undo();
      await context.sync();

      return originalText;
    });
  }

  async extractRevisedText(): Promise<string> {
    return Word.run(async (context) => {
      // Get all tracked changes
      const trackedChanges = context.document.body.trackedChanges;

      // Temporarily accept all changes
      trackedChanges.acceptAll();
      await context.sync();

      // Get text
      const body = context.document.body;
      body.load('text');
      await context.sync();
      const revisedText = body.text;

      // Restore changes (undo the accept)
      context.document.undo();
      await context.sync();

      return revisedText;
    });
  }

  async compareVersions(): Promise<ContractComparisonResponse> {
    // Extract both versions
    const originalText = await this.extractOriginalText();
    const revisedText = await this.extractRevisedText();

    // Create temporary contract IDs
    const timestamp = Date.now();
    const originalId = `word_original_${timestamp}`;
    const revisedId = `word_revised_${timestamp}`;

    // Call compare API
    const request: ContractComparisonRequest = {
      standardContractId: originalId,
      compareContractIds: [revisedId],
      comparisonMode: 'full'
    };

    // Note: Would need to upload the text first or modify API to accept inline text
    return await this.contractService.compareContracts(request).toPromise();
  }
}
```

### Models: track-changes.models.ts

```typescript
export interface TrackedChangeInfo {
  id: string;
  type: 'Inserted' | 'Deleted' | 'Moved' | 'Formatted';
  author: string;
  date: Date;
  text: string;
  range?: any; // Word.Range
}

export interface TrackChangesSummary {
  isEnabled: boolean;
  totalChanges: number;
  byAuthor: Map<string, number>;
  byType: Map<string, number>;
  oldestChange: Date;
  newestChange: Date;
}

export interface ComparisonMode {
  mode: 'quick' | 'ai';
  showCompliance: boolean;
}
```

### UI Component Updates

Add to `word-addin.component.ts`:
```typescript
// State
trackChangesEnabled: boolean = false;
trackChangesSummary: TrackChangesSummary | null = null;
comparisonMode: 'quick' | 'ai' = 'quick';

// Methods
async checkTrackChanges(): Promise<void> {
  this.trackChangesEnabled = await this.trackChangesService.isTrackChangesEnabled();
  if (this.trackChangesEnabled) {
    this.trackChangesSummary = await this.trackChangesService.getTrackChangesSummary();
  }
}

async analyzeChanges(): Promise<void> {
  if (this.comparisonMode === 'ai') {
    const comparison = await this.trackChangesService.compareVersions();
    // Display comparison results
  } else {
    const changes = await this.trackChangesService.getTrackedChanges();
    // Display quick review list
  }
}
```

---

## 6. API Enhancement Needed

### Option 1: Modify Existing Endpoint (Preferred)

Update `/api/compare-contracts` to accept inline text:

```python
@app.post("/api/compare-contracts")
async def compare_contracts(request: Request):
    body = await request.json()

    # NEW: Accept inline text instead of contract IDs
    standard_text = body.get("standardText")
    compare_texts = body.get("compareTexts")

    if standard_text and compare_texts:
        # Use provided text directly instead of fetching from DB
        standard_data = {
            "contract_id": "inline_standard",
            "mode": "full",
            "content": standard_text
        }
        comparison_data = {
            f"inline_{i}": {
                "contract_id": f"inline_{i}",
                "mode": "full",
                "content": text
            }
            for i, text in enumerate(compare_texts)
        }
    else:
        # Existing logic: fetch from DB by ID
        ...
```

### Option 2: New Endpoint

Create `/api/compare-text` specifically for inline comparison:

```python
@app.post("/api/compare-text")
async def compare_text(request: Request):
    """
    Compare text content directly without storing in DB.
    For Word Add-in track changes comparison.
    """
    body = await request.json()
    original_text = body.get("originalText")
    revised_text = body.get("revisedText")

    # Same comparison logic as compare-contracts
    # but works with provided text
```

---

## 7. Questions Needing Clarification

### Technical Questions

1. **Storage**: Should we temporarily store original/revised versions in CosmosDB for comparison, or pass as inline text?
   - **Recommendation**: Inline text (Option 2 above) to avoid DB clutter

2. **Compliance**: Should compliance evaluation run on both versions or just revised?
   - **Recommendation**: Both - show delta in compliance status

3. **Change Granularity**: Should we highlight individual changes in compliance results?
   - **Recommendation**: Yes - map each change to affected rules

### UX Questions

1. **Default Mode**: Should Quick Review or AI Analysis be default?
   - **Recommendation**: Quick Review for <10 changes, AI Analysis for more

2. **Auto-detect**: Should we automatically show track changes UI when detected?
   - **Recommendation**: Yes - show notification with option to analyze

3. **Workflow**: Accept changes from add-in or require native Word features?
   - **Recommendation**: Both - provide convenience buttons but link to native UI

---

## 8. Implementation Roadmap

### Sprint 1 (Week 1)
- [ ] Create TrackChangesService with detection & extraction
- [ ] Add track changes indicator to UI
- [ ] Implement Quick Review mode (list changes)
- [ ] Add accept/reject functionality

### Sprint 2 (Week 2)
- [ ] Implement extractOriginalText() and extractRevisedText()
- [ ] Create `/api/compare-text` endpoint
- [ ] Integrate with AI Analysis mode
- [ ] Display comparison results

### Sprint 3 (Week 3)
- [ ] Add compliance integration
- [ ] Show compliance delta (original vs revised)
- [ ] Highlight compliance-impacting changes
- [ ] Risk scoring per change

### Sprint 4 (Week 4)
- [ ] Polish UI/UX
- [ ] Add filtering and search
- [ ] Performance optimization
- [ ] Documentation and testing

---

## 9. Limitations & Considerations

### Office.js Limitations
1. **API Availability**: Track changes API requires Word 2016+ and specific API sets
2. **Permissions**: May need additional manifest permissions
3. **Performance**: Large documents with many changes may be slow
4. **Formatting**: Some formatting changes may not be captured well as text

### Backend Limitations
1. **Context**: Inline text comparison loses document metadata
2. **Clause Detection**: May be less accurate without contract structure
3. **Token Limits**: Very large documents may exceed LLM token limits

### Recommended Mitigations
1. Add API version detection and graceful degradation
2. Implement chunking for large documents
3. Cache comparison results for repeated analyses
4. Provide clear error messages for unsupported scenarios

---

## 10. Estimated Effort

| Component | Effort | Priority |
|-----------|--------|----------|
| Detection & Basic UI | 2 days | P0 |
| Quick Review Mode | 3 days | P0 |
| Text Extraction | 2 days | P0 |
| Backend API Enhancement | 2 days | P1 |
| AI Analysis Integration | 3 days | P1 |
| Compliance Integration | 4 days | P2 |
| Polish & Testing | 4 days | P2 |
| **Total** | **20 days** | |

**Timeline**: 4 weeks with 1 developer

---

## Conclusion

**Recommendation**: Implement Approach C (Hybrid) using the phased roadmap above.

**Key Benefits**:
- ✅ Leverages existing compare-contracts functionality
- ✅ Provides both quick review and deep analysis options
- ✅ Integrates compliance evaluation with change tracking
- ✅ Minimal backend changes needed (just add inline text support)
- ✅ Follows Microsoft Office Add-in best practices

**Next Steps**:
1. Confirm approach with stakeholders
2. Clarify technical and UX questions above
3. Begin Sprint 1 implementation
