# Phase 5: Angular UI Testing Guide - Rules Management

## Overview

This document provides testing instructions for the Compliance Rules Management UI built in Phase 5.

## Prerequisites

1. **Backend Running**: Python web_app must be running on port 8000
   ```powershell
   cd web_app
   .\web_app.ps1
   ```

2. **Sample Rules Loaded**: Use the sample rules from `sample_compliance_rules.md` to create test data

3. **Angular App Running**: The query-builder app should be running on port 4200
   ```bash
   cd query-builder
   npm start
   ```

## Phase 5 Components Completed

### ✅ 5.1 TypeScript Models/Interfaces
**File**: `query-builder/src/app/compliance/models/compliance.models.ts`

**Features**:
- Complete TypeScript interfaces for all compliance entities
- 15 predefined categories with descriptions
- Helper functions: `getSeverityColor()`, `formatDate()`
- Severity options with color coding
- Type safety for all compliance operations

### ✅ 5.2 ComplianceService
**File**: `query-builder/src/app/compliance/services/compliance.service.ts`

**Features**:
- Complete REST API integration (22 methods)
- Observable-based HTTP calls with error handling
- Job polling for async operations
- Category management
- Dashboard summary retrieval

### ✅ 5.3 ComplianceRulesComponent (List View)
**Files**:
- `query-builder/src/app/compliance/compliance-rules/compliance-rules.component.ts`
- `query-builder/src/app/compliance/compliance-rules/compliance-rules.component.html`
- `query-builder/src/app/compliance/compliance-rules/compliance-rules.component.scss`

**Features**:
- Rules list with pagination (10/20/50/100 per page)
- Filtering by active status, category, and severity
- Full-text search across name, description, and category
- Sortable columns (name, severity, category, updated date)
- Bulk selection and deletion
- CSV export functionality
- Responsive design with mobile support
- Status indicators and severity badges
- Navigation to dashboard, create, edit, and view modes

### ✅ 5.4 ComplianceRuleEditorComponent (Create/Edit)
**Files**:
- `query-builder/src/app/compliance/compliance-rule-editor/compliance-rule-editor.component.ts`
- `query-builder/src/app/compliance/compliance-rule-editor/compliance-rule-editor.component.html`
- `query-builder/src/app/compliance/compliance-rule-editor/compliance-rule-editor.component.scss`

**Features**:
- Create and edit modes (route-driven)
- Form validation (name: 3-200 chars, description: 10-1000 chars)
- Character count tracking
- Severity selection with preview
- Category selection with inline category creation
- Active/inactive status toggle
- Unsaved changes detection with confirmation
- Only sends changed fields when updating
- Metadata display in edit mode (ID, dates, creator)
- Responsive form layout

### ✅ 5.5 Routing Configuration
**Files**:
- `query-builder/src/app/app.routes.ts` (routes defined)
- `query-builder/src/app/app.ts` (navigation link added)

**Routes**:
- `/compliance/rules` - Rules list view
- `/compliance/rules/new` - Create new rule
- `/compliance/rules/edit/:id` - Edit existing rule
- `/compliance/rules/view/:id` - View rule details

**Navigation**:
- "Compliance Rules" link added to main navbar
- Active route highlighting

## Testing Scenarios

### Test 1: Navigate to Compliance Rules
**Steps**:
1. Open browser to `http://localhost:4200`
2. Click "Compliance Rules" in navbar
3. Verify navigation to `/compliance/rules`

**Expected Results**:
- Rules list page loads
- "Compliance Rules" link is highlighted in navbar
- Page shows header with "New Rule" and "Dashboard" buttons
- Filters section displays (active only, category, severity, search)
- Stats bar shows total rules and filtered count

### Test 2: View Rules List
**Steps**:
1. Navigate to `/compliance/rules`
2. Observe the rules table

**Expected Results**:
- Rules displayed in table format
- Columns: checkbox, name, description, severity, category, status, updated date, actions
- Severity badges color-coded (critical=red, high=orange, medium=blue, low=gray)
- Status indicators show active/inactive
- Pagination controls at bottom
- No errors in browser console

### Test 3: Filter Rules
**Steps**:
1. Navigate to `/compliance/rules`
2. Test each filter:
   - Uncheck "Active Rules Only" → Should show inactive rules
   - Select "Payment Terms" category → Should filter by category
   - Select "Critical" severity → Should filter by severity
   - Type "payment" in search → Should filter by keyword

**Expected Results**:
- Filtered rules count updates in stats bar
- Table shows only matching rules
- Filters work independently and in combination
- Search is case-insensitive
- Pagination resets to page 1 when filtering

### Test 4: Sort Rules
**Steps**:
1. Navigate to `/compliance/rules`
2. Click column headers to sort:
   - "Rule Name" → Should sort alphabetically
   - "Severity" → Should sort by severity level
   - "Category" → Should sort by category
   - "Updated" → Should sort by date

**Expected Results**:
- Arrow icon appears next to sorted column
- Click again to reverse sort direction
- Data sorts correctly
- Sorting persists when changing pages

### Test 5: Create New Rule
**Steps**:
1. Navigate to `/compliance/rules`
2. Click "New Rule" button
3. Fill out form:
   - **Name**: "Test Rule - Payment Terms Check"
   - **Description**: "This is a test rule to verify that payment terms are specified in the contract and are reasonable (30 days or less)."
   - **Severity**: "Medium"
   - **Category**: "Payment Terms"
   - **Active**: Checked
4. Click "Create Rule"

**Expected Results**:
- Form validation passes (no error messages)
- Character counts update as you type
- Severity preview badge displays
- Category description appears below dropdown
- Success toast appears: "Rule created successfully"
- Redirects to `/compliance/rules`
- New rule appears in list

### Test 6: Form Validation
**Steps**:
1. Navigate to `/compliance/rules/new`
2. Try to save with empty form → Should show validation errors
3. Enter name with 2 characters → Should show "at least 3 characters" error
4. Enter description with 5 characters → Should show "at least 10 characters" error
5. Leave severity blank → Should show "required" error
6. Leave category blank → Should show "required" error

**Expected Results**:
- Error messages display in red below fields
- "Please fix validation errors" toast appears
- Form does not submit
- Character counts turn red when limits exceeded

### Test 7: Edit Existing Rule
**Steps**:
1. Navigate to `/compliance/rules`
2. Click edit icon for any rule
3. Verify form loads with existing data
4. Modify description: Add " (Updated)"
5. Click "Save Changes"

**Expected Results**:
- Edit mode detected (route has `:id` parameter)
- Form pre-populated with rule data
- Metadata section displays at bottom (ID, dates, creator)
- Only changed field sent in update request
- Success toast: "Rule updated successfully"
- Redirects to `/compliance/rules`
- Updated rule shows in list with new updated_date

### Test 8: Unsaved Changes Warning
**Steps**:
1. Navigate to `/compliance/rules/new`
2. Enter some text in name field
3. Click "Cancel" button

**Expected Results**:
- Confirmation dialog appears: "You have unsaved changes. Are you sure you want to leave?"
- Click "Cancel" → Stay on form
- Click "OK" → Navigate back to `/compliance/rules`

### Test 9: Toggle Rule Status
**Steps**:
1. Navigate to `/compliance/rules`
2. Find an active rule
3. Click the pause icon in actions column
4. Observe status change

**Expected Results**:
- Success toast: "Rule deactivated"
- Status indicator changes from "Active" (green) to "Inactive" (gray)
- Play icon replaces pause icon
- Rule remains in list (still visible with "Active Rules Only" unchecked)
- No page reload required

### Test 10: Delete Single Rule
**Steps**:
1. Navigate to `/compliance/rules`
2. Click trash icon for any rule
3. Confirm deletion in dialog

**Expected Results**:
- Confirmation dialog: "Are you sure you want to delete...?"
- Click "OK" → Rule deleted
- Success toast: "Rule deleted successfully"
- Rule removed from list
- Total rules count decrements

### Test 11: Bulk Delete Rules
**Steps**:
1. Navigate to `/compliance/rules`
2. Check checkboxes for 3 rules
3. Click "Delete Selected" button in stats bar
4. Confirm deletion

**Expected Results**:
- Selected count shows in stats bar: "Selected: 3"
- Confirmation dialog: "Are you sure you want to delete 3 selected rule(s)?"
- Click "OK" → All selected rules deleted
- Success toast: "3 rule(s) deleted successfully"
- Selected checkboxes cleared
- Rules removed from list

### Test 12: Select/Deselect All
**Steps**:
1. Navigate to `/compliance/rules`
2. Click checkbox in table header (select all)
3. Observe all visible rules selected
4. Click again to deselect all

**Expected Results**:
- First click: All rules on current page selected
- Second click: All selections cleared
- Selected count updates in stats bar
- Individual checkboxes sync with header checkbox

### Test 13: Export to CSV
**Steps**:
1. Navigate to `/compliance/rules`
2. Apply some filters to get specific rules
3. Click "Export" button

**Expected Results**:
- CSV file downloads automatically
- Filename format: `compliance-rules-YYYY-MM-DD.csv`
- CSV contains filtered rules only
- Headers: Name, Description, Severity, Category, Active, Created, Updated
- Data properly quoted (handles commas and quotes in text)
- Success toast: "Rules exported to CSV"

### Test 14: Pagination
**Steps**:
1. Navigate to `/compliance/rules`
2. Create enough rules to span multiple pages (>20)
3. Test pagination:
   - Click page numbers
   - Click "Previous" and "Next" buttons
   - Change items per page (10/20/50/100)

**Expected Results**:
- Current page highlighted in blue
- Previous/Next buttons disabled at boundaries
- Page info updates: "Showing X to Y of Z rules"
- Changing items per page resets to page 1
- Up to 5 page numbers visible at once

### Test 15: Responsive Design
**Steps**:
1. Navigate to `/compliance/rules`
2. Resize browser window to mobile width (<768px)
3. Observe layout changes

**Expected Results**:
- Navigation stacks vertically
- Filters stack vertically
- Description column hides on medium screens (<1024px)
- Action buttons remain accessible
- Forms adjust to single column
- Touch-friendly button sizes

### Test 16: Create New Category (Inline)
**Steps**:
1. Navigate to `/compliance/rules/new`
2. Click "New Category" button next to category dropdown
3. Enter category details in prompts:
   - **ID**: "test_category"
   - **Name**: "Test Category"
   - **Description**: "This is a test category for testing inline creation"

**Expected Results**:
- Three sequential prompts appear
- Category created via API
- Success toast: "Category created successfully"
- Category dropdown reloads with new category
- New category automatically selected

### Test 17: View Rule Details
**Steps**:
1. Navigate to `/compliance/rules`
2. Click on a rule name (blue link)

**Expected Results**:
- Navigates to `/compliance/rules/view/:id`
- Same editor component loads in view mode
- Form should be read-only (or we need to implement view-only mode)

**Note**: View-only mode may need additional implementation if you want it truly read-only.

### Test 18: Navigation Integration
**Steps**:
1. Start at Query Builder
2. Click "Compliance Rules" in navbar
3. Verify active link highlighting
4. Navigate back to Query Builder
5. Verify "Compliance Rules" link no longer highlighted

**Expected Results**:
- Smooth navigation between routes
- Active route always highlighted in navbar
- Browser back/forward buttons work correctly
- No page reloads (SPA behavior)

### Test 19: Error Handling
**Steps**:
1. Stop the backend (web_app)
2. Navigate to `/compliance/rules`
3. Observe error handling
4. Try to create a rule
5. Observe error toast

**Expected Results**:
- Error toast displays when API calls fail
- Error message shows: "Error loading compliance rules"
- Creating rule shows: "Error: [error details]"
- UI remains stable (no crashes)
- User can retry after restarting backend

### Test 20: Dashboard Navigation (Placeholder)
**Steps**:
1. Navigate to `/compliance/rules`
2. Click "Dashboard" button in header

**Expected Results**:
- Navigates to `/compliance/dashboard`
- Route exists but component not yet implemented (Phase 6)
- May show blank page or error

## Browser Console Checks

Throughout testing, monitor the browser console for:

### ✅ Good Signs:
- No errors or warnings
- Successful HTTP requests (200, 201 status codes)
- Observable subscriptions complete properly

### ❌ Red Flags:
- TypeScript compilation errors
- HTTP 404 (check backend is running)
- HTTP 500 (check backend logs)
- Memory leaks from unclosed subscriptions
- Missing component imports

## Performance Checks

### Load Times:
- Initial page load: < 2 seconds
- Route navigation: < 500ms
- API calls: < 1 second (depends on backend)

### Responsiveness:
- Typing in search: Immediate filtering
- Sorting: Instant reorder
- Pagination: Smooth transitions

## Known Limitations (Phase 5)

1. **Dashboard Not Implemented**: Dashboard route exists but component is Phase 6
2. **View Mode**: View route uses same editor component (may need read-only implementation)
3. **No Rule Details Page**: Dedicated details page could be added in future
4. **No Rule History**: Version history not tracked in UI (only latest updated_date)

## Common Issues and Solutions

### Issue 1: "Cannot GET /compliance/rules" Error
**Solution**: Ensure Angular dev server is running (`npm start` in query-builder directory)

### Issue 2: Empty Rules List
**Solution**:
- Check backend is running on port 8000
- Create sample rules using `sample_compliance_rules.md`
- Check browser console for API errors

### Issue 3: Compilation Errors
**Solution**:
- Verify all imports are correct
- Check for typos in component/service names
- Ensure all files are saved
- Try `npm install` to install dependencies

### Issue 4: Styles Not Loading
**Solution**:
- Verify `.scss` files are in correct locations
- Check for syntax errors in SCSS
- Clear browser cache and reload

### Issue 5: Navigation Not Working
**Solution**:
- Verify routes in `app.routes.ts`
- Check component imports are correct
- Ensure `RouterOutlet` is in app template

## Next Steps (Phase 6)

After successfully testing Phase 5:

1. **Dashboard Component**: Summary view with statistics and charts
2. **Rule Details View**: Dedicated page showing rule details and evaluation history
3. **Contract Results View**: View which contracts pass/fail each rule
4. **Stale Results Detection**: Highlight when evaluations need re-running
5. **Dashboard Drilldowns**: Click statistics to see detailed contract lists

## Success Criteria

Phase 5 is complete when:

- ✅ All 20 test scenarios pass
- ✅ No errors in browser console
- ✅ Responsive design works on mobile/tablet/desktop
- ✅ All CRUD operations function correctly
- ✅ Navigation and routing work properly
- ✅ Form validation prevents invalid data
- ✅ Error handling gracefully manages API failures

## Reporting Issues

If you encounter issues during testing:

1. **Check browser console** for errors
2. **Check backend logs** for API errors
3. **Verify prerequisites** (backend running, sample data loaded)
4. **Document the issue**:
   - What you were doing
   - Expected behavior
   - Actual behavior
   - Error messages
   - Browser and version
5. **Test workarounds** if available
