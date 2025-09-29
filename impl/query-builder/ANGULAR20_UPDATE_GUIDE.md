# Angular 20 Query Builder Update Guide

Your project uses Angular 20 with standalone components. This requires a different approach than the traditional module-based structure.

## Key Differences in Angular 20

1. **Standalone Components**: No NgModules required
2. **Direct Imports**: Components import their dependencies directly
3. **New File Structure**: Uses `app.ts` instead of `app.component.ts`
4. **Signals**: Uses Angular signals for reactive state

## Step-by-Step Update Instructions

### 1. Update the main app.ts file

```typescript
// src/app/app.ts
import { Component } from '@angular/core';
import { QueryBuilderMainComponent } from './query-builder/query-builder-main/query-builder-main';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [QueryBuilderMainComponent],
  template: `<app-query-builder-main></app-query-builder-main>`,
  styles: []
})
export class App {
  title = 'query-builder';
}
```

### 2. Update app.config.ts for providers

```typescript
// src/app/app.config.ts
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient } from '@angular/common/http';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }), 
    provideRouter(routes),
    provideAnimationsAsync(),
    provideHttpClient()
  ]
};
```

### 3. Update Each Component to be Standalone

For EACH component file, you need to:

1. Import CommonModule and other required modules
2. Add `standalone: true` to the @Component decorator
3. Add `imports` array with all required modules
4. Export the class with "Component" suffix

#### Example: template-selector.ts

```typescript
import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { QueryTemplate } from '../models/query.models';
import { MockDataService } from '../services/mock-data.service';

@Component({
  selector: 'app-template-selector',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatChipsModule, MatButtonModule],
  templateUrl: './template-selector.html',
  styleUrls: ['./template-selector.scss'],
  providers: [MockDataService]
})
export class TemplateSelectorComponent {
  // ... component code ...
}
```

#### Example: entity-selector.ts

```typescript
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
// ... rest of imports

@Component({
  selector: 'app-entity-selector',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule
  ],
  templateUrl: './entity-selector.html',
  styleUrls: ['./entity-selector.scss']
})
export class EntitySelectorComponent implements OnInit {
  // ... component code ...
}
```

### 4. Component Name Mapping

Make sure to use the correct component class names:

| File | Class Name |
|------|------------|
| template-selector.ts | TemplateSelectorComponent |
| entity-selector.ts | EntitySelectorComponent |
| query-preview.ts | QueryPreviewComponent |
| query-builder-main.ts | QueryBuilderMainComponent |

### 5. Service Registration

Services can be provided at the component level or in app.config.ts:

```typescript
// Option 1: In component
@Component({
  // ...
  providers: [MockDataService, QueryBuilderService, EntityService]
})

// Option 2: In app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    // ... existing providers
    MockDataService,
    QueryBuilderService, 
    EntityService
  ]
};
```

## Quick Fix Script

Run this PowerShell to fix the basic structure:

```powershell
# Fix app.ts
$appContent = @'
import { Component } from '@angular/core';
import { QueryBuilderMainComponent } from './query-builder/query-builder-main/query-builder-main';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [QueryBuilderMainComponent],
  template: `<app-query-builder-main></app-query-builder-main>`,
  styles: []
})
export class App {
  title = 'query-builder';
}
'@
Set-Content -Path "src/app/app.ts" -Value $appContent -Encoding UTF8
```

## Common Issues & Solutions

### Issue: "Can't bind to 'formControl'"
**Solution**: Import `ReactiveFormsModule` in the component

### Issue: "Mat-* is not a known element"
**Solution**: Import the specific Material module (e.g., `MatCardModule`)

### Issue: "Can't resolve service"
**Solution**: Add service to component's `providers` array or app.config.ts

### Issue: "ngFor/ngIf not working"
**Solution**: Import `CommonModule` in the component

## Testing Your Updates

1. Start with updating app.ts
2. Update one component at a time
3. Run `ng serve` to test after each update
4. Check browser console for specific import errors

## Material Design Modules Needed

```typescript
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatListModule } from '@angular/material/list';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
```

## Next Steps

1. Update app.ts and app.config.ts first
2. Update each component to be standalone with proper imports
3. Ensure all HTML templates use the correct selectors
4. Run `ng serve` and fix any remaining import errors