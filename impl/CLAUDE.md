# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a microservices-based knowledge graph system with AI capabilities, consisting of:
- **graph_app**: Java/Spring Boot graph service using Apache Jena for RDF/SPARQL (port 8001)
- **web_app**: Python/FastAPI web application with Azure OpenAI integration (port 8000)

## Development Commands

### Java Graph Service (graph_app/)

#### Build and Package
```bash
# Windows
.\build.ps1

# Linux/macOS
./build.sh
```

#### Run Locally
```bash
# Windows
.\graph_app.ps1

# Linux/macOS
./graph_app.sh

# Or directly with Gradle
gradle bootRun
```

#### Testing
```bash
# Run all tests
gradle test

# Run specific test class
gradle test --tests "*GraphTests"
```

#### Console Tasks
```bash
gradle consoleAppInvokeGraphBuilder    # Build graph from source
gradle consoleAppGenerateArtifacts     # Generate ontology artifacts  
gradle consoleAppPostSparqlAddDocuments # Add documents via SPARQL
```

### Contract Entity System

#### Overview
The contract entity system manages and tracks entities extracted from contracts:
- **Contractor Parties**: Companies/individuals performing work
- **Contracting Parties**: Companies/individuals initiating contracts
- **Governing Laws**: Jurisdictions that govern contracts
- **Contract Types**: MSA, NDA, SOW, etc.

#### Architecture: Option 2 - Separate Entity Collections
Uses separate CosmosDB containers for each entity type:
- `contractor_parties` container
- `contracting_parties` container
- `governing_laws` container
- `contract_types` container
- `config` container holds the reference document

#### Key Components

**ContractEntitiesService** (`web_app/src/services/contract_entities_service.py`):
- Manages entity catalogs with in-memory caching
- Provides fuzzy matching (85% threshold) for entity identification
- Tracks entity statistics (contract counts, total values)
- TODO: Implement sophisticated matching (phonetic, n-gram, ML-based)

**ContractStrategyBuilder** (`web_app/src/services/contract_strategy_builder.py`):
- Determines query strategy (db/vector/graph) for contract queries
- Identifies entities in natural language queries
- TODO: Implement NER, semantic similarity, query templates

**Entity Building During Contract Loading**:
- `main_contracts.py` automatically builds entity catalogs during ingestion
- Entities are updated in real-time as contracts are loaded
- Statistics are tracked per entity (contract count, total value)

#### Entity Normalization
- Converts to lowercase
- Removes special characters
- Replaces spaces with underscores
- Removes common suffixes (LLC, Inc, Corp) for matching

#### Usage

```bash
# Load contracts with entity building
python main_contracts.py load_contracts caig contracts data/contracts 999999
```

Entities are automatically:
1. Extracted from contract metadata
2. Normalized for consistent storage
3. Stored in separate containers
4. Cached in memory for fast lookup
5. Persisted after all contracts are loaded

### Python Web App (web_app/)

#### Setup Virtual Environment
```bash
# Windows
.\venv.ps1

# Linux/macOS
./venv.sh
```

#### Run Locally
```bash
# Windows
.\web_app.ps1

# Linux/macOS
./web_app.sh
```

#### Testing
```bash
# Windows
.\tests.ps1

# Run individual test
pytest -v tests/test_config_service.py

# With coverage
pytest -v --cov=src/ --cov-report html tests/
```

#### Entity Initialization
The web app automatically initializes `ContractEntitiesService` for contract entity management at startup.

#### Contract Data Loading
```bash
# Load contracts with embeddings generated at runtime
python main_contracts.py load_contracts caig contracts data/contracts 999999

# Preprocess contracts to generate and save embeddings
python main_contracts.py preprocess_contracts data/contracts data/contracts/processed

# Load preprocessed contracts (faster, no embedding generation)
python main_contracts.py load_contracts caig contracts data/contracts/processed 999999
```

### Docker Deployment

```bash
# Run both services
docker compose -f docker-compose.yml up

# Stop services
docker compose -f docker-compose.yml down
```

## Configuration

### Environment Setup
1. Copy `set-caig-env-vars-sample.ps1` to `set-caig-env-vars.ps1` and configure with your Azure resources
2. For Java: Copy `graph_app/example-override.properties` to `graph_app/.override.properties`
3. For Python: Create `web_app/.env` file based on `web_app/dotenv_example`

### Key Environment Variables
- `CAIG_GRAPH_SOURCE_TYPE`: One of `cosmos_nosql`, `rdf_file`, or `json_docs_file`
- `CAIG_COSMOSDB_NOSQL_URI`: Azure CosmosDB endpoint
- `CAIG_COSMOSDB_NOSQL_KEY`: CosmosDB access key
- `CAIG_AZURE_OPENAI_URL`: Azure OpenAI endpoint
- `CAIG_AZURE_OPENAI_KEY`: Azure OpenAI key
- `CAIG_AZURE_OPENAI_COMPLETIONS_DEP`: Deployment name for completions model
- `CAIG_AZURE_OPENAI_EMBEDDINGS_DEP`: Deployment name for embeddings model

## Architecture

### Graph Service (Java/Jena)
- **AppGraph**: Singleton in-memory RDF graph using Apache Jena
- **AppGraphBuilder**: Factory for building graph from CosmosDB, RDF files, or JSON documents
- **GraphRestController**: REST endpoints for SPARQL queries and graph operations
- **Triple Builders**:
  - `ContractsGraphTriplesBuilder`: For contract/contractor/governing law relationships
- **Data Sources**: 
  - `cosmos_nosql`: Live CosmosDB connection
  - `rdf_file`: Local RDF file for development
  - `json_docs_file`: Cached CosmosDB documents

### Web Application (Python/FastAPI)
- **AiService**: Azure OpenAI integration for completions and embeddings
- **CosmosNoSQLService**: CosmosDB client for document operations and vector search
  - ⚠️ **CRITICAL**: See `web_app/COSMOSDB_SERVICE_PATTERNS.md` for correct usage patterns
  - Must use `query_items()`, `parameterized_query()`, `upsert_item()` (NOT `query_documents()`, `get_document()`, `upsert_document()`)
  - Must call `set_container()` before every operation
- **RAGDataService**: RAG (Retrieval Augmented Generation) orchestration
- **AiConversation**: Conversation state management with context
- **ContractEntitiesService**: Contract entity extraction and processing
- **OntologyService**: OWL ontology management and SPARQL generation
- **ClauseLibraryService**: Clause library management with AI-powered comparison and vector search

### API Endpoints

#### Graph Service (port 8001)
- `GET /ping`: Health check
- `GET /health`: Detailed health status
- `GET /ontology`: Returns OWL/XML ontology
- `POST /sparql_query`: Execute SPARQL SELECT queries
- `POST /sparql_update`: Execute SPARQL UPDATE operations
- `POST /sparql_bom_query`: Bill of Materials query for visualizations
- `POST /add_documents`: Add CosmosDB documents to graph
- `GET /reload_graph`: Reload graph from source (dev only)

#### Web Application (port 8000)
- `GET /`: Home page
- `GET /sparql_console`: SPARQL query interface
- `GET /gen_sparql_console`: AI-powered SPARQL generation
- `GET /conv_ai_console`: Conversational AI interface
- `GET /vector_search_console`: Vector search interface
- `POST /gen_sparql`: Generate SPARQL from natural language
- `POST /invoke_sparql`: Execute SPARQL query
- `POST /vector_search`: Perform vector similarity search
- `POST /ai_completion`: Get AI completions
- `POST /liveness`: Application health check

## Testing Strategy

### Graph Service
- Unit tests with JUnit and Spring Boot Test
- Mock external dependencies when testing graph operations
- Test data in `graph_app/data/` and `graph_app/samples/`

### Web Application
- pytest framework with async support
- Tests use live services (CosmosDB, Azure OpenAI) - ensure environment configured
- Coverage target: 80% for unit tests, 70% for integration
- Test data in `web_app/samples/`

### Playwright E2E Testing
- Angular frontend: E2E tests using Playwright TypeScript
- Python backend: API tests using Playwright Python with pytest
- Test directory: `query-builder/e2e/` and `web_app/tests/`
- Run tests: `npm run test:e2e` (Angular) and `pytest tests/api` (Python)

## Code Testability Guidelines for Playwright

**CRITICAL**: All code written for this project MUST follow these testability patterns to ensure Playwright tests can reliably interact with and verify the application.

### 1. Use Test IDs for All Interactive Elements

**MANDATORY**: Add `data-testid` attributes to ALL interactive elements and important content areas.

#### Angular Components - Required Test IDs

**Buttons and Actions:**
```html
<!-- ALL buttons must have data-testid -->
<button data-testid="upload-contract-btn" (click)="upload()">Upload</button>
<button data-testid="submit-query-btn" (click)="submit()">Submit Query</button>
<button data-testid="compare-contracts-btn" (click)="compare()">Compare</button>
<button [attr.data-testid]="'delete-btn-' + item.id" (click)="delete(item)">Delete</button>
```

**Form Inputs:**
```html
<!-- ALL inputs, selects, and textareas must have data-testid -->
<input data-testid="search-input" [(ngModel)]="searchQuery" />
<input data-testid="question-input" [(ngModel)]="question" />
<select data-testid="contract-type-select" [(ngModel)]="contractType">
<textarea data-testid="clause-text-input" [(ngModel)]="clauseText">
<input type="checkbox" [attr.data-testid]="'contract-checkbox-' + contract.id">
<input type="radio" data-testid="mode-realtime" name="mode" value="realtime">
```

**Navigation and Links:**
```html
<!-- ALL navigation elements must have data-testid -->
<a data-testid="contracts-nav-link" routerLink="/contracts">Contracts</a>
<a data-testid="compare-nav-link" routerLink="/compare-contracts">Compare</a>
```

**Lists and Tables:**
```html
<!-- Tables and lists must have container test IDs -->
<table data-testid="contracts-table">
  <tr *ngFor="let contract of contracts"
      [attr.data-testid]="'contract-row-' + contract.id">
    <td [attr.data-testid]="'contract-name-' + contract.id">{{ contract.name }}</td>
  </tr>
</table>

<div data-testid="job-list">
  <div *ngFor="let job of jobs"
       [attr.data-testid]="'job-card-' + job.id"
       [attr.data-status]="job.status">
  </div>
</div>
```

**Dialogs and Modals:**
```html
<!-- Dialogs must have test IDs for container, close button, and actions -->
<div data-testid="contract-details-dialog">
  <button data-testid="close-dialog-btn" (click)="close()">×</button>
  <div data-testid="dialog-content">...</div>
  <button data-testid="dialog-confirm-btn">Confirm</button>
  <button data-testid="dialog-cancel-btn">Cancel</button>
</div>
```

**Status Indicators and Results:**
```html
<!-- Results containers and status elements must have test IDs -->
<div data-testid="comparison-results">
  <div data-testid="clause-termination-result">...</div>
  <span data-testid="similarity-score">85%</span>
</div>

<div data-testid="query-results">
  <div data-testid="query-answer">{{ answer }}</div>
</div>

<div data-testid="job-status">{{ job.status }}</div>
<div data-testid="progress-bar">
  <div data-testid="progress-fill" [style.width.%]="progress"></div>
</div>
```

**Error Messages and Toasts:**
```html
<!-- Error messages must be testable -->
<div data-testid="error-message" *ngIf="errorMessage">{{ errorMessage }}</div>
<div data-testid="toast-error" class="toast toast-error">{{ message }}</div>
<div data-testid="toast-success" class="toast toast-success">{{ message }}</div>
```

### 2. Expose Component State for Testing

**REQUIRED**: Use `@HostBinding` to expose loading, error, and ready states.

```typescript
import { Component, HostBinding } from '@angular/core';

@Component({
  selector: 'app-contracts-list',
  templateUrl: './contracts-list.component.html'
})
export class ContractsListComponent {
  // Expose loading state
  @HostBinding('attr.data-loading')
  get isLoading() { return this.loading; }

  // Expose error state
  @HostBinding('attr.data-error')
  get hasError() { return !!this.errorMessage; }

  // Expose ready state (when component has loaded data)
  @HostBinding('attr.data-ready')
  get isReady() { return this.dataLoaded && !this.loading; }

  // Internal state
  private loading = false;
  private dataLoaded = false;
  errorMessage: string | null = null;

  async loadContracts() {
    this.loading = true;
    this.errorMessage = null;

    try {
      this.contracts = await this.contractService.getContracts().toPromise();
      this.dataLoaded = true;
    } catch (error) {
      this.errorMessage = error.message;
    } finally {
      this.loading = false;
    }
  }
}
```

**Tests can wait for states:**
```typescript
// Wait for loading to complete
await page.waitForSelector('[data-loading="false"]');

// Wait for data to be ready
await page.waitForSelector('[data-ready="true"]');

// Check for error state
const hasError = await page.locator('[data-error="true"]').isVisible();
```

### 3. Use Stable Identifiers (NOT Random or Index-Based)

**REQUIRED**: Always use stable, predictable identifiers.

#### Good Examples (Use Entity IDs):
```html
<!-- Use contract.id, not array index -->
<div *ngFor="let contract of contracts; trackBy: trackById"
     [attr.data-testid]="'contract-card-' + contract.id">

<!-- Use job.job_id, not array index -->
<div *ngFor="let job of jobs"
     [attr.data-testid]="'job-' + job.job_id"
     [attr.data-status]="job.status">

<!-- Use clause.id, not random ID -->
<div [attr.data-testid]="'clause-' + clause.id">
```

```typescript
// TrackBy function using ID
trackById(index: number, item: any): string {
  return item.id;
}
```

#### Bad Examples (DO NOT USE):
```html
<!-- ❌ DO NOT use array index -->
<div *ngFor="let contract of contracts; let i = index"
     [attr.data-testid]="'contract-' + i">

<!-- ❌ DO NOT use random IDs -->
<div [attr.data-testid]="'modal-' + Math.random()">

<!-- ❌ DO NOT use timestamps for IDs -->
<div [attr.data-testid]="'item-' + Date.now()">
```

### 4. Make Async Operations Testable

**REQUIRED**: All async operations must have testable state transitions.

#### Loading States:
```typescript
async performOperation() {
  // 1. Set loading state
  this.loading = true;
  this.operationInProgress = true;

  try {
    // 2. Perform operation
    const result = await this.service.doSomething();

    // 3. Set success state
    this.operationComplete = true;
    this.result = result;

  } catch (error) {
    // 4. Set error state
    this.operationFailed = true;
    this.errorMessage = error.message;

  } finally {
    // 5. Clear loading state
    this.loading = false;
    this.operationInProgress = false;
  }
}
```

#### Background Jobs:
```typescript
// Jobs must expose status for testing
<div [attr.data-testid]="'job-' + job.id"
     [attr.data-status]="job.status"
     [attr.data-progress]="job.progress.percentage">
  <span data-testid="job-status">{{ job.status }}</span>
  <span data-testid="job-progress">{{ job.progress.percentage }}%</span>
</div>
```

**Tests can wait for completion:**
```typescript
// Wait for job to complete
await page.waitForSelector('[data-testid="job-123"][data-status="completed"]', {
  timeout: 60000
});

// Wait for progress to reach 100%
await page.waitForSelector('[data-progress="100"]');
```

### 5. Backend API Testability

#### Add Health Check Endpoints:
```python
# web_app/web_app.py
from datetime import datetime

@app.get("/api/health")
async def health_check():
    """Health check endpoint for testing."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

#### Add Test Data Endpoints (Test Environment Only):
```python
import os

if os.getenv("ENVIRONMENT") in ["development", "test"]:

    @app.post("/api/test/reset")
    async def reset_test_data():
        """Reset database to clean state for testing."""
        # Clean up test data
        return {"status": "reset", "timestamp": datetime.now().isoformat()}

    @app.post("/api/test/seed")
    async def seed_test_data(data_type: str):
        """Seed test data."""
        if data_type == "contracts":
            # Create sample contracts
            pass
        return {"status": "seeded", "type": data_type}

    @app.get("/api/test/contracts/{contract_id}")
    async def get_test_contract(contract_id: str):
        """Get test contract for verification."""
        # Return contract data
        pass
```

#### Use Predictable IDs in Test Mode:
```python
def generate_id(entity_type: str, data: dict) -> str:
    """Generate ID - predictable in test mode, random in production."""
    if os.getenv("ENVIRONMENT") == "test":
        # Use deterministic hash for testing
        data_str = json.dumps(data, sort_keys=True)
        hash_val = hashlib.md5(data_str.encode()).hexdigest()[:8]
        return f"test_{entity_type}_{hash_val}"
    else:
        # Use UUID in production
        return f"{entity_type}_{uuid.uuid4()}"
```

#### Make Background Jobs Synchronous in Tests:
```python
class BackgroundWorker:
    def __init__(self):
        self.sync_mode = os.getenv("TEST_SYNC_MODE") == "true"

    async def submit_job(self, job):
        if self.sync_mode:
            # Execute immediately for testing
            return await self._execute_job(job)
        else:
            # Queue for background execution
            await self._queue_job(job)
```

### 6. Angular Service Testability

#### Make Services Injectable with Test Doubles:
```typescript
// Provide service at component level for easy mocking
@Component({
  providers: [ContractService]  // Can be overridden in tests
})
export class ContractsListComponent {
  constructor(private contractService: ContractService) {}
}
```

#### Return Observables for Async Operations:
```typescript
// Good - Returns Observable
getContracts(): Observable<Contract[]> {
  return this.http.get<Contract[]>('/api/contracts');
}

// Tests can mock responses
const mockService = {
  getContracts: () => of([{ id: '1', name: 'Test Contract' }])
};
```

### 7. Common Patterns and Anti-Patterns

#### ✅ DO: Use Semantic Test IDs
```html
<button data-testid="submit-comparison-btn">Submit</button>
<div data-testid="comparison-results">...</div>
<span data-testid="error-message">{{ error }}</span>
```

#### ❌ DON'T: Rely on CSS Classes or Structure
```html
<!-- Don't rely on this for testing -->
<button class="btn btn-primary submit">Submit</button>
<div class="results mt-4">...</div>
```

#### ✅ DO: Expose Meaningful State
```typescript
@HostBinding('attr.data-state')
get currentState() {
  if (this.loading) return 'loading';
  if (this.error) return 'error';
  if (this.success) return 'success';
  return 'idle';
}
```

#### ❌ DON'T: Hide State in Private Variables
```typescript
// Don't do this - tests can't see private state
private loading = false;
private error = null;
```

#### ✅ DO: Use Stable, Predictable Timing
```typescript
// Good - predictable delay
setTimeout(() => this.showMessage(), 1000);

// Tests can wait reliably
await page.waitForTimeout(1000);
await page.waitForSelector('[data-testid="message"]');
```

#### ❌ DON'T: Use Random Delays
```typescript
// Don't do this - tests will be flaky
setTimeout(() => this.showMessage(), Math.random() * 1000);
```

### 8. Test ID Naming Conventions

Follow these conventions for consistency:

**Buttons:** `{action}-btn`
```html
<button data-testid="upload-btn">Upload</button>
<button data-testid="submit-query-btn">Submit Query</button>
<button data-testid="cancel-btn">Cancel</button>
```

**Inputs:** `{field-name}-input`
```html
<input data-testid="search-input" />
<input data-testid="question-input" />
<textarea data-testid="clause-text-input" />
```

**Selects/Dropdowns:** `{field-name}-select`
```html
<select data-testid="contract-type-select">
<select data-testid="comparison-mode-select">
```

**Lists/Tables:** `{entity}-list` or `{entity}-table`
```html
<div data-testid="contracts-list">
<table data-testid="jobs-table">
```

**List Items:** `{entity}-{id}` or `{entity}-row-{id}`
```html
<div [attr.data-testid]="'contract-' + contract.id">
<tr [attr.data-testid]="'job-row-' + job.id">
```

**Dialogs/Modals:** `{name}-dialog` or `{name}-modal`
```html
<div data-testid="contract-details-dialog">
<div data-testid="confirmation-modal">
```

**Results/Content:** `{context}-results` or `{context}-content`
```html
<div data-testid="comparison-results">
<div data-testid="query-results">
<div data-testid="dialog-content">
```

**Status/State:** `{context}-status` or `{context}-state`
```html
<span data-testid="job-status">
<div data-testid="loading-state">
```

### 9. Checklist for New Components

Before completing any new component, verify:

- [ ] All buttons have `data-testid` attributes
- [ ] All form inputs have `data-testid` attributes
- [ ] All navigation links have `data-testid` attributes
- [ ] List/table containers have `data-testid` attributes
- [ ] List/table items have dynamic `data-testid` using entity ID
- [ ] Component exposes loading state via `@HostBinding('attr.data-loading')`
- [ ] Component exposes error state via `@HostBinding('attr.data-error')`
- [ ] Component exposes ready state via `@HostBinding('attr.data-ready')`
- [ ] Async operations set testable state flags
- [ ] No random IDs or array indices in test IDs
- [ ] TrackBy functions use entity IDs, not indices
- [ ] Background jobs expose status via `[attr.data-status]`
- [ ] Error messages have `data-testid` attributes
- [ ] Success messages/toasts have `data-testid` attributes

### 10. Documentation References

For detailed implementation guides, see:
- **PLAYWRIGHT_IMPLEMENTATION_GUIDE.md**: Comprehensive Playwright setup and patterns
- **PLAYWRIGHT_QUICK_START.md**: Step-by-step implementation guide
- **Playwright Docs**: https://playwright.dev/docs/best-practices

## Development Notes

### Requirements
- **Java**: 21+ (for graph service)
- **Gradle**: 8.11 or 8.12
- **Python**: 3.12.9 (for web app)
- **Docker**: For containerized deployment

### Graph Data Flow
1. Data loaded from CosmosDB/files into Apache Jena RDF model at startup
2. SPARQL queries processed against in-memory graph
3. Graph can be reloaded via `/reload_graph` endpoint (dev only)
4. Updates persisted back to CosmosDB when using `cosmos_nosql` source

### AI Integration Flow
1. User query → Entity extraction → Vector embeddings
2. Vector search in CosmosDB → Retrieve relevant documents
3. Context + documents → Azure OpenAI → Generated response
4. Conversation history maintained in CosmosDB

### Common Development Tasks

#### Add New RDF Triples
1. Update ontology in `ontologies/contracts.owl`
2. Add triples via SPARQL UPDATE or reload from data source
3. Reload graph via endpoint or restart service

#### Update Vector Index Policy
1. Modify policy in `web_app/config/cosmosdb_nosql_contract_parents_index_policy*.json`
2. Apply to CosmosDB container via Azure Portal or CLI
3. Restart web app to use new policy

#### Debug SPARQL Queries
1. Use `/sparql_console` in web app for interactive testing
2. Enable debug logging: Set `CAIG_LOG_LEVEL=debug`
3. Check `tmp/` directory for captured query/response JSON files

### Performance Considerations
- Graph service maintains entire RDF model in memory - monitor heap usage
- Use `CAIG_GRAPH_SOURCE_TYPE=json_docs_file` for faster development iteration
- Vector search performance depends on CosmosDB index configuration
- Web app uses hypercorn with configurable workers via `WEB_CONCURRENCY`