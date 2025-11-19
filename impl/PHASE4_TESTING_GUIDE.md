# Phase 4 Testing Guide: Angular Frontend Integration

## Overview

Phase 4 implements the Angular frontend integration for saving analysis results and generating PDFs. This guide covers testing the complete user workflow from performing analysis to downloading PDF reports.

## Prerequisites

### Backend Services Running
1. **Web Application** (Python/FastAPI):
   ```powershell
   cd web_app
   .\web_app.ps1
   ```
   - Should be running on https://localhost:8000
   - Verify at: https://localhost:8000/

2. **CosmosDB Containers**:
   - `analysis_results` container must exist
   - Verify setup with: `python setup_analysis_results_container.py`

### Frontend Application Running
3. **Query Builder** (Angular):
   ```powershell
   cd query-builder
   npm start
   ```
   - Should be running on https://localhost:4200
   - Verify at: https://localhost:4200/contract-workbench

### Test Data
4. **Contracts Loaded**:
   - At least 2-3 contracts loaded in CosmosDB
   - Use: `python main_contracts.py load_contracts caig contracts data/contracts 999999`

## Test Scenarios

### Test 1: Save and Generate PDF from Comparison

**Objective**: Verify comparison results can be saved and PDF generated automatically.

**Steps**:
1. Navigate to https://localhost:4200/contract-workbench
2. Select **Standard Contract** from dropdown
3. Select 1-2 contracts to compare
4. Choose comparison mode: **Full Contract** or **Selected Clauses**
5. Click **Compare Contracts** button
6. Wait for comparison results to display
7. Locate the button group in comparison results header:
   - Should see three buttons: "📥 Export Results", "📄 Save & Generate PDF", "✉️ Email PDF"
8. Click **"📄 Save & Generate PDF"** button

**Expected Results**:
- Button text changes to "💾 Saving..." immediately
- Toast notification: "Saved: Comparison results saved successfully"
- Button text changes to "📄 Generating PDF..."
- PDF file downloads automatically to your Downloads folder
- Filename format: `report_{result_id}.pdf`
- Toast notification: "PDF Generated: Your PDF report has been downloaded"
- Button returns to original state

**Verify PDF Content**:
- Open downloaded PDF file
- Should contain:
  - Report title: "Contract Comparison Report"
  - Metadata section with generation timestamp
  - Standard Contract section
  - Compared Contracts section
  - Comparison Mode
  - Comparison Results
  - Professional styling with tables and formatting

**Backend Verification**:
```powershell
# Check CosmosDB for saved result
# Use Azure Portal or Cosmos DB Explorer
# Container: analysis_results
# Look for document with result_type: "comparison"
```

### Test 2: Save and Generate PDF from Query

**Objective**: Verify query results can be saved and PDF generated automatically.

**Steps**:
1. Navigate to https://localhost:4200/contract-workbench
2. Scroll to **Query Contracts** section
3. Select 1-3 contracts for querying
4. Enter a natural language question, e.g.:
   - "What are the payment terms?"
   - "Who is the contractor?"
   - "What are the termination clauses?"
5. Click **Ask Question** button
6. Wait for answer to stream and complete
7. Locate the button group below the answer:
   - Should see two buttons: "📄 Save & Generate PDF", "✉️ Email PDF"
8. Click **"📄 Save & Generate PDF"** button

**Expected Results**:
- Button text changes to "💾 Saving..." immediately
- Toast notification: "Saved: Query results saved successfully"
- Button text changes to "📄 Generating PDF..."
- PDF file downloads automatically to your Downloads folder
- Filename format: `report_{result_id}.pdf`
- Toast notification: "PDF Generated: Your PDF report has been downloaded"
- Button returns to original state

**Verify PDF Content**:
- Open downloaded PDF file
- Should contain:
  - Report title: "Query Report"
  - Metadata section with generation timestamp
  - Query Text section with your question
  - Contracts Analyzed section (list of contracts)
  - Answer Summary section with the LLM response
  - Professional styling with tables and formatting

### Test 3: Email Button (Disabled State)

**Objective**: Verify email functionality is properly disabled with user messaging.

**Steps**:
1. Complete either Test 1 or Test 2 to display results
2. Locate the **"✉️ Email PDF"** button

**Expected Results**:
- Button is visually disabled (grayed out)
- Hovering over button shows tooltip: "Email functionality coming soon"
- Clicking button does nothing (no error, no action)

### Test 4: Error Handling - No Results

**Objective**: Verify proper error handling when attempting to save without results.

**Steps**:
1. Navigate to https://localhost:4200/contract-workbench
2. Without performing any comparison or query, try to trigger save
   - (Note: buttons won't be visible without results, so this tests the code path)

**Expected Results**:
- Toast notification: "No Results: No comparison/query results to save"
- No backend calls made

### Test 5: Button States During Operations

**Objective**: Verify button states prevent duplicate operations.

**Steps**:
1. Complete Test 1 or Test 2 to display results
2. Click **"📄 Save & Generate PDF"** button
3. While "Saving..." or "Generating PDF..." is displayed, try to click the button again

**Expected Results**:
- Button is disabled during saving phase
- Button remains disabled during PDF generation phase
- Cannot trigger duplicate save/PDF operations
- Only one PDF downloads at the end

### Test 6: Multiple Result Saves

**Objective**: Verify multiple results can be saved and generate distinct PDFs.

**Steps**:
1. Perform a comparison (Test 1)
2. Save and generate PDF - note the result_id from filename
3. Change the comparison (different contracts or mode)
4. Perform another comparison
5. Save and generate PDF - note the new result_id

**Expected Results**:
- Two different PDF files downloaded
- Different filenames (different result_ids)
- Both PDFs exist in Downloads folder
- Each PDF contains correct data for its respective analysis

**Backend Verification**:
```powershell
# Check CosmosDB for both saved results
# Should see two documents with different result_ids
```

### Test 7: Large Result Sets

**Objective**: Verify PDF generation works with large comparison results.

**Steps**:
1. Select a standard contract
2. Select 5+ contracts to compare (maximum available)
3. Use "Full Contract" mode for comprehensive results
4. Click **Compare Contracts**
5. Wait for large result set to display
6. Click **"📄 Save & Generate PDF"**

**Expected Results**:
- Saving completes successfully (may take a few seconds)
- PDF generation completes successfully (may take 5-10 seconds)
- PDF downloads successfully
- PDF contains all comparison data (may be multi-page)
- No timeout errors or truncation

### Test 8: Special Characters in Queries

**Objective**: Verify PDF generation handles special characters correctly.

**Steps**:
1. Enter a query with special characters:
   - "What are the "termination" clauses & 'liability' terms?"
2. Complete query and get results
3. Click **"📄 Save & Generate PDF"**

**Expected Results**:
- PDF generates successfully
- Special characters render correctly in PDF (quotes, ampersands, apostrophes)
- No encoding errors or garbled text

## Error Scenarios to Test

### Test E1: Backend Unavailable

**Setup**: Stop the web_app service

**Steps**:
1. Perform a comparison or query
2. Click **"📄 Save & Generate PDF"**

**Expected Results**:
- Toast notification: "Save Failed: Failed to save comparison/query results"
- Button returns to normal state
- No PDF download attempted
- User can retry after backend is restored

### Test E2: CosmosDB Connection Issues

**Setup**: Configure invalid CosmosDB connection string

**Steps**:
1. Perform a comparison or query
2. Click **"📄 Save & Generate PDF"**

**Expected Results**:
- Toast notification with appropriate error message
- Button returns to normal state
- Error logged to browser console

### Test E3: PDF Generation Failure

**Setup**: This is harder to simulate, but can be tested by:
- Manually calling the PDF endpoint with invalid result_id
- Or modifying backend to simulate PDF generation error

**Expected Results**:
- Toast notification: "PDF Generation Failed: Failed to generate PDF. Please try again."
- Button returns to normal state
- User can retry the operation

## Browser Console Verification

Throughout testing, monitor the browser console (F12) for:

**Success Scenario Logs**:
```
Comparison/Query results saved successfully
PDF generated and downloaded
```

**Error Scenario Logs**:
```
Error saving comparison: [error details]
Error generating PDF: [error details]
```

## Performance Benchmarks

Expected operation times:

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Save comparison | < 2 seconds | Depends on result size |
| Save query | < 2 seconds | Depends on result size |
| Generate PDF (small) | 2-5 seconds | < 5 pages |
| Generate PDF (large) | 5-10 seconds | 10+ pages |
| Total user wait | < 12 seconds | Save + PDF combined |

## Backend API Testing (Optional)

You can test the backend endpoints directly using curl or Postman:

### Test Save Comparison Endpoint
```bash
curl -X POST "https://localhost:8000/api/analysis-results/comparison" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@user.com",
    "standard_contract_id": "contract_001",
    "compare_contract_ids": ["contract_002", "contract_003"],
    "comparison_mode": "full",
    "results": {"test": "data"},
    "metadata": {
      "title": "Test Comparison",
      "description": "Test"
    }
  }'
```

**Expected Response**:
```json
{
  "result_id": "result_abc123xyz...",
  "message": "Comparison result saved successfully"
}
```

### Test Generate PDF Endpoint
```bash
curl -X GET "https://localhost:8000/api/analysis-results/results/{result_id}/pdf?user_id=test@user.com" \
  --output test_report.pdf
```

**Expected Response**:
- HTTP 200 status
- Content-Type: application/pdf
- Binary PDF file downloaded as test_report.pdf

### Test Save Query Endpoint
```bash
curl -X POST "https://localhost:8000/api/analysis-results/query" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@user.com",
    "query_text": "What are the payment terms?",
    "query_type": "natural_language",
    "contracts_queried": [
      {
        "contract_id": "contract_001",
        "filename": "contract_001.json",
        "contract_title": "Test Contract"
      }
    ],
    "results": {"answer_summary": "Test answer"},
    "metadata": {
      "title": "Test Query",
      "description": "Test"
    }
  }'
```

**Expected Response**:
```json
{
  "result_id": "result_def456uvw...",
  "message": "Query result saved successfully"
}
```

## Known Limitations

1. **User Authentication**: Currently using hardcoded `'default@user.com'`
   - TODO: Integrate with actual authentication system
   - All results stored under same user ID

2. **Email Functionality**: Disabled (Phase 3 deferred)
   - Button shown but disabled
   - Will be implemented in future phase

3. **PDF Styling**: Basic professional styling
   - TODO: Enhanced styling in future development session
   - Current styling is functional but minimal

4. **Results History**: Not implemented in Phase 4
   - Users can access saved results via CosmosDB directly
   - Future phase may add UI for browsing history

## Troubleshooting

### PDF Not Downloading
**Symptom**: "Save & Generate PDF" completes but no file downloads

**Checks**:
1. Check browser's download settings - may be blocking downloads
2. Check browser console for errors
3. Check browser's Downloads page (Ctrl+J in Chrome)
4. Verify PDF was generated on backend (check logs)

### PDF Renders Incorrectly
**Symptom**: PDF downloads but content is garbled or missing

**Checks**:
1. Verify xhtml2pdf is installed: `pip list | grep xhtml2pdf`
2. Check backend logs for PDF generation errors
3. Verify CSS is loading correctly (check styles.css exists)
4. Try with smaller result set to isolate issue

### Save Fails with Validation Error
**Symptom**: Toast shows "Save Failed" with validation error

**Checks**:
1. Check browser console for full error details
2. Verify backend models match frontend models
3. Check that all required fields are being sent
4. Verify user_id format is correct

### Slow PDF Generation
**Symptom**: "Generating PDF..." takes > 15 seconds

**Checks**:
1. Check size of results being processed
2. Monitor backend CPU/memory usage
3. Check CosmosDB latency
4. Consider result size optimization

## Success Criteria

Phase 4 is considered successfully tested when:

- ✅ Can save comparison results and download PDF (Test 1)
- ✅ Can save query results and download PDF (Test 2)
- ✅ Email button is disabled with appropriate messaging (Test 3)
- ✅ Button states prevent duplicate operations (Test 5)
- ✅ Multiple results can be saved independently (Test 6)
- ✅ Large result sets generate PDFs successfully (Test 7)
- ✅ Error scenarios show appropriate user feedback (Tests E1-E3)
- ✅ Performance is within acceptable bounds (< 12 seconds total)

## Next Steps After Testing

After Phase 4 testing is complete:

1. **Review PDF Styling**: Schedule session to enhance PDF appearance
2. **Implement User Authentication**: Replace hardcoded user ID
3. **Implement Phase 3**: Azure Communication Services email functionality
4. **Add Results History UI**: Allow users to browse and re-download previous results
5. **Performance Optimization**: If needed based on testing results
