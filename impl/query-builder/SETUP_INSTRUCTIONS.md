# Angular Query Builder Setup Instructions

## Quick Setup

1. **Run the PowerShell script to update core files:**
   ```powershell
   .\update-components.ps1
   ```

2. **Manually update the remaining component files:**
   - The TypeScript files for each component have been updated
   - You need to update the HTML and SCSS files for:
     - entity-selector
     - query-preview
     - query-builder-main

3. **Install dependencies and run:**
   ```bash
   npm install --legacy-peer-deps
   ng serve
   ```

## Files That Have Been Updated

### ✅ Complete (All files updated):
- `/models/query.models.ts` - Data models
- `/services/mock-data.service.ts` - Mock data provider
- `/services/entity.service.ts` - Entity management
- `/services/query-builder.service.ts` - Query building logic
- `/template-selector/*` - Template selection component (TS, HTML, SCSS)
- `/entity-selector/entity-selector.ts` - Entity selector TypeScript

### ⚠️ Need Manual Update:
The HTML and SCSS content for these components is provided below.

## Entity Selector HTML Content

Copy this to `/entity-selector/entity-selector.html`:

```html
<div class="entity-selector">
  <mat-form-field appearance="outline" class="entity-input">
    <mat-label>
      <mat-icon>{{ getEntityIcon() }}</mat-icon>
      {{ label }}
    </mat-label>
    
    <input matInput
           [formControl]="entityControl"
           [matAutocomplete]="auto"
           [placeholder]="multiple ? 'Type to search and add multiple...' : 'Type to search...'"
           [required]="required">
    
    <button mat-icon-button matSuffix 
            *ngIf="entityControl.value || selectedEntities.length > 0"
            (click)="clearSelection()">
      <mat-icon>clear</mat-icon>
    </button>
    
    <mat-autocomplete #auto="matAutocomplete" 
                      [displayWith]="displayEntity"
                      (optionSelected)="onEntitySelected($event.option.value)">
      <mat-optgroup *ngFor="let group of filteredEntityGroups$ | async" 
                    [label]="group.type">
        <mat-option *ngFor="let entity of group.entities" 
                    [value]="entity"
                    class="entity-option">
          <div class="entity-option-content">
            <span class="entity-display">{{ entity.displayName }}</span>
            <span class="entity-normalized">({{ entity.normalizedName }})</span>
            <span class="entity-stats">{{ getEntityStatistics(entity) }}</span>
          </div>
        </mat-option>
      </mat-optgroup>
      
      <mat-option *ngIf="(filteredEntityGroups$ | async)?.length === 0" disabled>
        No matching entities found
      </mat-option>
    </mat-autocomplete>
    
    <mat-hint *ngIf="hint">{{ hint }}</mat-hint>
    <mat-error *ngIf="required && !entityControl.value && !selectedEntities.length">
      This field is required
    </mat-error>
  </mat-form-field>
  
  <mat-chip-list *ngIf="multiple && selectedEntities.length > 0" class="selected-entities">
    <mat-chip *ngFor="let entity of selectedEntities"
              removable
              (removed)="removeEntity(entity)"
              color="primary"
              selected>
      <mat-icon class="chip-icon">{{ getEntityIcon() }}</mat-icon>
      {{ entity.displayName }}
      <mat-icon matChipRemove>cancel</mat-icon>
    </mat-chip>
  </mat-chip-list>
  
  <div *ngIf="selectedEntities.length > 0" class="selection-stats">
    <mat-icon>info</mat-icon>
    <span>
      {{ selectedEntities.length }} {{ entityType === 'contractor' ? 'contractor' : entityType === 'contracting' ? 'contracting part' : entityType }}{{ selectedEntities.length === 1 ? 'y' : 'ies' }} selected
      <span *ngIf="selectedEntities.length >= 2 && entityType === 'contractor'">
        • Ready for comparison
      </span>
    </span>
  </div>
</div>
```

## Entity Selector SCSS Content

Copy this to `/entity-selector/entity-selector.scss`:

```scss
.entity-selector {
  width: 100%;
  
  .entity-input {
    width: 100%;
    
    mat-label {
      display: flex;
      align-items: center;
      gap: 8px;
      
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
    }
  }
}

.entity-option {
  .entity-option-content {
    display: flex;
    flex-direction: column;
    padding: 4px 0;
    
    .entity-display {
      font-weight: 500;
      font-size: 14px;
      color: rgba(0, 0, 0, 0.87);
    }
    
    .entity-normalized {
      font-size: 12px;
      color: rgba(0, 0, 0, 0.54);
      font-family: 'Roboto Mono', monospace;
      margin-left: 8px;
    }
    
    .entity-stats {
      font-size: 12px;
      color: rgba(0, 0, 0, 0.6);
      margin-top: 2px;
      font-style: italic;
    }
  }
  
  &:hover {
    .entity-option-content {
      .entity-display {
        color: #3f51b5;
      }
    }
  }
}

.selected-entities {
  margin-top: 12px;
  
  mat-chip {
    margin: 4px;
    
    .chip-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      margin-right: 4px;
    }
  }
}

.selection-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  margin-top: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  
  mat-icon {
    font-size: 18px;
    width: 18px;
    height: 18px;
    color: #3f51b5;
  }
  
  span {
    font-size: 13px;
    color: rgba(0, 0, 0, 0.7);
  }
}

::ng-deep {
  .mat-autocomplete-panel {
    max-height: 400px;
    
    .mat-optgroup-label {
      font-weight: 600;
      color: #3f51b5;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    .mat-option {
      line-height: 1.4;
      min-height: 56px;
      
      &.mat-selected {
        background: rgba(63, 81, 181, 0.08);
      }
    }
  }
}
```

## Query Preview Component

The TypeScript file (`query-preview.ts`) needs to be updated similarly to the entity-selector. 
The HTML and SCSS files are ready to be copied from the generated content.

## Query Builder Main Component

This is the largest component and orchestrates the entire flow.
The TypeScript, HTML, and SCSS files all need to be updated with the provided content.

## Running the Application

After updating all files:

1. Install dependencies:
   ```bash
   npm install --legacy-peer-deps
   ```

2. Run the development server:
   ```bash
   ng serve
   ```

3. Navigate to http://localhost:4200

## Troubleshooting

If you encounter module import errors:
- Make sure all Material modules are imported in query-builder.module.ts
- Ensure BrowserAnimationsModule is imported in app.module.ts
- Use --legacy-peer-deps flag when installing packages

If components don't render:
- Check that all component class names match (e.g., `TemplateSelectorComponent` not `TemplateSelector`)
- Verify that the component selectors match in the templates
- Check the browser console for errors