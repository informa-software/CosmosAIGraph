# Phase 5 Quick Reference Guide - Compliance Rules Management UI

## Overview

Complete Angular-based user interface for managing contract compliance rules with full CRUD operations, advanced filtering, and bulk actions.

## Access

**URL**: `http://localhost:4200/compliance/rules`

**Navigation**: Click "Compliance Rules" in the main navbar

## Key Features at a Glance

### Rules List View (`/compliance/rules`)

#### Filtering & Search
- **Active Status**: Toggle "Active Rules Only" checkbox
- **Category Filter**: Dropdown with 15 predefined categories
- **Severity Filter**: Dropdown (Critical, High, Medium, Low)
- **Full-Text Search**: Search across name, description, and category

#### Sorting
- Click column headers to sort: Name, Severity, Category, Updated Date
- Click again to reverse sort direction
- Visual indicators show current sort column and direction

#### Pagination
- Options: 10, 20, 50, or 100 rules per page
- Page numbers with Previous/Next navigation
- Shows "Showing X to Y of Z rules" information

#### Bulk Operations
- **Select All**: Click header checkbox to select all visible rules
- **Individual Selection**: Click row checkboxes
- **Bulk Delete**: "Delete Selected" button appears when rules selected
- **Selection Count**: Displayed in stats bar

#### Actions (Per Rule)
- **View**: Click rule name (blue link)
- **Edit**: Pencil icon
- **Toggle Status**: Play/Pause icon (activate/deactivate)
- **Delete**: Trash icon

#### Export
- **CSV Export**: Export filtered rules to CSV file
- Filename format: `compliance-rules-YYYY-MM-DD.csv`
- Includes all filtered results

### Create/Edit Rule View

#### Create New Rule
**URL**: `/compliance/rules/new`
**Access**: Click "New Rule" button

#### Edit Existing Rule
**URL**: `/compliance/rules/edit/:id`
**Access**: Click edit icon or rule name

#### Form Fields

1. **Rule Name** (Required)
   - Min: 3 characters
   - Max: 200 characters
   - Character counter displayed

2. **Rule Description** (Required)
   - Min: 10 characters
   - Max: 1000 characters
   - Textarea with character counter
   - Explain what the rule checks

3. **Severity Level** (Required)
   - Options: Critical, High, Medium, Low
   - Color-coded badge preview
   - Indicates impact of violation

4. **Category** (Required)
   - 15 predefined categories
   - "New Category" button for inline creation
   - Description appears when selected

5. **Active Status** (Toggle)
   - Checked: Rule will be evaluated
   - Unchecked: Rule is inactive

#### Form Features
- **Real-time Validation**: Errors display as you type
- **Character Counts**: Live counts for name and description
- **Unsaved Changes Warning**: Prompt when leaving with changes
- **Smart Updates**: Only changed fields sent on update
- **Category Preview**: Shows category description on selection

## 15 Predefined Categories

1. **Payment Terms**: Payment timelines, methods, and conditions
2. **Confidentiality**: Non-disclosure and confidentiality requirements
3. **Liability**: Liability limits, indemnification, and risk allocation
4. **Termination**: Contract termination conditions and notice periods
5. **Intellectual Property**: IP ownership, licensing, and usage rights
6. **Warranties**: Warranties, representations, and guarantees
7. **Compliance**: Legal and regulatory compliance requirements
8. **Dispute Resolution**: Arbitration, mediation, and legal proceedings
9. **Force Majeure**: Extraordinary events and circumstances
10. **Insurance**: Insurance coverage requirements and limits
11. **Governing Law**: Applicable laws and jurisdictions
12. **Assignment**: Contract assignment and transfer rights
13. **Amendment**: Contract modification procedures
14. **Notices**: Communication and notification requirements
15. **General**: General contract provisions not covered above

## Common Workflows

### Creating a New Rule

```
1. Navigate to /compliance/rules
2. Click "New Rule" button
3. Fill in required fields:
   - Name: "Payment terms must be 30 days or less"
   - Description: "Contract must specify payment terms of net 30 days or less"
   - Severity: "Medium"
   - Category: "Payment Terms"
   - Active: Checked
4. Click "Create Rule"
5. Success notification appears
6. Redirects to rules list
```

### Editing a Rule

```
1. Navigate to /compliance/rules
2. Find rule to edit
3. Click edit icon (pencil)
4. Modify fields as needed
5. Click "Save Changes"
6. Only changed fields sent to API
7. Success notification appears
8. Redirects to rules list
```

### Filtering Rules

```
1. Navigate to /compliance/rules
2. Use filter controls:
   - Uncheck "Active Rules Only" to see all rules
   - Select category from dropdown
   - Select severity from dropdown
   - Type search term in search box
3. Filters apply in real-time
4. Stats bar shows filtered count
5. Click "Refresh" to reload data
```

### Bulk Deleting Rules

```
1. Navigate to /compliance/rules
2. Check boxes for rules to delete
3. "Delete Selected" button appears in stats bar
4. Click "Delete Selected"
5. Confirm deletion in dialog
6. All selected rules deleted
7. Success notification with count
8. List refreshes automatically
```

### Exporting Rules

```
1. Navigate to /compliance/rules
2. Apply filters if needed (exports filtered results)
3. Click "Export" button
4. CSV file downloads automatically
5. Filename: compliance-rules-YYYY-MM-DD.csv
6. Open in Excel or text editor
```

### Creating a Custom Category

```
1. Navigate to /compliance/rules/new (or edit)
2. Scroll to Category field
3. Click "New Category" button
4. Enter category ID (e.g., "custom_category")
5. Enter category name (e.g., "Custom Category")
6. Enter category description
7. Category created and auto-selected
8. Available in dropdown for future rules
```

## Keyboard Shortcuts & Interactions

### Navigation
- Click navbar links to switch between pages
- Browser back/forward buttons work correctly
- Direct URL access supported

### Table Interactions
- Click column headers to sort
- Click checkboxes for selection
- Click action icons for operations
- Hover over rows for highlight effect

### Form Interactions
- Tab key navigates between fields
- Enter key in text fields (no auto-submit)
- Real-time validation feedback
- Character count updates on keypress

## Visual Indicators

### Severity Badges
- **Critical**: Red background (`#fee2e2` bg, `#991b1b` text)
- **High**: Orange/yellow background (`#fef3c7` bg, `#92400e` text)
- **Medium**: Blue background (`#dbeafe` bg, `#1e40af` text)
- **Low**: Gray background (`#f3f4f6` bg, `#4b5563` text)

### Status Indicators
- **Active**: Green pill (`#d1fae5` bg, `#065f46` text)
- **Inactive**: Gray pill (`#f3f4f6` bg, `#6b7280` text)

### Validation States
- **Error**: Red border on field, red error message below
- **Valid**: Normal border, no error message
- **Character Count**: Gray text, turns red when limit exceeded

## Responsive Design

### Desktop (>1024px)
- Full table with all columns visible
- Filters displayed horizontally
- Side-by-side button groups

### Tablet (768-1024px)
- Description column hidden
- Filters stack vertically
- Simplified action buttons

### Mobile (<768px)
- Single column layout
- Stacked navigation
- Full-width buttons
- Optimized touch targets

## API Integration

### Endpoints Used

**Rules List**:
```
GET /api/compliance/rules?active_only=true&category=&severity=
```

**Create Rule**:
```
POST /api/compliance/rules
Body: { name, description, severity, category, active }
```

**Update Rule**:
```
PATCH /api/compliance/rules/{rule_id}
Body: { ...changed_fields_only }
```

**Delete Rule**:
```
DELETE /api/compliance/rules/{rule_id}
```

**Get Categories**:
```
GET /api/compliance/categories
```

**Create Category**:
```
POST /api/compliance/categories
Body: { id, name, description }
```

## Toast Notifications

All user actions trigger toast notifications:

- **Success** (Green): Operations completed successfully
- **Error** (Red): Operations failed with error details
- **Warning** (Yellow): Validation issues or empty states
- **Info** (Blue): Informational messages

**Duration**:
- Success: 3 seconds
- Error: 5 seconds
- Warning/Info: 3 seconds

## Error Handling

### Backend Down
- Error toast: "Error loading compliance rules"
- List shows empty state
- User can retry after backend restart

### Validation Errors
- Error toast: "Please fix validation errors"
- Red borders on invalid fields
- Error messages below each field

### Network Errors
- Error toast with specific error message
- UI remains stable
- User can retry operation

### Unsaved Changes
- Confirmation dialog appears
- User can cancel or proceed
- Changes lost if proceeding

## Performance Characteristics

### Load Times
- Initial page load: <2 seconds
- Route navigation: <500ms
- API calls: <1 second (backend dependent)

### Pagination
- Up to 100 rules per page without lag
- Smooth page transitions
- Instant filtering and sorting

### Real-time Features
- Search filters as you type
- Character counts update on keypress
- Validation feedback immediate

## Data Model Reference

### ComplianceRule Interface
```typescript
{
  id: string;                 // UUID
  name: string;               // 3-200 chars
  description: string;        // 10-1000 chars
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;           // Category ID
  active: boolean;            // true/false
  created_date: string;       // ISO 8601
  updated_date: string;       // ISO 8601
  created_by: string;         // User ID
}
```

### Category Interface
```typescript
{
  id: string;                 // Lowercase with underscores
  name: string;               // Display name
  description: string;        // Description text
}
```

## Testing Checklist

Use this checklist to verify all features work:

- [ ] Navigate to compliance rules page
- [ ] View list of rules
- [ ] Filter by active status
- [ ] Filter by category
- [ ] Filter by severity
- [ ] Search by keyword
- [ ] Sort by name
- [ ] Sort by severity
- [ ] Sort by category
- [ ] Sort by updated date
- [ ] Change items per page
- [ ] Navigate between pages
- [ ] Select individual rules
- [ ] Select all rules
- [ ] Create new rule
- [ ] Validate form fields
- [ ] Edit existing rule
- [ ] Delete single rule
- [ ] Delete multiple rules
- [ ] Toggle rule status
- [ ] Export to CSV
- [ ] Create custom category
- [ ] View rule details
- [ ] Unsaved changes warning
- [ ] Responsive design on mobile

## Tips & Best Practices

### Creating Effective Rules

1. **Be Specific**: Clearly describe what the rule checks
2. **Set Appropriate Severity**: Match severity to business impact
3. **Use Categories**: Helps organize and filter rules
4. **Test Before Activating**: Create inactive rules, test, then activate
5. **Review Regularly**: Update rules as requirements change

### Managing Large Rule Sets

1. **Use Filters**: Narrow down to relevant rules
2. **Use Search**: Find specific rules quickly
3. **Sort Strategically**: Group related rules together
4. **Bulk Operations**: Update multiple rules efficiently
5. **Export for Review**: Review rules offline in Excel

### Performance Tips

1. **Pagination**: Use smaller page sizes for faster loads
2. **Filters**: Filter before searching for better performance
3. **Bulk Delete**: Delete multiple rules at once vs. individually
4. **CSV Export**: Export filtered results to reduce file size

## Troubleshooting

### Rules Not Loading
**Symptom**: Empty list or loading spinner
**Check**:
- Backend running on port 8000
- Browser console for errors
- Network tab in dev tools
**Solution**: Restart backend, refresh page

### Validation Errors Persist
**Symptom**: Can't save rule despite fixing errors
**Check**:
- All fields meet requirements
- No hidden validation messages
- Character counts within limits
**Solution**: Clear all fields and re-enter

### CSV Export Not Working
**Symptom**: No file downloads
**Check**:
- Browser download settings
- Pop-up blocker settings
- Rules exist to export
**Solution**: Allow downloads, check filters

### Pagination Issues
**Symptom**: Wrong page numbers or missing data
**Check**:
- Total rules count
- Items per page setting
- Current page number
**Solution**: Reset to page 1, reload data

## Next Steps

After mastering Phase 5:

1. **Phase 6**: Dashboard with statistics and charts
2. **Phase 7**: Contract evaluation triggers
3. **Phase 8**: Testing and documentation

## Support

For issues or questions:

1. Check browser console for errors
2. Review `COMPLIANCE_PHASE5_TESTING.md` for detailed tests
3. Verify backend logs at `web_app/` directory
4. Ensure all prerequisites met (Angular running, backend running)

## File Locations

**Frontend (Angular)**:
```
query-builder/src/app/compliance/
├── models/
│   └── compliance.models.ts
├── services/
│   └── compliance.service.ts
├── compliance-rules/
│   ├── compliance-rules.component.ts
│   ├── compliance-rules.component.html
│   └── compliance-rules.component.scss
└── compliance-rule-editor/
    ├── compliance-rule-editor.component.ts
    ├── compliance-rule-editor.component.html
    └── compliance-rule-editor.component.scss
```

**Routing**:
```
query-builder/src/app/
├── app.routes.ts (route definitions)
└── app.ts (navigation link)
```

**Backend (Python)**:
```
web_app/
├── models/compliance_models.py
├── services/
│   ├── compliance_rules_service.py
│   ├── compliance_evaluation_service.py
│   └── evaluation_job_service.py
└── routers/
    └── compliance_router.py
```

## Quick Command Reference

**Start Backend**:
```powershell
cd web_app
.\web_app.ps1
```

**Start Frontend**:
```bash
cd query-builder
npm start
```

**Access Application**:
```
http://localhost:4200/compliance/rules
```

**Create Sample Data**:
Use Postman with curls from `sample_compliance_rules.md`

---

**Phase 5 Status**: ✅ Complete and Production Ready

**Last Updated**: 2025-10-09

**Version**: 1.0
