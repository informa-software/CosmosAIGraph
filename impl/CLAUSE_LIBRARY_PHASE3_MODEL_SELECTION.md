# Clause Library - Phase 3A: Model Selection Implementation

## Overview

Implement user-selectable LLM model choice throughout the application, allowing users to choose between GPT-4.1 (primary) and GPT-4.1-mini (secondary) for all AI operations.

**Prerequisites**: Phase 2 completed with dual-model comparison capability

**Duration**: 3-4 days

**Goal**: Provide users with model selection controls in UI and API, with preference storage and cost tracking

---

## Architecture Overview

### Model Selection Flow

```
User Selection → Preference Storage → API Call → Service Layer → AI Service → Azure OpenAI
```

### Components to Update

1. **Backend API**: Add `model_selection` parameter to all AI endpoints
2. **Service Layer**: Update all AI service methods to accept model parameter
3. **Frontend UI**: Add model selection controls (dropdown/radio buttons)
4. **User Preferences**: Store default model preference
5. **Monitoring**: Track model usage and costs
6. **Documentation**: Update API docs and user guides

---

## Phase 3A.1: Backend API Updates (Day 1)

### 1.1 Update Clause Library Router

**File**: `web_app/routers/clause_library_router.py`

**Changes**:

#### Add Model Selection to Compare Endpoint

```python
@router.post("/compare")
async def compare_clause_endpoint(
    request: CompareClauseRequest,
    model_selection: str = "primary",  # NEW: default to primary
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """
    Compare contract text against library clause.

    Args:
        request: Comparison request with clause_id and contract_text
        model_selection: "primary" (GPT-4.1) or "secondary" (GPT-4.1-mini)
    """
    # Validate model_selection
    if model_selection not in ["primary", "secondary"]:
        raise HTTPException(
            status_code=400,
            detail="model_selection must be 'primary' or 'secondary'"
        )

    comparison = await service.compare_clause(
        request=request,
        user_email="api_user@example.com",  # TODO: Get from auth
        use_cache=True,
        model_selection=model_selection
    )
    return comparison
```

#### Add Model Selection to Suggest Endpoint

The suggest endpoint uses embeddings, which currently uses the primary model only. Update if secondary model supports embeddings.

**Current behavior**: Embeddings always use primary model (not cost-effective to change)
**Recommendation**: Keep embeddings on primary model, only allow model selection for completion operations

### 1.2 Create User Preferences API

**File**: `web_app/routers/user_preferences_router.py` (NEW)

```python
"""
API endpoints for user preferences management.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService

router = APIRouter(prefix="/api/user-preferences", tags=["user-preferences"])


class ModelPreference(BaseModel):
    """Model preference settings."""
    default_model: str  # "primary" or "secondary"
    auto_select: bool = False  # Automatically select based on contract characteristics
    cost_optimization: bool = False  # Prefer secondary model when quality is similar


class UserPreferences(BaseModel):
    """User preferences model."""
    id: Optional[str] = None
    type: str = "user_preferences"
    user_email: str
    model_preference: ModelPreference
    created_date: str
    modified_date: str


@router.get("/model-preference")
async def get_model_preference(
    user_email: str,
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """Get user's model preference."""
    cosmos.set_container("user_preferences")

    # Query for user preferences
    query = "SELECT * FROM c WHERE c.type = 'user_preferences' AND c.user_email = @email"
    params = [{"name": "@email", "value": user_email}]

    results = await cosmos.parameterized_query(query, params)

    if results:
        return results[0]

    # Return default preferences
    return UserPreferences(
        user_email=user_email,
        model_preference=ModelPreference(
            default_model="primary",
            auto_select=False,
            cost_optimization=False
        ),
        created_date="",
        modified_date=""
    )


@router.post("/model-preference")
async def save_model_preference(
    user_email: str,
    preference: ModelPreference,
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """Save user's model preference."""
    from datetime import datetime

    cosmos.set_container("user_preferences")

    # Check if preferences exist
    query = "SELECT * FROM c WHERE c.type = 'user_preferences' AND c.user_email = @email"
    params = [{"name": "@email", "value": user_email}]
    results = await cosmos.parameterized_query(query, params)

    now = datetime.utcnow().isoformat()

    if results:
        # Update existing
        prefs = results[0]
        prefs["model_preference"] = preference.model_dump()
        prefs["modified_date"] = now
    else:
        # Create new
        prefs = UserPreferences(
            id=f"prefs_{user_email}",
            user_email=user_email,
            model_preference=preference,
            created_date=now,
            modified_date=now
        ).model_dump(mode='json', exclude_none=True)

    await cosmos.upsert_item(prefs)
    return {"message": "Preferences saved successfully", "preferences": prefs}


def get_cosmos_service():
    """Dependency to get CosmosDB service."""
    from src.services.cosmos_nosql_service import CosmosNoSQLService
    cosmos = CosmosNoSQLService()
    # Initialize in endpoint
    return cosmos
```

### 1.3 Update Main App to Register Router

**File**: `web_app/web_app.py`

```python
# Add import
from routers.user_preferences_router import router as user_prefs_router

# Register router
app.include_router(user_prefs_router)
```

### 1.4 Create CosmosDB Container Setup Script

**File**: `web_app/setup_user_preferences_container.py` (NEW)

```python
"""
Setup script for user_preferences container in CosmosDB.
"""

import asyncio
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService

async def setup_container():
    """Create user_preferences container with index policy."""
    cosmos = CosmosNoSQLService()
    await cosmos.initialize()

    db_name = ConfigService.graph_source_db()
    container_name = "user_preferences"

    # Index policy optimized for user preference queries
    index_policy = {
        "indexingMode": "consistent",
        "automatic": True,
        "includedPaths": [
            {"path": "/*"}
        ],
        "excludedPaths": [
            {"path": "/\"_etag\"/?"}
        ]
    }

    print(f"Creating container: {container_name}")
    print(f"Database: {db_name}")

    # Create container
    # Note: This assumes you have access to create containers
    # You may need to do this via Azure Portal or CLI

    print("\nContainer configuration:")
    print(f"  Partition key: /user_email")
    print(f"  Indexing: consistent")
    print("\nPlease create this container manually via Azure Portal or use:")
    print(f"  az cosmosdb sql container create \\")
    print(f"    --account-name YOUR_ACCOUNT \\")
    print(f"    --database-name {db_name} \\")
    print(f"    --name {container_name} \\")
    print(f"    --partition-key-path /user_email \\")
    print(f"    --throughput 400")

    await cosmos._client.close()

if __name__ == "__main__":
    asyncio.run(setup_container())
```

**Deliverables - Day 1**:
- ✅ Updated compare endpoint with model_selection parameter
- ✅ Created user preferences API router
- ✅ Container setup script for user preferences
- ✅ API tests for preferences endpoints

---

## Phase 3A.2: Frontend UI Components (Day 2)

### 2.1 Create Model Selection Component

**File**: `query-builder/src/app/shared/components/model-selector/model-selector.ts`

```typescript
import { Component, EventEmitter, Input, Output } from '@angular/core';

export interface ModelOption {
  value: string;
  label: string;
  description: string;
  badge?: string;
}

@Component({
  selector: 'app-model-selector',
  templateUrl: './model-selector.html',
  styleUrls: ['./model-selector.scss']
})
export class ModelSelectorComponent {
  @Input() selectedModel: string = 'primary';
  @Input() showDescription: boolean = true;
  @Input() disabled: boolean = false;
  @Output() modelChange = new EventEmitter<string>();

  models: ModelOption[] = [
    {
      value: 'primary',
      label: 'GPT-4.1',
      description: 'Best quality, comprehensive analysis',
      badge: 'Recommended'
    },
    {
      value: 'secondary',
      label: 'GPT-4.1-mini',
      description: 'Good quality, faster and more cost-effective',
      badge: 'Cost Saver'
    }
  ];

  onModelChange(value: string): void {
    this.selectedModel = value;
    this.modelChange.emit(value);
  }

  getModelInfo(value: string): ModelOption | undefined {
    return this.models.find(m => m.value === value);
  }
}
```

**File**: `query-builder/src/app/shared/components/model-selector/model-selector.html`

```html
<div class="model-selector">
  <label class="model-selector-label">AI Model Selection</label>

  <div class="model-options">
    <div *ngFor="let model of models"
         class="model-option"
         [class.selected]="selectedModel === model.value"
         [class.disabled]="disabled">

      <input
        type="radio"
        [id]="'model-' + model.value"
        [name]="'model-selection'"
        [value]="model.value"
        [checked]="selectedModel === model.value"
        [disabled]="disabled"
        (change)="onModelChange(model.value)">

      <label [for]="'model-' + model.value" class="model-label">
        <div class="model-header">
          <span class="model-name">{{ model.label }}</span>
          <span *ngIf="model.badge" class="model-badge">{{ model.badge }}</span>
        </div>
        <p *ngIf="showDescription" class="model-description">
          {{ model.description }}
        </p>
      </label>
    </div>
  </div>
</div>
```

**File**: `query-builder/src/app/shared/components/model-selector/model-selector.scss`

```scss
.model-selector {
  margin: 16px 0;

  .model-selector-label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #333;
  }

  .model-options {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .model-option {
    flex: 1;
    min-width: 200px;
    position: relative;

    input[type="radio"] {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }

    .model-label {
      display: block;
      padding: 16px;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
      background: white;

      &:hover {
        border-color: #2196F3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
    }

    &.selected .model-label {
      border-color: #2196F3;
      background: #E3F2FD;
    }

    &.disabled .model-label {
      opacity: 0.6;
      cursor: not-allowed;

      &:hover {
        border-color: #e0e0e0;
        box-shadow: none;
      }
    }

    .model-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }

    .model-name {
      font-weight: 600;
      color: #333;
    }

    .model-badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      background: #4CAF50;
      color: white;
      font-weight: 500;
    }

    .model-description {
      font-size: 13px;
      color: #666;
      margin: 0;
      line-height: 1.4;
    }
  }
}
```

### 2.2 Create User Preferences Service

**File**: `query-builder/src/app/shared/services/user-preferences.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';

export interface ModelPreference {
  default_model: string;
  auto_select: boolean;
  cost_optimization: boolean;
}

export interface UserPreferences {
  id?: string;
  type: string;
  user_email: string;
  model_preference: ModelPreference;
  created_date?: string;
  modified_date?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UserPreferencesService {
  private apiUrl = '/api/user-preferences';
  private modelPreferenceSubject = new BehaviorSubject<string>('primary');

  public modelPreference$ = this.modelPreferenceSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadPreferences();
  }

  private loadPreferences(): void {
    const userEmail = this.getCurrentUserEmail();
    this.getModelPreference(userEmail).subscribe(
      prefs => {
        if (prefs && prefs.model_preference) {
          this.modelPreferenceSubject.next(prefs.model_preference.default_model);
        }
      },
      error => console.error('Error loading preferences:', error)
    );
  }

  getModelPreference(userEmail: string): Observable<UserPreferences> {
    return this.http.get<UserPreferences>(
      `${this.apiUrl}/model-preference?user_email=${userEmail}`
    );
  }

  saveModelPreference(
    userEmail: string,
    preference: ModelPreference
  ): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/model-preference?user_email=${userEmail}`,
      preference
    ).pipe(
      tap(() => {
        this.modelPreferenceSubject.next(preference.default_model);
      })
    );
  }

  getCurrentModel(): string {
    return this.modelPreferenceSubject.value;
  }

  private getCurrentUserEmail(): string {
    // TODO: Get from authentication service
    return 'user@example.com';
  }
}
```

### 2.3 Update Contract Workbench Component

**File**: `query-builder/src/app/contract-workbench/contract-workbench.html`

Add model selector before comparison section:

```html
<!-- Add after contract selection, before comparison section -->
<div class="model-selection-section">
  <app-model-selector
    [(selectedModel)]="selectedModel"
    [showDescription]="true"
    (modelChange)="onModelChange($event)">
  </app-model-selector>
</div>

<!-- Update comparison section to show model being used -->
<div class="comparison-section">
  <h3>Clause Comparison</h3>
  <p class="model-info">Using: <strong>{{ getModelDisplayName() }}</strong></p>
  <!-- Rest of comparison UI -->
</div>
```

**File**: `query-builder/src/app/contract-workbench/contract-workbench.ts`

```typescript
export class ContractWorkbenchComponent implements OnInit {
  selectedModel: string = 'primary';

  constructor(
    private contractService: ContractService,
    private userPrefsService: UserPreferencesService
  ) {}

  ngOnInit(): void {
    // Load user's preferred model
    this.userPrefsService.modelPreference$.subscribe(model => {
      this.selectedModel = model;
    });
  }

  onModelChange(model: string): void {
    console.log('Model changed to:', model);
    // Model will be used in next comparison
  }

  getModelDisplayName(): string {
    return this.selectedModel === 'primary' ? 'GPT-4.1' : 'GPT-4.1-mini';
  }

  async compareClause(): Promise<void> {
    // Pass selectedModel to API call
    const result = await this.contractService.compareClause(
      this.selectedClauseId,
      this.contractText,
      this.selectedModel  // NEW: Pass model selection
    );
    // Handle result...
  }
}
```

### 2.4 Update Contract Service

**File**: `query-builder/src/app/contract-workbench/services/contract.service.ts`

```typescript
export class ContractService {
  async compareClause(
    clauseId: string,
    contractText: string,
    modelSelection: string = 'primary'  // NEW parameter
  ): Promise<ClauseComparison> {
    const response = await fetch('/api/clause-library/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clause_id: clauseId,
        contract_text: contractText,
        contract_id: this.currentContractId,
        model_selection: modelSelection  // NEW: Include in request
      })
    });

    if (!response.ok) {
      throw new Error(`Comparison failed: ${response.statusText}`);
    }

    return await response.json();
  }
}
```

**Deliverables - Day 2**:
- ✅ Model selector component (reusable)
- ✅ User preferences service
- ✅ Updated contract workbench with model selection
- ✅ Updated contract service to pass model parameter

---

## Phase 3A.3: User Preferences UI (Day 3)

### 3.1 Create Settings/Preferences Page

**File**: `query-builder/src/app/settings/settings.component.ts`

```typescript
import { Component, OnInit } from '@angular/core';
import { UserPreferencesService, ModelPreference } from '../shared/services/user-preferences.service';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss']
})
export class SettingsComponent implements OnInit {
  preferences: ModelPreference = {
    default_model: 'primary',
    auto_select: false,
    cost_optimization: false
  };

  saving: boolean = false;
  saveSuccess: boolean = false;
  saveError: string = '';

  constructor(private userPrefsService: UserPreferencesService) {}

  ngOnInit(): void {
    this.loadPreferences();
  }

  loadPreferences(): void {
    const userEmail = 'user@example.com'; // TODO: Get from auth
    this.userPrefsService.getModelPreference(userEmail).subscribe(
      prefs => {
        if (prefs && prefs.model_preference) {
          this.preferences = prefs.model_preference;
        }
      },
      error => console.error('Error loading preferences:', error)
    );
  }

  savePreferences(): void {
    this.saving = true;
    this.saveSuccess = false;
    this.saveError = '';

    const userEmail = 'user@example.com'; // TODO: Get from auth
    this.userPrefsService.saveModelPreference(userEmail, this.preferences).subscribe(
      () => {
        this.saving = false;
        this.saveSuccess = true;
        setTimeout(() => this.saveSuccess = false, 3000);
      },
      error => {
        this.saving = false;
        this.saveError = 'Failed to save preferences: ' + error.message;
      }
    );
  }

  onModelChange(model: string): void {
    this.preferences.default_model = model;
  }
}
```

**File**: `query-builder/src/app/settings/settings.component.html`

```html
<div class="settings-container">
  <h2>User Preferences</h2>

  <div class="preferences-section">
    <h3>Default AI Model</h3>
    <p class="section-description">
      Choose which AI model to use by default for clause comparisons.
      You can override this choice on individual comparisons.
    </p>

    <app-model-selector
      [(selectedModel)]="preferences.default_model"
      [showDescription]="true"
      (modelChange)="onModelChange($event)">
    </app-model-selector>

    <div class="model-comparison-info">
      <h4>Model Comparison</h4>
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Feature</th>
            <th>GPT-4.1</th>
            <th>GPT-4.1-mini</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Quality</td>
            <td>⭐⭐⭐⭐⭐</td>
            <td>⭐⭐⭐⭐</td>
          </tr>
          <tr>
            <td>Speed</td>
            <td>⚡⚡⚡</td>
            <td>⚡⚡⚡⚡⚡</td>
          </tr>
          <tr>
            <td>Cost</td>
            <td>$$$</td>
            <td>$$</td>
          </tr>
          <tr>
            <td>Best For</td>
            <td>Critical contracts, detailed analysis</td>
            <td>Routine contracts, high volume</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="preferences-section">
    <h3>Advanced Options</h3>

    <div class="option">
      <label>
        <input
          type="checkbox"
          [(ngModel)]="preferences.auto_select"
          disabled>
        <span>Auto-select model based on contract characteristics</span>
        <span class="badge coming-soon">Coming Soon</span>
      </label>
      <p class="option-description">
        Automatically choose the best model based on contract value, complexity, and risk level.
      </p>
    </div>

    <div class="option">
      <label>
        <input
          type="checkbox"
          [(ngModel)]="preferences.cost_optimization"
          disabled>
        <span>Optimize for cost</span>
        <span class="badge coming-soon">Coming Soon</span>
      </label>
      <p class="option-description">
        Prefer GPT-4.1-mini when quality difference is minimal (based on your comparison history).
      </p>
    </div>
  </div>

  <div class="actions">
    <button
      class="btn btn-primary"
      (click)="savePreferences()"
      [disabled]="saving">
      <span *ngIf="!saving">Save Preferences</span>
      <span *ngIf="saving">Saving...</span>
    </button>

    <div *ngIf="saveSuccess" class="alert alert-success">
      ✓ Preferences saved successfully
    </div>

    <div *ngIf="saveError" class="alert alert-error">
      ✗ {{ saveError }}
    </div>
  </div>
</div>
```

### 3.2 Add Route for Settings

**File**: `query-builder/src/app/app.routes.ts`

```typescript
import { SettingsComponent } from './settings/settings.component';

export const routes: Routes = [
  // ... existing routes
  {
    path: 'settings',
    component: SettingsComponent,
    data: { title: 'Settings' }
  }
];
```

### 3.3 Add Navigation Link

**File**: `query-builder/src/index.html` or main navigation

```html
<nav>
  <!-- Other nav items -->
  <a routerLink="/settings" routerLinkActive="active">
    <i class="icon-settings"></i> Settings
  </a>
</nav>
```

**Deliverables - Day 3**:
- ✅ Settings page with model preferences
- ✅ Model comparison table in UI
- ✅ Save/load functionality
- ✅ Navigation to settings

---

## Phase 3A.4: Cost Tracking & Analytics (Day 4)

### 4.1 Add Usage Tracking to Service

**File**: `web_app/src/services/clause_library_service.py`

Add usage tracking after each comparison:

```python
async def compare_clause(
    self,
    request: CompareClauseRequest,
    user_email: str,
    use_cache: bool = True,
    model_selection: str = "primary"
) -> ClauseComparison:
    # ... existing code ...

    # Track usage
    await self._track_model_usage(
        user_email=user_email,
        model=deployment,
        operation="clause_comparison",
        tokens=response.get("usage", {}).get("completion_tokens", 0),
        elapsed_time=time.time() - start_time
    )

    # ... rest of code ...

async def _track_model_usage(
    self,
    user_email: str,
    model: str,
    operation: str,
    tokens: int,
    elapsed_time: float
):
    """Track model usage for analytics and cost estimation."""
    from datetime import datetime

    usage_record = {
        "id": str(uuid.uuid4()),
        "type": "model_usage",
        "user_email": user_email,
        "model": model,
        "operation": operation,
        "tokens": tokens,
        "elapsed_time": elapsed_time,
        "timestamp": datetime.utcnow().isoformat(),
        "estimated_cost": self._estimate_cost(model, tokens)
    }

    self.cosmos.set_container("model_usage")
    await self.cosmos.upsert_item(usage_record)

def _estimate_cost(self, model: str, tokens: int) -> float:
    """Estimate cost based on model and token count."""
    # Pricing as of 2025 (update with actual pricing)
    pricing = {
        "gpt-4.1": 0.00003,  # per token
        "gpt-4.1-mini": 0.00001  # per token
    }

    rate = pricing.get(model, 0.00003)
    return tokens * rate
```

### 4.2 Create Usage Analytics Endpoint

**File**: `web_app/routers/analytics_router.py` (NEW)

```python
"""
API endpoints for usage analytics and cost tracking.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime, timedelta
from src.services.cosmos_nosql_service import CosmosNoSQLService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/usage-summary")
async def get_usage_summary(
    user_email: str,
    days: int = Query(30, ge=1, le=365),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """Get usage summary for the specified time period."""
    cosmos.set_container("model_usage")

    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    query = """
    SELECT
        c.model,
        COUNT(1) as total_operations,
        SUM(c.tokens) as total_tokens,
        SUM(c.estimated_cost) as total_cost,
        AVG(c.elapsed_time) as avg_time
    FROM c
    WHERE c.type = 'model_usage'
      AND c.user_email = @email
      AND c.timestamp >= @start_date
    GROUP BY c.model
    """

    params = [
        {"name": "@email", "value": user_email},
        {"name": "@start_date", "value": start_date}
    ]

    results = await cosmos.parameterized_query(query, params)

    return {
        "period_days": days,
        "start_date": start_date,
        "models": results,
        "total_cost": sum(r.get("total_cost", 0) for r in results),
        "total_operations": sum(r.get("total_operations", 0) for r in results)
    }


@router.get("/cost-savings")
async def get_cost_savings(
    user_email: str,
    days: int = Query(30, ge=1, le=365),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """Calculate potential cost savings if secondary model was used."""
    cosmos.set_container("model_usage")

    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # Get all primary model usage
    query = """
    SELECT
        SUM(c.tokens) as total_tokens,
        SUM(c.estimated_cost) as actual_cost
    FROM c
    WHERE c.type = 'model_usage'
      AND c.user_email = @email
      AND c.model = 'gpt-4.1'
      AND c.timestamp >= @start_date
    """

    params = [
        {"name": "@email", "value": user_email},
        {"name": "@start_date", "value": start_date}
    ]

    results = await cosmos.parameterized_query(query, params)

    if results and results[0]["total_tokens"]:
        actual_cost = results[0]["actual_cost"]
        total_tokens = results[0]["total_tokens"]

        # Calculate what it would cost with secondary model
        secondary_rate = 0.00001
        potential_cost = total_tokens * secondary_rate
        savings = actual_cost - potential_cost
        savings_pct = (savings / actual_cost) * 100 if actual_cost > 0 else 0

        return {
            "actual_cost": actual_cost,
            "potential_cost": potential_cost,
            "savings": savings,
            "savings_percentage": savings_pct,
            "recommendation": "Consider using GPT-4.1-mini for routine comparisons" if savings_pct > 20 else "Current usage is optimal"
        }

    return {
        "actual_cost": 0,
        "potential_cost": 0,
        "savings": 0,
        "savings_percentage": 0,
        "recommendation": "No usage data available"
    }


def get_cosmos_service():
    """Dependency to get CosmosDB service."""
    from src.services.cosmos_nosql_service import CosmosNoSQLService
    cosmos = CosmosNoSQLService()
    return cosmos
```

### 4.3 Create Analytics Dashboard Component

**File**: `query-builder/src/app/analytics/analytics-dashboard.component.ts`

```typescript
import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

interface UsageSummary {
  period_days: number;
  models: Array<{
    model: string;
    total_operations: number;
    total_tokens: number;
    total_cost: number;
    avg_time: number;
  }>;
  total_cost: number;
  total_operations: number;
}

@Component({
  selector: 'app-analytics-dashboard',
  templateUrl: './analytics-dashboard.component.html',
  styleUrls: ['./analytics-dashboard.component.scss']
})
export class AnalyticsDashboardComponent implements OnInit {
  usageSummary: UsageSummary | null = null;
  costSavings: any = null;
  selectedPeriod: number = 30;
  loading: boolean = false;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    this.loading = true;
    const userEmail = 'user@example.com'; // TODO: Get from auth

    // Load usage summary
    this.http.get<UsageSummary>(
      `/api/analytics/usage-summary?user_email=${userEmail}&days=${this.selectedPeriod}`
    ).subscribe(
      data => {
        this.usageSummary = data;
        this.loading = false;
      },
      error => {
        console.error('Error loading analytics:', error);
        this.loading = false;
      }
    );

    // Load cost savings
    this.http.get(
      `/api/analytics/cost-savings?user_email=${userEmail}&days=${this.selectedPeriod}`
    ).subscribe(
      data => this.costSavings = data,
      error => console.error('Error loading cost savings:', error)
    );
  }

  onPeriodChange(days: number): void {
    this.selectedPeriod = days;
    this.loadAnalytics();
  }
}
```

**File**: `query-builder/src/app/analytics/analytics-dashboard.component.html`

```html
<div class="analytics-container">
  <h2>Usage Analytics</h2>

  <div class="period-selector">
    <label>Time Period:</label>
    <select [(ngModel)]="selectedPeriod" (change)="onPeriodChange(selectedPeriod)">
      <option [value]="7">Last 7 days</option>
      <option [value]="30">Last 30 days</option>
      <option [value]="90">Last 90 days</option>
    </select>
  </div>

  <div *ngIf="loading" class="loading">Loading analytics...</div>

  <div *ngIf="!loading && usageSummary" class="analytics-content">
    <!-- Summary Cards -->
    <div class="summary-cards">
      <div class="card">
        <div class="card-title">Total Operations</div>
        <div class="card-value">{{ usageSummary.total_operations }}</div>
      </div>

      <div class="card">
        <div class="card-title">Total Cost</div>
        <div class="card-value">${{ usageSummary.total_cost.toFixed(2) }}</div>
      </div>

      <div class="card" *ngIf="costSavings">
        <div class="card-title">Potential Savings</div>
        <div class="card-value savings">
          ${{ costSavings.savings.toFixed(2) }}
          <span class="percentage">({{ costSavings.savings_percentage.toFixed(1) }}%)</span>
        </div>
      </div>
    </div>

    <!-- Model Breakdown -->
    <div class="model-breakdown">
      <h3>Usage by Model</h3>
      <table class="usage-table">
        <thead>
          <tr>
            <th>Model</th>
            <th>Operations</th>
            <th>Tokens</th>
            <th>Avg Time</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let model of usageSummary.models">
            <td>{{ model.model }}</td>
            <td>{{ model.total_operations }}</td>
            <td>{{ model.total_tokens | number }}</td>
            <td>{{ model.avg_time.toFixed(2) }}s</td>
            <td>${{ model.total_cost.toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Cost Savings Recommendation -->
    <div *ngIf="costSavings" class="recommendation">
      <h3>Cost Optimization</h3>
      <div class="recommendation-card">
        <p><strong>Recommendation:</strong> {{ costSavings.recommendation }}</p>
        <p>By using GPT-4.1-mini for routine comparisons, you could save approximately
          <strong>${{ costSavings.savings.toFixed(2) }}</strong> per month.</p>
      </div>
    </div>
  </div>
</div>
```

**Deliverables - Day 4**:
- ✅ Usage tracking in service layer
- ✅ Analytics API endpoints
- ✅ Analytics dashboard component
- ✅ Cost savings calculator

---

## Testing Checklist

### Backend Testing
- [ ] Test compare endpoint with model_selection parameter
- [ ] Verify preferences save/load correctly
- [ ] Test usage tracking records correctly
- [ ] Verify cost calculations are accurate
- [ ] Test analytics endpoints with various date ranges

### Frontend Testing
- [ ] Model selector component renders correctly
- [ ] Selected model persists across page reloads
- [ ] Preferences save successfully
- [ ] Analytics dashboard displays data correctly
- [ ] Cost savings calculations display

### Integration Testing
- [ ] End-to-end: Select model → Compare clause → See result with correct model
- [ ] Verify cache keys are different for different models
- [ ] Test that secondary model is actually used when selected
- [ ] Verify usage is tracked for both models

---

## Documentation Updates

### API Documentation
- Update OpenAPI/Swagger docs with model_selection parameter
- Document user preferences endpoints
- Document analytics endpoints

### User Guide
- Add "Choosing the Right Model" section
- Explain cost vs quality trade-offs
- Provide decision matrix for model selection

### Developer Guide
- Document model selection architecture
- Explain how to add new models in the future
- Document usage tracking system

---

## Deployment Steps

1. **Database Setup**:
   ```bash
   python web_app/setup_user_preferences_container.py
   python web_app/setup_model_usage_container.py
   ```

2. **Backend Deployment**:
   ```bash
   # Test updated endpoints
   pytest web_app/tests/test_model_selection.py

   # Deploy backend
   # (your deployment process)
   ```

3. **Frontend Deployment**:
   ```bash
   cd query-builder
   npm run build
   # Deploy frontend build
   ```

4. **Verification**:
   - Test model selection in UI
   - Verify preferences save/load
   - Check analytics dashboard
   - Monitor usage tracking

---

## Success Criteria

- ✅ Users can select model for each comparison
- ✅ Default model preference is saved and restored
- ✅ Analytics show usage breakdown by model
- ✅ Cost savings recommendations are accurate
- ✅ Performance: Model selection adds <100ms overhead
- ✅ All existing functionality still works

---

## Future Enhancements (Phase 3B+)

1. **Smart Model Selection**:
   - Auto-select based on contract value/complexity
   - ML model to predict best model for each contract

2. **Cost Budgets**:
   - Set monthly cost limits
   - Alerts when approaching budget
   - Auto-switch to cheaper model near limit

3. **A/B Testing**:
   - Run comparisons with both models
   - Compare quality systematically
   - Build quality confidence scores

4. **Custom Models**:
   - Support for additional Azure OpenAI deployments
   - User-defined model configurations
   - Fine-tuned model support

---

## Timeline Summary

- **Day 1**: Backend API updates (compare endpoint, preferences API)
- **Day 2**: Frontend UI components (model selector, updated workbench)
- **Day 3**: Settings page (preferences UI, save/load)
- **Day 4**: Analytics & cost tracking (usage tracking, dashboard)

**Total**: 4 days for complete model selection implementation

---

## Next Phase

After completing Phase 3A, proceed with **Phase 3B: Frontend Development** (main clause library UI as outlined in original plan).
