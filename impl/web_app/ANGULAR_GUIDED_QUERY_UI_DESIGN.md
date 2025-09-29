# Angular Guided Query Builder UI Design

## Executive Summary

This document outlines the design and implementation approach for an Angular-based guided query builder that simplifies complex contract analysis queries through templates and intelligent entity selection. The UI will transform user-friendly selections into structured queries that the backend can process efficiently.

## Design Philosophy

### Core Principles
1. **Progressive Disclosure**: Start simple, reveal complexity as needed
2. **Template-Driven**: Pre-defined query patterns guide users
3. **Entity-Aware**: Intelligent autocomplete with normalized/display name handling
4. **Visual Feedback**: Show query structure as it's being built
5. **Error Prevention**: Validate selections before submission

## Architecture Overview

### Frontend Architecture
```
Angular Application
├── Query Builder Module
│   ├── Template Selector Component
│   ├── Entity Selector Component
│   ├── Clause Selector Component
│   ├── Query Preview Component
│   └── Results Display Component
├── Shared Services
│   ├── Entity Service (cached entity lookups)
│   ├── Query Builder Service (query construction)
│   ├── Backend API Service (HTTP communications)
│   └── Query Template Service (template management)
└── State Management (NgRx or Akita)
```

### Query Flow
```
User Selection → Template → Entity Selection → Query Construction → Structured Query → Backend API → Results
```

## Query Template Designs

### Template 1: Compare Clauses
```typescript
interface CompareClausesTemplate {
  type: 'COMPARE_CLAUSES';
  parameters: {
    clauseType: ClauseType;              // Required: What to compare
    contractingParty?: Entity;           // Optional: Filter by contracting party
    contractors: Entity[];                // Required: 2+ contractors to compare
    dateRange?: DateRange;               // Optional: Contract date filter
  };
  
  // Generated structured query
  output: {
    operation: 'comparison';
    target: 'clauses';
    filters: {
      clause_type: string;
      contracting_party?: string;        // Normalized value
      contractor_parties: string[];       // Normalized values
      date_range?: [string, string];
    };
    display_names: Map<string, string>;  // Normalized → Display mapping
  };
}
```

### Template 2: Analyze Contract
```typescript
interface AnalyzeContractTemplate {
  type: 'ANALYZE_CONTRACT';
  parameters: {
    contractId?: string;                 // Direct contract ID
    // OR identify by parties
    contractingParty?: Entity;
    contractorParty?: Entity;
    analysisType: 'full' | 'clauses' | 'risks' | 'obligations';
    includeChunks: boolean;
  };
  
  output: {
    operation: 'analysis';
    target: 'contract';
    contract_identifier: {
      id?: string;
      parties?: {
        contracting: string;             // Normalized
        contractor: string;               // Normalized
      };
    };
    analysis_scope: string[];
  };
}
```

### Template 3: Find Contracts
```typescript
interface FindContractsTemplate {
  type: 'FIND_CONTRACTS';
  parameters: {
    parties: {
      contracting?: Entity[];
      contractor?: Entity[];
      either?: Entity[];                 // Party in either role
    };
    governingLaw?: Entity[];
    contractType?: ContractType[];
    dateRange?: DateRange;
    valueRange?: ValueRange;
    clauseContains?: {
      clauseType: ClauseType;
      keywords: string[];
    };
  };
  
  output: {
    operation: 'search';
    target: 'contracts';
    filters: {
      [key: string]: any;
    };
    search_strategy: 'db' | 'vector' | 'graph';
  };
}
```

### Template 4: Compare Contracts
```typescript
interface CompareContractsTemplate {
  type: 'COMPARE_CONTRACTS';
  parameters: {
    contracts: Array<{
      id?: string;
      parties?: {
        contracting: Entity;
        contractor: Entity;
      };
    }>;
    comparisonAspects: Array<'terms' | 'clauses' | 'obligations' | 'values'>;
  };
  
  output: {
    operation: 'comparison';
    target: 'contracts';
    contract_identifiers: Array<any>;
    aspects: string[];
  };
}
```

## UI Component Designs

### 1. Template Selector Component
```typescript
@Component({
  selector: 'app-template-selector',
  template: `
    <div class="template-grid">
      <mat-card *ngFor="let template of templates" 
                (click)="selectTemplate(template)"
                [class.selected]="selectedTemplate?.id === template.id">
        <mat-icon>{{ template.icon }}</mat-icon>
        <h3>{{ template.title }}</h3>
        <p>{{ template.description }}</p>
      </mat-card>
    </div>
  `
})
export class TemplateSelectorComponent {
  templates = [
    {
      id: 'COMPARE_CLAUSES',
      icon: 'compare_arrows',
      title: 'Compare Clauses',
      description: 'Compare specific clauses across multiple contracts'
    },
    {
      id: 'ANALYZE_CONTRACT',
      icon: 'analytics',
      title: 'Analyze Contract',
      description: 'Deep analysis of a single contract'
    },
    {
      id: 'FIND_CONTRACTS',
      icon: 'search',
      title: 'Find Contracts',
      description: 'Search for contracts by various criteria'
    },
    {
      id: 'COMPARE_CONTRACTS',
      icon: 'difference',
      title: 'Compare Contracts',
      description: 'Side-by-side comparison of multiple contracts'
    }
  ];
  
  @Output() templateSelected = new EventEmitter<QueryTemplate>();
}
```

### 2. Entity Selector Component with Autocomplete
```typescript
@Component({
  selector: 'app-entity-selector',
  template: `
    <mat-form-field class="entity-selector">
      <mat-label>{{ label }}</mat-label>
      <input matInput
             [formControl]="entityControl"
             [matAutocomplete]="auto"
             (input)="filterEntities($event.target.value)">
      <mat-autocomplete #auto="matAutocomplete" 
                        [displayWith]="displayEntity"
                        (optionSelected)="onEntitySelected($event)">
        <mat-optgroup *ngFor="let group of filteredEntityGroups | async" 
                      [label]="group.type">
          <mat-option *ngFor="let entity of group.entities" 
                      [value]="entity">
            <span class="entity-display">{{ entity.displayName }}</span>
            <span class="entity-meta">{{ entity.contractCount }} contracts</span>
          </mat-option>
        </mat-optgroup>
      </mat-autocomplete>
      <mat-hint>{{ hint }}</mat-hint>
    </mat-form-field>
  `
})
export class EntitySelectorComponent implements OnInit {
  @Input() entityType: 'contractor' | 'contracting' | 'governing_law' | 'any';
  @Input() label: string;
  @Input() hint: string;
  @Input() multiple: boolean = false;
  @Output() entitySelected = new EventEmitter<Entity>();
  
  entityControl = new FormControl();
  filteredEntityGroups: Observable<EntityGroup[]>;
  
  constructor(private entityService: EntityService) {}
  
  ngOnInit() {
    // Load entities from backend
    this.entityService.loadEntities(this.entityType);
    
    // Setup autocomplete with fuzzy matching
    this.filteredEntityGroups = this.entityControl.valueChanges.pipe(
      startWith(''),
      debounceTime(300),
      switchMap(value => this.entityService.searchEntities(value, this.entityType))
    );
  }
  
  filterEntities(searchText: string) {
    // Use the same fuzzy matching as backend
    // Show both normalized and display names in results
  }
  
  displayEntity(entity: Entity): string {
    return entity ? entity.displayName : '';
  }
  
  onEntitySelected(event: MatAutocompleteSelectedEvent) {
    const entity = event.option.value;
    this.entitySelected.emit({
      ...entity,
      normalizedName: entity.normalizedName,  // For backend
      displayName: entity.displayName         // For UI
    });
  }
}
```

### 3. Clause Type Selector
```typescript
@Component({
  selector: 'app-clause-selector',
  template: `
    <mat-form-field>
      <mat-label>Select Clause Type</mat-label>
      <mat-select [formControl]="clauseControl" [multiple]="multiple">
        <mat-option *ngFor="let clause of availableClauses" 
                    [value]="clause.type">
          <mat-icon>{{ clause.icon }}</mat-icon>
          {{ clause.displayName }}
        </mat-option>
      </mat-select>
    </mat-form-field>
  `
})
export class ClauseSelectorComponent {
  @Input() multiple: boolean = false;
  @Output() clauseSelected = new EventEmitter<ClauseType[]>();
  
  availableClauses = [
    { type: 'Indemnification', displayName: 'Indemnification', icon: 'shield' },
    { type: 'PaymentObligations', displayName: 'Payment Terms', icon: 'payment' },
    { type: 'TerminationObligations', displayName: 'Termination', icon: 'cancel' },
    { type: 'WarrantyObligations', displayName: 'Warranties', icon: 'verified' },
    { type: 'ConfidentialityObligations', displayName: 'Confidentiality', icon: 'lock' },
    // ... other clause types
  ];
  
  clauseControl = new FormControl();
}
```

### 4. Query Builder Component (Main Orchestrator)
```typescript
@Component({
  selector: 'app-query-builder',
  template: `
    <mat-stepper #stepper linear>
      <!-- Step 1: Select Template -->
      <mat-step [completed]="selectedTemplate">
        <ng-template matStepLabel>Choose Query Type</ng-template>
        <app-template-selector 
          (templateSelected)="onTemplateSelected($event)">
        </app-template-selector>
      </mat-step>
      
      <!-- Step 2: Configure Query -->
      <mat-step [completed]="queryValid">
        <ng-template matStepLabel>Configure Query</ng-template>
        
        <!-- Dynamic form based on template -->
        <div [ngSwitch]="selectedTemplate?.type">
          <!-- Compare Clauses Form -->
          <div *ngSwitchCase="'COMPARE_CLAUSES'" class="query-form">
            <app-clause-selector
              [multiple]="false"
              (clauseSelected)="updateQuery('clauseType', $event)">
            </app-clause-selector>
            
            <app-entity-selector
              entityType="contracting"
              label="Contracting Party (Optional)"
              hint="Leave blank to compare across all contracting parties"
              (entitySelected)="updateQuery('contractingParty', $event)">
            </app-entity-selector>
            
            <app-entity-selector
              entityType="contractor"
              label="Select Contractors to Compare"
              hint="Select 2 or more contractors"
              [multiple]="true"
              (entitySelected)="addContractor($event)">
            </app-entity-selector>
            
            <mat-chip-list>
              <mat-chip *ngFor="let contractor of selectedContractors"
                        removable
                        (removed)="removeContractor(contractor)">
                {{ contractor.displayName }}
                <mat-icon matChipRemove>cancel</mat-icon>
              </mat-chip>
            </mat-chip-list>
          </div>
          
          <!-- Other template forms... -->
        </div>
      </mat-step>
      
      <!-- Step 3: Review Query -->
      <mat-step>
        <ng-template matStepLabel>Review & Execute</ng-template>
        <app-query-preview 
          [query]="structuredQuery"
          [naturalLanguage]="naturalLanguageQuery">
        </app-query-preview>
        
        <button mat-raised-button color="primary" 
                (click)="executeQuery()"
                [disabled]="!queryValid">
          Execute Query
        </button>
      </mat-step>
    </mat-stepper>
  `
})
export class QueryBuilderComponent {
  selectedTemplate: QueryTemplate;
  structuredQuery: StructuredQuery;
  queryValid = false;
  
  constructor(
    private queryService: QueryBuilderService,
    private apiService: BackendApiService
  ) {}
  
  onTemplateSelected(template: QueryTemplate) {
    this.selectedTemplate = template;
    this.structuredQuery = this.queryService.initializeQuery(template);
  }
  
  updateQuery(field: string, value: any) {
    this.structuredQuery = this.queryService.updateQuery(
      this.structuredQuery, 
      field, 
      value
    );
    this.validateQuery();
  }
  
  get naturalLanguageQuery(): string {
    return this.queryService.toNaturalLanguage(this.structuredQuery);
  }
  
  async executeQuery() {
    const result = await this.apiService.executeStructuredQuery(
      this.structuredQuery
    ).toPromise();
    
    // Navigate to results view
  }
}
```

### 5. Query Preview Component
```typescript
@Component({
  selector: 'app-query-preview',
  template: `
    <mat-card class="query-preview">
      <mat-card-title>Query Preview</mat-card-title>
      
      <mat-tab-group>
        <mat-tab label="Natural Language">
          <div class="preview-content">
            <p>{{ naturalLanguage }}</p>
          </div>
        </mat-tab>
        
        <mat-tab label="Structured Query">
          <pre class="json-preview">{{ query | json }}</pre>
        </mat-tab>
        
        <mat-tab label="Expected Results">
          <div class="preview-content">
            <p>This query will:</p>
            <ul>
              <li *ngFor="let expectation of getExpectations()">
                {{ expectation }}
              </li>
            </ul>
          </div>
        </mat-tab>
      </mat-tab-group>
    </mat-card>
  `
})
export class QueryPreviewComponent {
  @Input() query: StructuredQuery;
  @Input() naturalLanguage: string;
  
  getExpectations(): string[] {
    // Generate human-readable expectations based on query
    return this.queryService.generateExpectations(this.query);
  }
}
```

## Backend API Requirements

### New API Endpoints Needed

#### 1. Entity Lookup Endpoint
```typescript
// GET /api/entities?type={contractor|contracting|governing_law}&search={text}
interface EntitySearchResponse {
  entities: Array<{
    normalizedName: string;      // For backend queries
    displayName: string;          // For UI display
    contractCount: number;        // Statistics
    totalValue?: number;          // For contractor/contracting parties
    type: string;                 // Entity type
    confidence?: number;          // Match confidence if fuzzy search
  }>;
  total: number;
  searchText: string;
}
```

#### 2. Structured Query Endpoint
```typescript
// POST /api/query/structured
interface StructuredQueryRequest {
  template: string;               // Template type
  operation: string;              // comparison, analysis, search
  target: string;                 // contracts, clauses, chunks
  filters: {
    [key: string]: any;           // Normalized values
  };
  displayNames: {                 // For result enhancement
    [normalizedName: string]: string;
  };
  options: {
    limit?: number;
    includeChunks?: boolean;
    includeContext?: boolean;
  };
}

interface StructuredQueryResponse {
  success: boolean;
  results: any[];                 // Varies by query type
  metadata: {
    executionTime: number;
    documentsScanned: number;
    strategy: string;             // Which search strategy was used
  };
  context?: string;               // RAG context if requested
}
```

#### 3. Query Templates Endpoint
```typescript
// GET /api/query/templates
interface QueryTemplatesResponse {
  templates: Array<{
    id: string;
    name: string;
    description: string;
    parameters: ParameterDefinition[];
    examples: QueryExample[];
  }>;
}
```

#### 4. Query Validation Endpoint
```typescript
// POST /api/query/validate
interface QueryValidationRequest {
  query: StructuredQuery;
}

interface QueryValidationResponse {
  valid: boolean;
  errors?: string[];
  warnings?: string[];
  estimatedDocuments?: number;
  estimatedTime?: number;
}
```

## Angular Services

### 1. Entity Service
```typescript
@Injectable({ providedIn: 'root' })
export class EntityService {
  private entityCache = new Map<string, Entity[]>();
  private entitySubject = new BehaviorSubject<EntityState>({});
  
  constructor(private http: HttpClient) {}
  
  async loadEntities(type: string): Promise<void> {
    if (this.entityCache.has(type)) {
      return;
    }
    
    const response = await this.http.get<EntitySearchResponse>(
      `/api/entities?type=${type}`
    ).toPromise();
    
    this.entityCache.set(type, response.entities);
    this.entitySubject.next({
      ...this.entitySubject.value,
      [type]: response.entities
    });
  }
  
  searchEntities(searchText: string, type: string): Observable<EntityGroup[]> {
    return this.http.get<EntitySearchResponse>(
      `/api/entities?type=${type}&search=${encodeURIComponent(searchText)}`
    ).pipe(
      map(response => this.groupEntities(response.entities))
    );
  }
  
  private groupEntities(entities: Entity[]): EntityGroup[] {
    // Group by confidence levels or alphabetically
    const groups = new Map<string, Entity[]>();
    
    entities.forEach(entity => {
      const groupKey = entity.confidence > 0.9 ? 'Exact Matches' : 'Similar Matches';
      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey).push(entity);
    });
    
    return Array.from(groups.entries()).map(([type, entities]) => ({
      type,
      entities
    }));
  }
}
```

### 2. Query Builder Service
```typescript
@Injectable({ providedIn: 'root' })
export class QueryBuilderService {
  
  initializeQuery(template: QueryTemplate): StructuredQuery {
    return {
      template: template.id,
      operation: template.operation,
      target: template.target,
      filters: {},
      displayNames: {},
      options: template.defaultOptions || {}
    };
  }
  
  updateQuery(query: StructuredQuery, field: string, value: any): StructuredQuery {
    const updated = { ...query };
    
    // Handle entity fields specially
    if (value && typeof value === 'object' && 'normalizedName' in value) {
      updated.filters[field] = value.normalizedName;
      updated.displayNames[value.normalizedName] = value.displayName;
    } else {
      updated.filters[field] = value;
    }
    
    return updated;
  }
  
  toNaturalLanguage(query: StructuredQuery): string {
    const parts = [];
    
    switch (query.operation) {
      case 'comparison':
        if (query.target === 'clauses') {
          parts.push('Compare');
          parts.push(query.filters.clause_type);
          parts.push('clauses');
          
          if (query.filters.contracting_party) {
            const display = query.displayNames[query.filters.contracting_party];
            parts.push(`in contracts with ${display}`);
          }
          
          if (query.filters.contractor_parties?.length) {
            const contractors = query.filters.contractor_parties
              .map(c => query.displayNames[c] || c)
              .join(' and ');
            parts.push(`between ${contractors}`);
          }
        }
        break;
        
      case 'search':
        parts.push('Find contracts');
        // Build natural language from filters
        break;
        
      case 'analysis':
        parts.push('Analyze contract');
        // Add specifics
        break;
    }
    
    return parts.join(' ');
  }
  
  validateQuery(query: StructuredQuery): ValidationResult {
    const errors = [];
    const warnings = [];
    
    // Template-specific validation
    switch (query.template) {
      case 'COMPARE_CLAUSES':
        if (!query.filters.clause_type) {
          errors.push('Clause type is required');
        }
        if (!query.filters.contractor_parties || 
            query.filters.contractor_parties.length < 2) {
          errors.push('At least 2 contractors required for comparison');
        }
        break;
        
      // Other validations...
    }
    
    return { valid: errors.length === 0, errors, warnings };
  }
}
```

### 3. Backend API Service
```typescript
@Injectable({ providedIn: 'root' })
export class BackendApiService {
  constructor(private http: HttpClient) {}
  
  executeStructuredQuery(query: StructuredQuery): Observable<StructuredQueryResponse> {
    return this.http.post<StructuredQueryResponse>(
      '/api/query/structured',
      query
    ).pipe(
      tap(response => console.log('Query executed:', response)),
      catchError(this.handleError)
    );
  }
  
  validateQuery(query: StructuredQuery): Observable<QueryValidationResponse> {
    return this.http.post<QueryValidationResponse>(
      '/api/query/validate',
      query
    );
  }
  
  private handleError(error: HttpErrorResponse) {
    console.error('API Error:', error);
    return throwError(() => new Error(error.message));
  }
}
```

## State Management (NgRx)

```typescript
// State
interface QueryBuilderState {
  selectedTemplate: QueryTemplate | null;
  currentQuery: StructuredQuery | null;
  entities: {
    [type: string]: Entity[];
  };
  queryResults: any[] | null;
  loading: boolean;
  error: string | null;
}

// Actions
export const selectTemplate = createAction(
  '[Query Builder] Select Template',
  props<{ template: QueryTemplate }>()
);

export const updateQuery = createAction(
  '[Query Builder] Update Query',
  props<{ field: string; value: any }>()
);

export const executeQuery = createAction(
  '[Query Builder] Execute Query'
);

export const querySuccess = createAction(
  '[Query Builder] Query Success',
  props<{ results: any[] }>()
);

// Effects
@Injectable()
export class QueryBuilderEffects {
  executeQuery$ = createEffect(() =>
    this.actions$.pipe(
      ofType(executeQuery),
      withLatestFrom(this.store.select(selectCurrentQuery)),
      switchMap(([_, query]) =>
        this.apiService.executeStructuredQuery(query).pipe(
          map(response => querySuccess({ results: response.results })),
          catchError(error => of(queryFailure({ error: error.message })))
        )
      )
    )
  );
  
  constructor(
    private actions$: Actions,
    private store: Store,
    private apiService: BackendApiService
  ) {}
}
```

## User Experience Flow

### Flow 1: Compare Indemnification Clauses
1. User clicks "Compare Clauses" template
2. Selects "Indemnification" from clause dropdown
3. Types "West" → Autocomplete shows "The Westervelt Company (25 contracts)"
4. Selects Westervelt as contracting party (optional)
5. Types contractor names → Multi-select with autocomplete
6. Sees natural language preview: "Compare Indemnification clauses in contracts with The Westervelt Company between ContractorA LLC and ContractorB Inc"
7. Clicks Execute
8. Results show side-by-side clause comparison

### Flow 2: Find Contracts
1. User clicks "Find Contracts" template
2. Selects multiple filters:
   - Governing Law: Alabama
   - Date Range: 2024
   - Contract Type: MSA
3. Preview shows: "Find Master Services Agreements governed by Alabama law from 2024"
4. Execute returns list of matching contracts

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- Angular module structure
- Basic template selector
- Entity service with caching
- Mock API service

### Phase 2: Entity Selection (Week 2)
- Entity autocomplete component
- Fuzzy matching integration
- Display name handling
- Entity statistics display

### Phase 3: Query Building (Week 3)
- Template-specific forms
- Query validation
- Natural language generation
- Query preview component

### Phase 4: Backend Integration (Week 4)
- API endpoint implementation
- Structured query processing
- Result formatting
- Error handling

### Phase 5: Polish & Testing (Week 5)
- Loading states
- Error handling
- Unit tests
- E2E tests
- Performance optimization

## Technical Considerations

### Performance
- Cache entity lists on app initialization
- Debounce autocomplete searches
- Lazy load result components
- Virtual scrolling for large result sets

### Accessibility
- ARIA labels for all form controls
- Keyboard navigation support
- Screen reader friendly
- High contrast mode support

### Security
- Sanitize user inputs
- Validate on both frontend and backend
- Rate limiting for API calls
- Audit logging for queries

### Testing Strategy
```typescript
// Component Testing
describe('EntitySelectorComponent', () => {
  it('should filter entities based on search text', () => {
    // Test fuzzy matching
  });
  
  it('should emit selected entity with both normalized and display names', () => {
    // Test entity selection
  });
});

// Service Testing
describe('QueryBuilderService', () => {
  it('should generate correct natural language from structured query', () => {
    // Test NL generation
  });
  
  it('should validate queries based on template requirements', () => {
    // Test validation
  });
});

// E2E Testing
describe('Query Builder Flow', () => {
  it('should build and execute a clause comparison query', () => {
    // Full flow test
  });
});
```

## Conclusion

This guided query builder approach will:

1. **Simplify Complex Queries**: Transform complex analytical queries into step-by-step selections
2. **Ensure Data Quality**: Use normalized entities consistently while displaying friendly names
3. **Improve Success Rate**: Structured queries are easier for backend to process accurately
4. **Enhance User Experience**: Progressive disclosure and visual feedback guide users
5. **Enable Analytics**: Track which templates and entities are most used

The implementation focuses on making the complex simple while maintaining the power to perform sophisticated contract analysis queries.