# Troubleshooting: Missing Save & PDF Buttons

## Expected Button Location

After performing a comparison, you should see buttons in this location:

```
📊 Contract Comparison Results
┌─────────────────────────────────────────────┐
│ [Standard: Contract Name] [Mode: clauses]  │
│ [Compared: 2 contracts]                     │
│                                             │
│ [📥 Export Results] [📄 Save & Generate PDF] [✉️ Email PDF] │
└─────────────────────────────────────────────┘
```

The buttons should appear **directly below** the badge row, inside the comparison header section.

## Troubleshooting Steps

### Step 1: Verify Comparison Success

1. Open Browser Developer Console (F12)
2. Go to **Console** tab
3. After running comparison, check for:
   - ✅ Success message: `Comparison Complete: Contract comparison has been completed successfully.`
   - ❌ Error message: `Comparison Failed: ...`

If you see an error, the comparison failed and buttons won't appear.

### Step 2: Check Component State

In the Console tab, run this command:
```javascript
// Get Angular component instance
let component = ng.getComponent(document.querySelector('app-contract-workbench'));

// Check state
console.log('comparisonResults:', component.comparisonResults);
console.log('comparisonResults.success:', component.comparisonResults?.success);
console.log('isSavingResult:', component.isSavingResult);
console.log('isGeneratingPDF:', component.isGeneratingPDF);
```

**Expected Output**:
```
comparisonResults: {success: true, standardContractId: "...", compareContractIds: [...], ...}
comparisonResults.success: true
isSavingResult: false
isGeneratingPDF: false
```

If `comparisonResults.success` is **false** or **undefined**, the buttons won't show.

### Step 3: Check HTML Element

In the Console tab, run:
```javascript
// Check if button element exists in DOM
let buttonGroup = document.querySelector('.comparison-header .button-group');
console.log('Button group element:', buttonGroup);
console.log('Buttons:', buttonGroup?.querySelectorAll('button'));
```

**Expected Output**:
```
Button group element: <div class="button-group">...</div>
Buttons: NodeList(3) [button.btn, button.btn, button.btn]
```

If this returns `null`, the buttons are not in the DOM (conditional rendering issue).

### Step 4: Check CSS Visibility

In the Console tab, run:
```javascript
let buttonGroup = document.querySelector('.comparison-header .button-group');
if (buttonGroup) {
  let styles = window.getComputedStyle(buttonGroup);
  console.log('display:', styles.display);
  console.log('visibility:', styles.visibility);
  console.log('opacity:', styles.opacity);
}
```

**Expected Output**:
```
display: flex
visibility: visible
opacity: 1
```

If `display: none` or `visibility: hidden`, there's a CSS issue.

### Step 5: Check for JavaScript Errors

1. In Console tab, look for any red error messages
2. Common issues:
   - `Cannot read property 'success' of undefined`
   - `saveAndGenerateComparisonPDF is not a function`
   - TypeScript compilation errors

## Common Issues and Fixes

### Issue 1: Comparison Failed Silently
**Symptom**: No buttons, no error message
**Check**: Console for errors, Network tab for failed requests
**Fix**: Check backend is running, check contract IDs are valid

### Issue 2: Angular Not Updated
**Symptom**: Old code still running
**Fix**:
1. Stop Angular dev server (Ctrl+C)
2. Clear browser cache (Ctrl+Shift+Delete)
3. Restart: `npm start`
4. Hard refresh page (Ctrl+F5)

### Issue 3: Service Not Injected
**Symptom**: Error: `analysisResultsService is undefined`
**Fix**: Verify in `contract-workbench.ts` line 195:
```typescript
private analysisResultsService: AnalysisResultsService,
```

### Issue 4: Wrong Workbench Mode
**Symptom**: Looking at wrong tab
**Fix**: Ensure you're on the "Compare Contracts" tab (not "Query Contracts")

### Issue 5: CSS Not Compiled
**Symptom**: Buttons exist in DOM but not styled/visible
**Fix**:
1. Check `contract-workbench.scss` was saved
2. Restart Angular dev server
3. Check browser console for SCSS compilation errors

## Manual Verification

### Verify TypeScript Method Exists

Check `contract-workbench.ts` contains (around line 1155):
```typescript
saveAndGenerateComparisonPDF(): void {
  if (!this.comparisonResults) {
    this.toastService.error('No Results', 'No comparison results to save.');
    return;
  }
  // ... rest of method
}
```

### Verify Service Import

Check `contract-workbench.ts` line 22-23:
```typescript
import { AnalysisResultsService } from '../shared/services/analysis-results.service';
import { SaveComparisonRequest, SaveQueryRequest, ContractQueried } from '../shared/models/analysis-results.models';
```

### Verify Service Injection

Check `contract-workbench.ts` constructor (around line 195):
```typescript
constructor(
  private contractService: ContractService,
  private toastService: ToastService,
  private analysisResultsService: AnalysisResultsService,
  private sanitizer: DomSanitizer
) { }
```

## Quick Test

If you want to test if the button can be manually triggered:

1. Open Console
2. Get component: `let c = ng.getComponent(document.querySelector('app-contract-workbench'))`
3. Check method exists: `console.log(typeof c.saveAndGenerateComparisonPDF)`
   - Should output: `function`
4. Try calling it manually: `c.saveAndGenerateComparisonPDF()`
   - Should show toast or error

## If Still Not Working

Please provide the following information:

1. **Console Output** from Step 2 above (comparisonResults state)
2. **Any Error Messages** in red in the Console
3. **Screenshot** of the comparison results page
4. **Network Tab** - any failed requests to backend?

This will help diagnose the specific issue.
