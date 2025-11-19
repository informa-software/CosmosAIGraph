# Clause Library Phase 3 - Testing Guide

## Overview
This guide provides step-by-step testing procedures for all Phase 3 functionality including CategoryTreeComponent, VariableManagerComponent, and all bug fixes.

---

## Test Environment
- **Angular App**: Running on https://localhost:4200
- **API**: Running on http://localhost:8000
- **Browser**: Chrome/Edge (for best compatibility)

---

## 1. Category Tree Navigation Tests

### Test 1.1: Category Tree Display
**Location**: Navigate to `/clause-library`

**Expected Results**:
- ✅ Category tree appears in left sidebar (280px wide on desktop)
- ✅ Categories display with emoji icons (🛡️, 🔒, ⚖️, etc.) not text names
- ✅ Root categories are expanded by default
- ✅ Each category shows clause count badge
- ✅ "All Clauses" option at top

**Actions**:
1. Open clause library page
2. Verify tree structure renders correctly
3. Check that icons are emojis (not "shield", "lock", etc.)
4. Verify clause counts are displayed

**Pass Criteria**: All categories visible with proper icons and counts

---

### Test 1.2: Category Expansion/Collapse
**Expected Results**:
- ✅ Categories with children show expand/collapse arrows (▶/▼)
- ✅ Clicking arrow toggles expansion without selecting category
- ✅ Child categories indent properly (20px per level)
- ✅ Expansion state persists during session

**Actions**:
1. Click collapse arrow on expanded category
2. Verify children hide
3. Click expand arrow
4. Verify children reappear
5. Navigate to another page and back
6. Verify expansion states maintained

**Pass Criteria**: Smooth expansion/collapse without page reload

---

### Test 1.3: Category Selection and Filtering
**Expected Results**:
- ✅ Clicking category name highlights it (purple border, light purple background)
- ✅ Main content area filters to show only clauses in selected category
- ✅ Page resets to page 1 when category selected
- ✅ Clicking "All Clauses" clears filter and shows all clauses

**Actions**:
1. Click on a category with clauses
2. Verify category highlights
3. Verify clause list filters to that category
4. Click different category
5. Verify new filter applies
6. Click "All Clauses"
7. Verify all clauses shown

**Pass Criteria**: Filtering works correctly with visual feedback

---

### Test 1.4: Responsive Layout
**Expected Results**:
- ✅ Desktop (>1024px): Sidebar 280px, two-column layout
- ✅ Tablet (768-1024px): Sidebar 240px, narrower gap
- ✅ Mobile (<768px): Single column, tree above content

**Actions**:
1. Test on desktop resolution
2. Resize browser to tablet width
3. Resize to mobile width
4. Verify layout adapts appropriately

**Pass Criteria**: Layout responds to screen size changes

---

## 2. Variable Manager Tests

### Test 2.1: Variable Manager Access
**Location**: Navigate to `/clause-library/variables`

**Expected Results**:
- ✅ Page loads with header "🔤 Variable Manager"
- ✅ "➕ New Custom Variable" button in top right
- ✅ Search bar displays
- ✅ Tabs show: All Variables, System, Custom
- ✅ Variable cards display in grid (3-4 columns on desktop)

**Actions**:
1. Navigate to variable manager
2. Verify all UI elements present
3. Check grid layout renders properly

**Pass Criteria**: Clean, professional interface loads

---

### Test 2.2: Tab Filtering
**Expected Results**:
- ✅ "All Variables" tab shows both system and custom variables
- ✅ "System" tab shows only system variables with badge
- ✅ "Custom" tab shows only custom variables with badge
- ✅ Tab counts update dynamically (e.g., "System (15)")
- ✅ Active tab has purple underline

**Actions**:
1. Click "All Variables" tab - verify all shown
2. Click "System" tab - verify only system variables
3. Click "Custom" tab - verify only custom variables
4. Verify counts match displayed variables

**Pass Criteria**: Tabs filter correctly with accurate counts

---

### Test 2.3: Variable Search
**Expected Results**:
- ✅ Typing in search filters variables by name and description
- ✅ Search is case-insensitive
- ✅ Search works across all tabs
- ✅ "No variables found" message when no matches

**Actions**:
1. Type "CONTRACT" in search
2. Verify only variables with "CONTRACT" in name/description show
3. Clear search
4. Verify all variables return
5. Search for non-existent term
6. Verify empty state message

**Pass Criteria**: Search filters accurately in real-time

---

### Test 2.4: System Variables (Read-Only)
**Expected Results**:
- ✅ System variable cards have "system" badge in blue
- ✅ No edit/delete buttons on system variables
- ✅ System variables cannot be modified

**Actions**:
1. Find a system variable card
2. Verify blue "system" badge present
3. Verify no edit/delete buttons
4. Check 10+ system variables for consistency

**Pass Criteria**: System variables clearly marked as read-only

---

### Test 2.5: Create Custom Variable
**Expected Results**:
- ✅ Click "New Custom Variable" opens modal form
- ✅ Modal has fields: Name, Description, Default Value
- ✅ Name validation enforces uppercase with underscores
- ✅ Save button creates variable
- ✅ New variable appears in custom variables list
- ✅ Modal closes on save

**Actions**:
1. Click "➕ New Custom Variable"
2. Enter name "TEST_VARIABLE"
3. Enter description "Test variable for verification"
4. Enter default value "Test Value"
5. Click Save
6. Verify success toast
7. Verify variable appears in Custom tab

**Pass Criteria**: Variable creation works with validation

---

### Test 2.6: Edit Custom Variable
**Expected Results**:
- ✅ Click edit (✏️) button opens modal with pre-filled data
- ✅ Name field is read-only (greyed out)
- ✅ Can modify description and default value
- ✅ Save updates the variable
- ✅ Changes reflect immediately in card

**Actions**:
1. Find custom variable
2. Click edit button (✏️)
3. Verify name field is read-only
4. Change description
5. Change default value
6. Click Save
7. Verify changes appear in card

**Pass Criteria**: Editing works with name protection

---

### Test 2.7: Delete Custom Variable
**Expected Results**:
- ✅ Click delete (🗑️) button shows confirmation dialog
- ✅ Confirm deletes variable
- ✅ Variable removed from list
- ✅ Cancel preserves variable

**Actions**:
1. Find custom variable
2. Click delete button (🗑️)
3. Verify confirmation prompt
4. Click Cancel
5. Verify variable still present
6. Click delete again
7. Click Confirm
8. Verify variable removed
9. Verify success toast

**Pass Criteria**: Delete with confirmation works correctly

---

### Test 2.8: Variable Name Validation
**Expected Results**:
- ✅ Invalid names show error toast
- ✅ Valid format: uppercase letters, numbers, underscores
- ✅ Must start with letter
- ✅ Examples of valid: CONTRACT_DATE, PARTY_1_NAME
- ✅ Examples of invalid: contract_date, 1_CONTRACT, Contract-Date

**Actions**:
1. Try creating variable with lowercase name "test_var"
2. Verify error toast appears
3. Try name with hyphen "TEST-VAR"
4. Verify error toast
5. Try valid name "TEST_VARIABLE_123"
6. Verify it saves successfully

**Pass Criteria**: Validation prevents invalid names

---

## 3. Clause Editor Tests

### Test 3.1: Quill Editor Full Width
**Location**: Navigate to `/clause-library/new` or edit existing clause

**Expected Results**:
- ✅ Quill editor uses full width of container
- ✅ No white space beside editor
- ✅ Editor height is 300px
- ✅ Toolbar displays at top with formatting options
- ✅ Editor is responsive on smaller screens

**Actions**:
1. Navigate to new clause page
2. Go to "Clause Content" tab
3. Verify editor spans full width
4. Measure or visually confirm no white space on right
5. Verify editor height is appropriate (not too tall)

**Pass Criteria**: Editor uses full horizontal space (width: 100%)

---

### Test 3.2: Variable Insertion at Cursor
**Expected Results**:
- ✅ Variable chips display below editor
- ✅ Clicking variable inserts at cursor position (not end)
- ✅ Variable appears formatted in purple background
- ✅ Can insert multiple variables
- ✅ Can insert variables in middle of text

**Actions**:
1. Type "This is a contract for "
2. Click CONTRACTOR_NAME variable chip
3. Verify variable inserts at cursor (after "for ")
4. Type " dated "
5. Click CONTRACT_DATE variable chip
6. Verify inserts at new cursor position
7. Verify both variables formatted correctly

**Pass Criteria**: Variables insert at cursor, not at end

---

### Test 3.3: Rich Text Formatting
**Expected Results**:
- ✅ Toolbar has bold, italic, underline buttons
- ✅ Can apply formatting to text
- ✅ Can create numbered and bulleted lists
- ✅ Variables maintain formatting when styled text
- ✅ Formatting toolbar icons display correctly (not broken icons)

**Actions**:
1. Type text in editor
2. Select text and click Bold
3. Verify text becomes bold
4. Try italic, underline
5. Create bulleted list
6. Create numbered list
7. Insert variable in formatted text
8. Verify all formatting preserved

**Pass Criteria**: All Quill formatting features work

---

## 4. Version History Tests

### Test 4.1: Version History Display
**Location**: Edit existing clause, click "Version History" tab

**Expected Results**:
- ✅ All versions of clause display in chronological order (newest first)
- ✅ Each version shows version number, created date, created by
- ✅ Current version highlighted
- ✅ Parent version (if any) included in list
- ✅ All child versions included

**Actions**:
1. Edit a clause with multiple versions
2. Click "Version History" tab
3. Verify versions appear in descending order
4. Verify current version is highlighted
5. Check version details are complete

**Pass Criteria**: Complete version history displays correctly

---

### Test 4.2: Version History Query (No SQL Errors)
**Expected Results**:
- ✅ Version history loads without errors
- ✅ No 400/500 errors in network tab
- ✅ Query handles clauses with and without parents
- ✅ Root clauses show all children
- ✅ Child clauses show siblings and parent

**Actions**:
1. Open version history for root clause (no parent)
2. Verify loads successfully
3. Open version history for child clause (has parent)
4. Verify loads successfully
5. Check browser console for errors
6. Check network tab for failed requests

**Pass Criteria**: No SQL query errors, both cases work

---

## 5. Integration Tests

### Test 5.1: Create Clause with Category Selection
**Expected Results**:
- ✅ Can create new clause
- ✅ Category dropdown shows all categories
- ✅ Can select category from dropdown
- ✅ New clause appears in selected category
- ✅ Category tree updates clause count

**Actions**:
1. Navigate to clause library
2. Note clause count for a category
3. Click "➕ New Clause"
4. Fill in basic details
5. Select category from dropdown
6. Add content with variables
7. Save clause
8. Return to clause library
9. Verify clause appears in category
10. Verify category count increased

**Pass Criteria**: End-to-end clause creation with categorization

---

### Test 5.2: Filter by Category and Edit
**Expected Results**:
- ✅ Select category to filter clauses
- ✅ Edit clause from filtered view
- ✅ Return to list maintains filter
- ✅ Version history accessible from filtered view

**Actions**:
1. Select category in tree
2. Verify filtered list displays
3. Click edit on a clause
4. Make changes and save
5. Click back or navigate to clause library
6. Verify still filtered to same category
7. Verify updated clause shows changes

**Pass Criteria**: Category filter persists through editing

---

### Test 5.3: Variable Usage Across Components
**Expected Results**:
- ✅ Create custom variable in Variable Manager
- ✅ New variable appears in clause editor variable chips
- ✅ Can insert custom variable in clause content
- ✅ Custom variable renders correctly in clause viewer

**Actions**:
1. Go to Variable Manager
2. Create custom variable "TEST_COMPANY"
3. Navigate to clause editor
4. Verify TEST_COMPANY appears in variable chips
5. Insert variable in content
6. Save clause
7. View clause
8. Verify variable displays

**Pass Criteria**: Variables sync between manager and editor

---

### Test 5.4: Responsive Behavior End-to-End
**Expected Results**:
- ✅ Category tree collapses to top on mobile
- ✅ Variable cards stack in single column on mobile
- ✅ Clause editor remains functional on tablet
- ✅ Modal forms adapt to screen size

**Actions**:
1. Test clause library on mobile viewport
2. Verify tree navigation works
3. Test variable manager on mobile
4. Verify cards stack properly
5. Test clause editor on tablet
6. Verify editor and forms usable
7. Test modals on small screens
8. Verify readable and functional

**Pass Criteria**: Full functionality on all screen sizes

---

## 6. Error Handling Tests

### Test 6.1: Network Error Handling
**Expected Results**:
- ✅ Failed API calls show error toast
- ✅ Loading states display during requests
- ✅ Error messages are user-friendly
- ✅ Can retry after error

**Actions**:
1. Stop API server
2. Try to load clauses
3. Verify error toast appears
4. Try to create variable
5. Verify error toast
6. Restart API server
7. Retry operations
8. Verify success

**Pass Criteria**: Graceful error handling with recovery

---

### Test 6.2: Validation Error Messages
**Expected Results**:
- ✅ Empty required fields show validation messages
- ✅ Invalid variable names show specific error
- ✅ Cannot save with validation errors
- ✅ Error messages are clear and actionable

**Actions**:
1. Try to save clause with empty title
2. Verify validation error
3. Try to create variable with lowercase name
4. Verify specific error message
5. Fix validation errors
6. Verify can now save

**Pass Criteria**: Clear validation with helpful messages

---

## 7. Performance Tests

### Test 7.1: Large Category Tree
**Expected Results**:
- ✅ Tree with 50+ categories renders quickly (<1 second)
- ✅ Expansion/collapse is instantaneous
- ✅ Selection is responsive
- ✅ No lag when scrolling

**Actions**:
1. Load clause library with many categories
2. Time tree rendering
3. Rapidly expand/collapse categories
4. Quickly click through categories
5. Monitor browser performance tab

**Pass Criteria**: Smooth performance with large datasets

---

### Test 7.2: Variable List Performance
**Expected Results**:
- ✅ 100+ variables load quickly
- ✅ Search filters instantly (<100ms)
- ✅ Tab switching is immediate
- ✅ Scrolling is smooth

**Actions**:
1. Load variable manager with many variables
2. Test search responsiveness
3. Switch tabs rapidly
4. Scroll through long list
5. Check for lag or stuttering

**Pass Criteria**: Fast filtering and smooth scrolling

---

## Test Summary Checklist

### Category Tree (7 tests)
- [ ] Tree display with emoji icons
- [ ] Expansion/collapse functionality
- [ ] Category selection and filtering
- [ ] Responsive layout
- [ ] Performance with large tree
- [ ] Integration with clause list
- [ ] State persistence

### Variable Manager (8 tests)
- [ ] Page access and layout
- [ ] Tab filtering (All/System/Custom)
- [ ] Search functionality
- [ ] System variables read-only
- [ ] Create custom variable
- [ ] Edit custom variable
- [ ] Delete custom variable
- [ ] Name validation

### Clause Editor (3 tests)
- [ ] Quill editor full width
- [ ] Variable insertion at cursor
- [ ] Rich text formatting

### Version History (2 tests)
- [ ] Version display
- [ ] Query works without SQL errors

### Integration (4 tests)
- [ ] Create clause with category
- [ ] Filter and edit workflow
- [ ] Variable usage across components
- [ ] Responsive behavior

### Error Handling (2 tests)
- [ ] Network errors
- [ ] Validation errors

### Performance (2 tests)
- [ ] Large category tree
- [ ] Variable list performance

---

## Known Issues / TODO Items

### Variable Manager
- API integration incomplete (using TODO placeholders)
- Need to implement actual CRUD endpoints in backend
- Need to implement real-time sync with clause editor

### Category Tree
- No drag-and-drop reordering yet
- No context menu for category management
- Category counts may not update in real-time

### General
- No comprehensive error logging
- No analytics/usage tracking
- No keyboard shortcuts for power users

---

## Bug Fix Verification

### ✅ Fixed: CosmosDB SQL Null Check
**Verify**: Version history loads without 400 errors for clauses with and without parents

### ✅ Fixed: Category Icons Display
**Verify**: Icons show as emoji (🛡️, 🔒) not text ("shield", "lock")

### ✅ Fixed: Quill Editor Width
**Verify**: Editor uses full width with no white space beside it

---

## Testing Notes

**Browser Compatibility**:
- Primary: Chrome/Edge (Chromium)
- Secondary: Firefox, Safari
- Mobile: Chrome Mobile, Safari iOS

**Test Data Requirements**:
- At least 10 clauses with different categories
- At least 5 category levels for tree testing
- At least 20 variables (system + custom) for search testing
- At least 1 clause with 3+ versions for version history

**Performance Benchmarks**:
- Tree rendering: <1 second
- Variable search: <100ms
- Category selection: <200ms
- Clause save: <2 seconds

---

## Testing Complete

Once all tests pass, Phase 3 is ready for:
- ✅ User acceptance testing
- ✅ Deployment to staging environment
- ✅ Documentation updates
- ✅ Training material creation

**End of Testing Guide**
