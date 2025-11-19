# Track Changes Text Extraction Debugging Guide

## Overview

This document describes the track changes text extraction system and the comprehensive logging added to debug issues where original text (deleted values) may not be properly captured.

## System Architecture

### Text Extraction Flow

1. **Word Add-in Component** (`office-addin/src/app/word-addin/word-addin.component.ts`)
   - Lines 419-439: Orchestrates text extraction and comparison
   - Calls `TrackChangesService` to extract original and revised text
   - Sends both texts to the backend comparison API

2. **Track Changes Service** (`office-addin/src/app/services/track-changes.service.ts`)
   - `extractOriginalText()` (lines 69-114): Extracts text with deletions visible, insertions hidden
   - `extractRevisedText()` (lines 120-165): Extracts text with deletions hidden, insertions visible
   - `extractTextFromOoxml()` (lines 172-268): Core OOXML parsing logic

3. **Backend API** (`web_app/web_app.py`)
   - Lines 2806-2838: Receives original and revised text
   - Creates data structures for comparison
   - Logs received text for verification

## How OOXML Parsing Works

### OOXML Structure

Word documents store tracked changes in OOXML format:
- `<w:del>` elements contain deleted text
- `<w:ins>` elements contain inserted text
- `<w:t>` elements contain the actual text content

### Extraction Logic

**For Original Text** (how the document looked before changes):
- ✅ **Include**: Normal text nodes
- ✅ **Include**: Text inside `<w:del>` (deleted text)
- ❌ **Exclude**: Text inside `<w:ins>` (inserted text)

**For Revised Text** (how the document will look after accepting changes):
- ✅ **Include**: Normal text nodes
- ❌ **Exclude**: Text inside `<w:del>` (deleted text)
- ✅ **Include**: Text inside `<w:ins>` (inserted text)

## Potential Issues

### 1. Tag Name Detection Issues

The current code checks for:
```typescript
if (tagName === 'del') { isDeleted = true; }
if (tagName === 'ins') { isInserted = true; }
```

**Potential Problems**:
- OOXML uses namespaced tags like `w:del`, not just `del`
- The code uses `localName` which should strip the namespace, but this needs verification
- Different Word versions might use different OOXML structures

### 2. Fallback Behavior

If OOXML parsing returns empty text, the code falls back to `body.text`:
```typescript
if (!originalText || originalText.trim().length === 0) {
  body.load('text');
  await context.sync();
  originalText = body.text;  // This may not include deleted text!
}
```

**Problem**: The fallback `body.text` likely shows the current state of the document, which may not include deleted text.

### 3. Complex OOXML Structures

There might be other OOXML elements that represent changes:
- Move operations (`<w:moveFrom>`, `<w:moveTo>`)
- Format-only changes
- Nested changes (a deletion within an insertion)

## New Logging Added

### Frontend Logging (track-changes.service.ts)

#### High-Level Extraction Logging
```
=== EXTRACTING ORIGINAL TEXT ===
OOXML length: 12345
OOXML extraction result - length: 5678
OOXML extraction result - preview: [first 200 chars]
Final original text length: 5678
=== END EXTRACTING ORIGINAL TEXT ===
```

#### Detailed OOXML Parsing Logging
```
--- extractTextFromOoxml: version=original ---
Found 150 text nodes (w:t elements)

  Node 0: "This is some text"
    - Deleted: false, Inserted: false, Normal: true
    - Include in original: true
    - Parent chain: r > p > body > document

  Node 5: "deleted value"
    - Deleted: true, Inserted: false, Normal: false
    - Include in original: true
    - Parent chain: del > r > p > body

  Node 7: "new value"
    - Deleted: false, Inserted: true, Normal: false
    - Include in original: false
    - Parent chain: ins > r > p > body

--- OOXML Extraction Statistics ---
  Total text nodes: 150
  Deleted text nodes: 12
  Inserted text nodes: 8
  Normal text nodes: 130
  Included in original: 142
  Excluded from original: 8
  Final text length: 5678
--- End Statistics ---
```

#### Component-Level Logging
```
✓ Original text extracted - Length: 5678 characters
Original text preview (first 500 chars):
[preview text]

✓ Revised text extracted - Length: 5890 characters
Revised text preview (first 500 chars):
[preview text]

📊 Text length difference: +212 characters

Sending text to comparison API...
  - Original text: 5678 chars
  - Revised text: 5890 chars
```

### Backend Logging (web_app.py)

```
Contract comparison using inline text (track changes mode)
  - Original text length: 5678 characters
  - Revised text length: 5890 characters
  - Original text preview (first 500 chars): [preview]
  - Revised text preview (first 500 chars): [preview]
  - Text length difference: +212 characters
```

## How to Use This Logging

### 1. Reproduce the Issue

1. Open a Word document with track changes enabled
2. Update a value (delete old value, insert new value)
3. Open the Word add-in and click "Analyze Changes"
4. Open the browser developer console (F12)

### 2. Analyze the Logs

#### Check if OOXML is being retrieved:
- Look for `OOXML length: X` - should be > 0
- If 0 or very small, OOXML retrieval failed

#### Check text node counts:
```
Found X text nodes (w:t elements)
```
- If 0, the OOXML namespace or parsing failed
- Expected: dozens to hundreds depending on document size

#### Check deleted text node detection:
```
  Node X: "deleted value"
    - Deleted: true, Inserted: false, Normal: false
```
- Verify that deleted text is being detected (`Deleted: true`)
- Check the parent chain to see the OOXML structure

#### Check inclusion logic:
```
    - Include in original: true
```
- For original text: deleted nodes should have `Include in original: true`
- For original text: inserted nodes should have `Include in original: false`

#### Check statistics:
```
  Deleted text nodes: X
  Included in original: Y
```
- If `Deleted text nodes: 0` but you made deletions, the tag detection is failing
- Compare counts between original and revised extraction

#### Check for fallback usage:
```
⚠️ OOXML extraction returned empty text, falling back to body.text
```
- If you see this, OOXML parsing completely failed
- The fallback text likely won't include deleted content

### 3. Common Scenarios

#### Scenario 1: Deleted text not detected
**Symptoms**:
- `Deleted text nodes: 0` even though document has deletions
- Original and revised text are identical

**Diagnosis**:
- Check the parent chain for deleted text nodes
- May show `delText` or other tag names instead of `del`

**Solution**: Update tag detection logic to handle different tag names

#### Scenario 2: Empty OOXML extraction
**Symptoms**:
- `Found 0 text nodes`
- Falls back to `body.text`

**Diagnosis**:
- OOXML namespace issue
- Document structure not as expected

**Solution**: Log the raw OOXML XML and inspect structure

#### Scenario 3: Deleted text detected but not included
**Symptoms**:
- `Deleted text nodes: X` where X > 0
- But `Included in original:` shows counts that don't add up

**Diagnosis**:
- Logic error in inclusion check

**Solution**: Verify the logic in lines 232-239 of track-changes.service.ts

## Recommendations for Fixes

### 1. Improve Tag Detection

Add support for alternative tag names and structures:
```typescript
const deletionTags = ['del', 'delText', 'deleteText', 'moveFrom'];
const insertionTags = ['ins', 'insText', 'insertText', 'moveTo'];

if (deletionTags.includes(tagName)) {
  isDeleted = true;
  break;
}
```

### 2. Add OOXML Raw Logging (Optional Debug Mode)

For deep debugging, add option to log raw OOXML:
```typescript
// Only enable when DEBUG_OOXML environment variable is set
if (DEBUG_MODE) {
  console.log('Raw OOXML (first 10000 chars):', ooxml.value.substring(0, 10000));
}
```

### 3. Handle Edge Cases

- Nested changes (deletion within insertion)
- Move operations (text moved to different location)
- Format-only changes (shouldn't affect text extraction)

### 4. Better Fallback Strategy

Instead of falling back to `body.text` (which may not include deletions), consider:
- Trying alternate OOXML parsing methods
- Using Word API's revision tracking methods
- Showing a clear error to the user

## Testing the Logging

1. Create a test document with known changes:
   - Line 1: Normal text (no changes)
   - Line 2: "Old value" (deleted) → "New value" (inserted)
   - Line 3: "Additional text" (inserted only)
   - Line 4: "Removed text" (deleted only)

2. Run the Word add-in and analyze changes

3. Verify the logs show:
   - All text nodes found
   - Deletions correctly identified
   - Insertions correctly identified
   - Correct inclusion/exclusion for original vs revised

4. Compare the extracted text previews with expected content

## Files Modified

1. `office-addin/src/app/services/track-changes.service.ts`
   - Added logging to `extractOriginalText()` (lines 81-111)
   - Added logging to `extractRevisedText()` (lines 132-162)
   - Added comprehensive logging to `extractTextFromOoxml()` (lines 175-265)

2. `office-addin/src/app/word-addin/word-addin.component.ts`
   - Added logging around text extraction (lines 416-439)

3. `web_app/web_app.py`
   - Added logging to comparison endpoint (lines 2808-2816)

## Next Steps

1. **Test the logging** with a document that exhibits the issue
2. **Analyze the console output** to identify the root cause
3. **Implement fixes** based on findings (likely tag detection or OOXML structure handling)
4. **Consider adding unit tests** for OOXML parsing with various tracked change scenarios
