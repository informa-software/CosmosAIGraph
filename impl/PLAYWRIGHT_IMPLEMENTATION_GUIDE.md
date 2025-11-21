# Playwright Implementation Guide

Complete guide for adding Playwright testing to the Contract Intelligence Workbench.

---

## Table of Contents

1. [Overview](#overview)
2. [Angular Frontend Setup](#angular-frontend-setup)
3. [Python Backend Setup](#python-backend-setup)
4. [Code Design for Testability](#code-design-for-testability)
5. [Test Architecture](#test-architecture)
6. [Example Tests](#example-tests)
7. [CI/CD Integration](#cicd-integration)
8. [Best Practices](#best-practices)

---

## Overview

### What is Playwright?

Playwright is a modern end-to-end testing framework that:
- Tests across all major browsers (Chrome, Firefox, Safari, Edge)
- Provides reliable, auto-waiting test execution
- Supports parallel test execution
- Includes built-in test reporting
- Works with both frontend and backend applications

### Testing Strategy

**Angular Frontend:**
- E2E tests for user workflows
- Component interaction tests
- Visual regression tests
- API mocking for isolated tests

**Python Backend:**
- API endpoint tests
- Integration tests
- Database operation tests
- Background job tests

---

## Angular Frontend Setup

### Step 1: Install Playwright

```bash
cd query-builder

# Install Playwright
npm install --save-dev @playwright/test

# Install browsers
npx playwright install

# Install Angular-specific tools (optional but recommended)
npm install --save-dev @angular-devkit/build-angular
```

### Step 2: Initialize Playwright Configuration

```bash
# Generate Playwright config
npx playwright init
```

This creates `playwright.config.ts`. Update it for Angular:

```typescript
// query-builder/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',

  // Maximum time one test can run
  timeout: 30 * 1000,

  // Test execution settings
  expect: {
    timeout: 5000
  },

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }]
  ],

  // Shared settings for all the projects below
  use: {
    // Base URL for tests
    baseURL: 'https://localhost:4200',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Accept self-signed certificates (for localhost HTTPS)
    ignoreHTTPSErrors: true,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile viewports (optional)
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // Run your local dev server before starting the tests
  webServer: {
    command: 'npm run start',
    url: 'https://localhost:4200',
    reuseExistingServer: !process.env.CI,
    ignoreHTTPSErrors: true,
    timeout: 120 * 1000,
  },
});
```

### Step 3: Create Test Directory Structure

```bash
cd query-builder
mkdir -p e2e/fixtures
mkdir -p e2e/pages
mkdir -p e2e/tests
```

**Recommended Structure:**
```
query-builder/
├── e2e/
│   ├── fixtures/
│   │   ├── test-data.ts          # Test data generators
│   │   ├── mock-contracts.json    # Mock contract data
│   │   └── api-mocks.ts           # API response mocks
│   ├── pages/
│   │   ├── base.page.ts           # Base page object
│   │   ├── contracts-list.page.ts
│   │   ├── compare-contracts.page.ts
│   │   ├── query-contracts.page.ts
│   │   ├── clause-library.page.ts
│   │   ├── compliance.page.ts
│   │   └── jobs.page.ts
│   ├── tests/
│   │   ├── contracts/
│   │   │   ├── upload.spec.ts
│   │   │   ├── list.spec.ts
│   │   │   └── details.spec.ts
│   │   ├── comparison/
│   │   │   ├── clause-comparison.spec.ts
│   │   │   └── full-comparison.spec.ts
│   │   ├── query/
│   │   │   ├── natural-language.spec.ts
│   │   │   └── batch-query.spec.ts
│   │   └── workflows/
│   │       ├── contract-upload-workflow.spec.ts
│   │       └── compliance-workflow.spec.ts
│   └── playwright.config.ts
└── package.json
```

### Step 4: Update package.json Scripts

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:chromium": "playwright test --project=chromium",
    "test:e2e:report": "playwright show-report",
    "test:e2e:codegen": "playwright codegen https://localhost:4200"
  }
}
```

### Step 5: Add Test Selectors to Angular Components

Update your Angular components to include `data-testid` attributes for reliable test selectors:

**Before:**
```html
<button class="btn-primary" (click)="uploadContract()">Upload</button>
```

**After:**
```html
<button
  class="btn-primary"
  data-testid="upload-contract-btn"
  (click)="uploadContract()">
  Upload
</button>
```

**Key Areas to Add Test IDs:**
- All buttons and interactive elements
- Form inputs and dropdowns
- Navigation links
- List items and cards
- Dialog/modal elements
- Status indicators
- Error messages

---

## Python Backend Setup

### Step 1: Install Playwright for Python

```bash
cd web_app

# Activate virtual environment
.\venv.ps1  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install Playwright
pip install playwright pytest-playwright pytest-asyncio

# Install browsers
playwright install

# Update requirements.txt
pip freeze > requirements.txt
```

### Step 2: Create Pytest Configuration

Create `pytest.ini` in the `web_app` directory:

```ini
# web_app/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test* *Tests
python_functions = test_*
asyncio_mode = auto
markers =
    e2e: End-to-end tests
    integration: Integration tests
    api: API endpoint tests
    slow: Slow running tests
    smoke: Smoke tests for critical paths
```

### Step 3: Create Test Directory Structure

```bash
cd web_app
mkdir -p tests/e2e
mkdir -p tests/api
mkdir -p tests/fixtures
mkdir -p tests/utils
```

**Recommended Structure:**
```
web_app/
├── tests/
│   ├── conftest.py                # Pytest fixtures and configuration
│   ├── fixtures/
│   │   ├── contracts.py           # Contract test fixtures
│   │   ├── users.py               # User test fixtures
│   │   └── api_responses.py       # Mock API responses
│   ├── utils/
│   │   ├── api_client.py          # API test helper
│   │   └── test_data.py           # Test data generators
│   ├── api/
│   │   ├── test_contracts.py      # Contract API tests
│   │   ├── test_comparison.py     # Comparison API tests
│   │   ├── test_query.py          # Query API tests
│   │   ├── test_compliance.py     # Compliance API tests
│   │   └── test_jobs.py           # Background jobs tests
│   ├── e2e/
│   │   ├── test_upload_workflow.py
│   │   ├── test_comparison_workflow.py
│   │   └── test_compliance_workflow.py
│   └── pytest.ini
├── src/
└── requirements.txt
```

### Step 4: Create Base Test Configuration

Create `conftest.py`:

```python
# web_app/tests/conftest.py
import pytest
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import AsyncGenerator

# Backend URL
BASE_API_URL = "https://localhost:8000"
FRONTEND_URL = "https://localhost:4200"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    """Launch browser for the entire test session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture(scope="function")
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a new browser context for each test."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
    )
    yield context
    await context.close()

@pytest.fixture(scope="function")
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a new page for each test."""
    page = await context.new_page()
    yield page
    await page.close()

@pytest.fixture(scope="function")
async def api_client(page: Page):
    """Create an API client for testing backend endpoints."""
    from tests.utils.api_client import APIClient
    return APIClient(page, BASE_API_URL)

@pytest.fixture(scope="session")
def test_contract_pdf():
    """Provide path to a test contract PDF."""
    return "tests/fixtures/sample_contract.pdf"

@pytest.fixture(scope="function")
async def authenticated_page(page: Page) -> Page:
    """Provide an authenticated page (if authentication is implemented)."""
    # TODO: Implement authentication if needed
    # await page.goto(f"{FRONTEND_URL}/login")
    # await page.fill('[data-testid="username"]', 'test_user')
    # await page.fill('[data-testid="password"]', 'test_pass')
    # await page.click('[data-testid="login-btn"]')
    # await page.wait_for_url(f"{FRONTEND_URL}/contracts")
    return page
```

### Step 5: Update requirements.txt

Add to your `requirements.txt`:

```txt
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-playwright==0.4.3
playwright==1.40.0
pytest-cov==4.1.0
```

---

## Code Design for Testability

### Angular Frontend - Best Practices

#### 1. Use Semantic Test Selectors

**Good:**
```html
<!-- Use data-testid for test selectors -->
<button data-testid="submit-query-btn" (click)="submitQuery()">Submit</button>
<input data-testid="question-input" [(ngModel)]="question" />
<div data-testid="results-container">{{ results }}</div>
<span data-testid="job-status-{{job.id}}">{{ job.status }}</span>
```

**Bad:**
```html
<!-- Don't rely on classes or structure -->
<button class="btn btn-primary submit" (click)="submitQuery()">Submit</button>
<input name="q" [(ngModel)]="question" />
<div class="results mt-4">{{ results }}</div>
```

#### 2. Expose Component State for Testing

```typescript
// contracts-list.component.ts
export class ContractsListComponent {
  // Expose loading state for tests
  @HostBinding('attr.data-loading')
  get isLoading() { return this.loading; }

  // Expose error state
  @HostBinding('attr.data-error')
  get hasError() { return !!this.errorMessage; }

  // Make state queryable
  private loading = false;
  errorMessage: string | null = null;

  // Add data-testid to critical elements
  ngAfterViewInit() {
    // Component is ready for testing
    this.componentReady = true;
  }
}
```

#### 3. Use Stable Identifiers

```typescript
// Use stable IDs, not array indices
<div *ngFor="let contract of contracts; trackBy: trackById">
  <div [attr.data-testid]="'contract-card-' + contract.id">
    {{ contract.title }}
  </div>
</div>

trackById(index: number, contract: Contract): string {
  return contract.id;
}
```

#### 4. Make Async Operations Testable

```typescript
// Add data attributes that indicate loading/complete states
async loadContracts(): Promise<void> {
  this.loading = true;
  try {
    this.contracts = await this.contractService.getContracts().toPromise();
    this.loading = false;
    this.loaded = true;  // Test can wait for this
  } catch (error) {
    this.loading = false;
    this.error = true;   // Test can check for this
  }
}
```

#### 5. Avoid Random or Time-Based IDs

**Bad:**
```typescript
// Random IDs make tests flaky
this.modalId = `modal-${Math.random()}`;
this.timestamp = Date.now();
```

**Good:**
```typescript
// Predictable IDs
this.modalId = `modal-${this.contractId}`;
this.timestamp = this.contract.created_date;
```

### Python Backend - Best Practices

#### 1. Make Endpoints Testable

```python
# web_app/web_app.py

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint for testing."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/test/reset")
async def reset_test_data():
    """Reset test data (only enabled in test environment)."""
    if os.getenv("ENVIRONMENT") == "test":
        # Reset database to known state
        return {"status": "reset"}
    raise HTTPException(status_code=403, detail="Only available in test environment")
```

#### 2. Use Dependency Injection

```python
# Make services injectable for mocking
class ContractService:
    def __init__(self, db_service, ai_service):
        self.db = db_service
        self.ai = ai_service

    async def process_contract(self, contract_data):
        # Service logic
        pass

# In endpoint
@app.post("/api/contracts")
async def create_contract(
    request: ContractRequest,
    contract_service: ContractService = Depends(get_contract_service)
):
    return await contract_service.process_contract(request)
```

#### 3. Add Test Hooks

```python
# Add endpoints that help with testing
if os.getenv("ENVIRONMENT") == "test":
    @app.post("/api/test/seed-data")
    async def seed_test_data(data_type: str):
        """Seed test data for E2E tests."""
        if data_type == "contracts":
            # Create test contracts
            pass
        return {"status": "seeded"}

    @app.delete("/api/test/cleanup")
    async def cleanup_test_data():
        """Clean up test data."""
        # Remove all test data
        return {"status": "cleaned"}
```

#### 4. Return Predictable IDs

```python
# Use deterministic IDs in test mode
def generate_contract_id(contract_data):
    if os.getenv("ENVIRONMENT") == "test":
        # Use hash of filename for predictable IDs
        return f"test_contract_{hash(contract_data['filename'])}"
    else:
        return f"contract_{uuid.uuid4()}"
```

#### 5. Make Background Jobs Synchronous in Tests

```python
# background_worker.py
class BackgroundWorker:
    def __init__(self, sync_mode=False):
        self.sync_mode = sync_mode or os.getenv("TEST_SYNC_MODE") == "true"

    async def submit_job(self, job):
        if self.sync_mode:
            # Execute immediately for testing
            return await self.execute_job(job)
        else:
            # Queue for background execution
            await self.queue_job(job)
```

---

## Test Architecture

### Page Object Model (POM)

Use Page Objects to encapsulate page interactions:

```typescript
// query-builder/e2e/pages/base.page.ts
import { Page, Locator } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto(path: string = '') {
    await this.page.goto(`https://localhost:4200${path}`);
  }

  async waitForLoadingComplete() {
    await this.page.waitForSelector('[data-loading="false"]', {
      state: 'attached'
    });
  }

  async isErrorDisplayed(): Promise<boolean> {
    return await this.page.locator('[data-error="true"]').isVisible();
  }
}
```

```typescript
// query-builder/e2e/pages/contracts-list.page.ts
import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class ContractsListPage extends BasePage {
  readonly uploadButton: Locator;
  readonly searchInput: Locator;
  readonly contractsTable: Locator;
  readonly paginationInfo: Locator;

  constructor(page: Page) {
    super(page);
    this.uploadButton = page.locator('[data-testid="upload-contract-btn"]');
    this.searchInput = page.locator('[data-testid="search-input"]');
    this.contractsTable = page.locator('[data-testid="contracts-table"]');
    this.paginationInfo = page.locator('[data-testid="pagination-info"]');
  }

  async goto() {
    await super.goto('/contracts');
    await this.waitForLoadingComplete();
  }

  async uploadContract(filePath: string) {
    await this.uploadButton.click();
    const fileInput = this.page.locator('input[type="file"]');
    await fileInput.setInputFiles(filePath);
  }

  async searchContracts(query: string) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
    await this.waitForLoadingComplete();
  }

  async getContractCount(): Promise<number> {
    const text = await this.paginationInfo.textContent();
    const match = text?.match(/Total: (\d+)/);
    return match ? parseInt(match[1]) : 0;
  }

  async clickContract(contractId: string) {
    await this.page.locator(`[data-testid="contract-card-${contractId}"]`).click();
  }
}
```

### API Test Helpers

```python
# web_app/tests/utils/api_client.py
from playwright.async_api import Page
from typing import Dict, Any, Optional

class APIClient:
    """Helper class for testing API endpoints."""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request."""
        url = f"{self.base_url}{endpoint}"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"

        response = await self.page.request.get(url)
        return await response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request."""
        response = await self.page.request.post(
            f"{self.base_url}{endpoint}",
            data=data
        )
        return await response.json()

    async def upload_file(self, endpoint: str, file_path: str, field_name: str = "file"):
        """Upload file to endpoint."""
        with open(file_path, "rb") as f:
            response = await self.page.request.post(
                f"{self.base_url}{endpoint}",
                multipart={
                    field_name: {
                        "name": file_path,
                        "mimeType": "application/pdf",
                        "buffer": f.read()
                    }
                }
            )
        return await response.json()

    async def wait_for_job_completion(self, job_id: str, timeout: int = 60000):
        """Wait for background job to complete."""
        end_time = self.page.context.browser.now() + timeout

        while self.page.context.browser.now() < end_time:
            job = await self.get(f"/api/jobs/{job_id}", {"user_id": "system"})

            if job["status"] in ["completed", "failed", "cancelled"]:
                return job

            await self.page.wait_for_timeout(1000)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout}ms")
```

---

## Example Tests

### Angular E2E Test Example

```typescript
// query-builder/e2e/tests/contracts/upload.spec.ts
import { test, expect } from '@playwright/test';
import { ContractsListPage } from '../../pages/contracts-list.page';
import { JobsPage } from '../../pages/jobs.page';
import path from 'path';

test.describe('Contract Upload', () => {
  let contractsPage: ContractsListPage;
  let jobsPage: JobsPage;

  test.beforeEach(async ({ page }) => {
    contractsPage = new ContractsListPage(page);
    jobsPage = new JobsPage(page);
    await contractsPage.goto();
  });

  test('should upload a contract successfully', async ({ page }) => {
    // Arrange
    const testFile = path.join(__dirname, '../../fixtures/sample_contract.pdf');
    const initialCount = await contractsPage.getContractCount();

    // Act
    await contractsPage.uploadContract(testFile);

    // Assert - Upload job created
    await jobsPage.goto();
    await expect(page.locator('[data-testid="job-type-CONTRACT_UPLOAD"]').first())
      .toBeVisible();

    // Wait for job completion
    await page.waitForSelector('[data-testid="job-status-completed"]', {
      timeout: 60000
    });

    // Verify contract appears in list
    await contractsPage.goto();
    const newCount = await contractsPage.getContractCount();
    expect(newCount).toBe(initialCount + 1);
  });

  test('should display upload progress', async ({ page }) => {
    const testFile = path.join(__dirname, '../../fixtures/sample_contract.pdf');

    await contractsPage.uploadContract(testFile);
    await jobsPage.goto();

    // Check progress bar is visible
    await expect(page.locator('[data-testid="progress-bar"]')).toBeVisible();

    // Check progress percentage is displayed
    const progressText = await page.locator('[data-testid="progress-percentage"]').textContent();
    expect(progressText).toMatch(/\d+%/);
  });

  test('should handle upload errors gracefully', async ({ page }) => {
    // Mock API to return error
    await page.route('**/api/contracts/upload', route => {
      route.fulfill({
        status: 400,
        body: JSON.stringify({ error: 'Invalid file format' })
      });
    });

    const testFile = path.join(__dirname, '../../fixtures/invalid_file.txt');
    await contractsPage.uploadContract(testFile);

    // Check error toast is displayed
    await expect(page.locator('[data-testid="toast-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="toast-error"]'))
      .toContainText('Invalid file format');
  });
});
```

### Python API Test Example

```python
# web_app/tests/api/test_contracts.py
import pytest
from playwright.async_api import Page
from tests.utils.api_client import APIClient

@pytest.mark.api
@pytest.mark.asyncio
async def test_get_contracts(api_client: APIClient):
    """Test GET /api/contracts endpoint."""
    # Act
    response = await api_client.get("/api/contracts", {"limit": 10})

    # Assert
    assert "contracts" in response
    assert isinstance(response["contracts"], list)
    assert len(response["contracts"]) <= 10

@pytest.mark.api
@pytest.mark.asyncio
async def test_get_contract_by_id(api_client: APIClient):
    """Test GET /api/contracts/{id} endpoint."""
    # Arrange - Create a test contract first
    contracts = await api_client.get("/api/contracts", {"limit": 1})
    contract_id = contracts["contracts"][0]["id"]

    # Act
    response = await api_client.get(f"/api/contracts/{contract_id}")

    # Assert
    assert response["id"] == contract_id
    assert "filename" in response
    assert "contractor_party" in response

@pytest.mark.api
@pytest.mark.asyncio
@pytest.mark.slow
async def test_contract_upload(api_client: APIClient, test_contract_pdf: str):
    """Test contract upload workflow."""
    # Act
    response = await api_client.upload_file(
        "/api/contracts/upload",
        test_contract_pdf,
        "file"
    )

    # Assert
    assert "job_id" in response
    job_id = response["job_id"]

    # Wait for job completion
    job = await api_client.wait_for_job_completion(job_id, timeout=60000)

    assert job["status"] == "completed"
    assert job["result_id"] is not None

    # Verify contract was created
    contract = await api_client.get(f"/api/contracts/{job['result_id']}")
    assert contract["id"] == job["result_id"]

@pytest.mark.api
@pytest.mark.asyncio
async def test_query_contracts(api_client: APIClient):
    """Test contract query endpoint."""
    # Arrange
    query_request = {
        "question": "What are the termination provisions?",
        "contract_ids": ["contract_1", "contract_2"],
        "modelSelection": "primary",
        "userEmail": "test@example.com"
    }

    # Act
    response = await api_client.post("/api/contracts/query", query_request)

    # Assert
    assert "job_id" in response
    job_id = response["job_id"]

    # Wait for completion
    job = await api_client.wait_for_job_completion(job_id)

    assert job["status"] == "completed"
    assert job["result_id"] is not None
```

### E2E Workflow Test Example

```python
# web_app/tests/e2e/test_comparison_workflow.py
import pytest
from playwright.async_api import Page, expect
from tests.utils.api_client import APIClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_comparison_workflow(page: Page, api_client: APIClient):
    """Test complete contract comparison workflow from UI."""
    # Navigate to compare page
    await page.goto("https://localhost:4200/compare-contracts")

    # Select standard contract
    await page.locator('[data-testid="standard-contract-select"]').click()
    await page.locator('[data-testid="contract-option-1"]').click()

    # Select comparison contract
    await page.locator('[data-testid="comparison-contract-select"]').click()
    await page.locator('[data-testid="contract-option-2"]').click()

    # Select comparison mode
    await page.locator('[data-testid="comparison-mode-clauses"]').click()

    # Select clauses
    await page.locator('[data-testid="clause-select-termination"]').check()
    await page.locator('[data-testid="clause-select-liability"]').check()

    # Choose processing mode
    await page.locator('[data-testid="processing-mode-realtime"]').click()

    # Submit comparison
    await page.locator('[data-testid="submit-comparison-btn"]').click()

    # Wait for results to appear
    await expect(page.locator('[data-testid="comparison-results"]')).toBeVisible(
        timeout=30000
    )

    # Verify results contain expected sections
    await expect(page.locator('[data-testid="clause-termination-result"]')).toBeVisible()
    await expect(page.locator('[data-testid="clause-liability-result"]')).toBeVisible()

    # Check for similarity scores
    termination_score = await page.locator('[data-testid="termination-similarity-score"]').textContent()
    assert termination_score is not None
    assert "%" in termination_score

    # Export results
    await page.locator('[data-testid="export-results-btn"]').click()
    await page.locator('[data-testid="export-pdf-option"]').click()

    # Verify download started (check for download event)
    async with page.expect_download() as download_info:
        download = await download_info.value
        assert download.suggested_filename.endswith('.pdf')
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/playwright-tests.yml
name: Playwright Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test-frontend:
    name: Frontend E2E Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        working-directory: ./query-builder
        run: npm ci

      - name: Install Playwright browsers
        working-directory: ./query-builder
        run: npx playwright install --with-deps

      - name: Run Playwright tests
        working-directory: ./query-builder
        run: npm run test:e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: query-builder/playwright-report/
          retention-days: 30

  test-backend:
    name: Backend API Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        working-directory: ./web_app
        run: |
          pip install -r requirements.txt
          playwright install --with-deps chromium

      - name: Run API tests
        working-directory: ./web_app
        run: pytest tests/api -v --junit-xml=test-results.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: pytest-results
          path: web_app/test-results.xml
```

---

## Best Practices

### 1. Test Data Management

**Use Fixtures:**
```typescript
// e2e/fixtures/test-data.ts
export const TEST_CONTRACTS = {
  msa: {
    filename: "test_msa.pdf",
    contractorParty: "Acme Corp",
    contractingParty: "Customer Inc",
    type: "MSA"
  },
  sow: {
    filename: "test_sow.pdf",
    contractorParty: "Acme Corp",
    contractingParty: "Customer Inc",
    type: "SOW"
  }
};

export function generateTestContract(overrides = {}) {
  return {
    id: `test_contract_${Date.now()}`,
    filename: "test_contract.pdf",
    ...overrides
  };
}
```

### 2. Wait Strategies

**Use Smart Waits:**
```typescript
// Wait for network idle
await page.waitForLoadState('networkidle');

// Wait for specific element
await page.waitForSelector('[data-testid="results-loaded"]', {
  state: 'visible',
  timeout: 30000
});

// Wait for API response
await page.waitForResponse(
  response => response.url().includes('/api/contracts') && response.status() === 200
);

// Wait for function condition
await page.waitForFunction(() => {
  return document.querySelector('[data-loading]')?.getAttribute('data-loading') === 'false';
});
```

### 3. Test Isolation

**Clean Up Between Tests:**
```python
@pytest.fixture(autouse=True)
async def cleanup_test_data(api_client: APIClient):
    """Clean up test data before and after each test."""
    # Setup: Clean before test
    await api_client.post("/api/test/cleanup", {})

    yield

    # Teardown: Clean after test
    await api_client.post("/api/test/cleanup", {})
```

### 4. Parallel Execution

**Configure Workers:**
```typescript
// playwright.config.ts
export default defineConfig({
  // Run tests in parallel
  fullyParallel: true,

  // Number of parallel workers
  workers: process.env.CI ? 2 : 4,

  // Test timeout
  timeout: 30000,
});
```

### 5. Visual Testing (Optional)

**Screenshot Comparison:**
```typescript
test('compare contracts page layout', async ({ page }) => {
  await page.goto('/compare-contracts');
  await page.waitForLoadState('networkidle');

  // Take screenshot and compare
  await expect(page).toHaveScreenshot('compare-contracts.png', {
    maxDiffPixels: 100
  });
});
```

### 6. Accessibility Testing

**Check for A11y:**
```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('contracts page should be accessible', async ({ page }) => {
  await page.goto('/contracts');

  const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

  expect(accessibilityScanResults.violations).toEqual([]);
});
```

### 7. Network Mocking

**Mock API Responses:**
```typescript
test('handle API errors gracefully', async ({ page }) => {
  // Mock API to return error
  await page.route('**/api/contracts', route => {
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Internal server error' })
    });
  });

  await page.goto('/contracts');

  await expect(page.locator('[data-testid="error-message"]'))
    .toContainText('Failed to load contracts');
});
```

### 8. Test Organization

**Use Test Tags:**
```typescript
test.describe('Contract Upload @smoke', () => {
  test('basic upload @critical', async ({ page }) => {
    // Critical smoke test
  });

  test('upload with validation @slow', async ({ page }) => {
    // Slower, detailed test
  });
});
```

**Run Specific Tests:**
```bash
# Run smoke tests only
npx playwright test --grep @smoke

# Skip slow tests
npx playwright test --grep-invert @slow

# Run critical tests on specific browser
npx playwright test --grep @critical --project=chromium
```

---

## Quick Start Checklist

### Angular Setup
- [ ] Install Playwright: `npm install --save-dev @playwright/test`
- [ ] Install browsers: `npx playwright install`
- [ ] Create `playwright.config.ts`
- [ ] Create test directory structure: `e2e/tests`, `e2e/pages`, `e2e/fixtures`
- [ ] Add test scripts to `package.json`
- [ ] Add `data-testid` attributes to components
- [ ] Create page objects for each main page
- [ ] Write first test

### Python Setup
- [ ] Install Playwright: `pip install playwright pytest-playwright`
- [ ] Install browsers: `playwright install`
- [ ] Create `pytest.ini`
- [ ] Create test directory structure: `tests/api`, `tests/e2e`, `tests/fixtures`
- [ ] Create `conftest.py` with fixtures
- [ ] Create API client helper
- [ ] Add test endpoints (health, reset, seed)
- [ ] Write first API test

### Code Updates
- [ ] Add `data-testid` to all interactive elements
- [ ] Expose component states with `@HostBinding`
- [ ] Use stable IDs (not random/time-based)
- [ ] Add loading/error state indicators
- [ ] Create test-specific endpoints
- [ ] Make background jobs synchronous in test mode
- [ ] Add test data fixtures

---

## Resources

**Playwright Documentation:**
- Official Docs: https://playwright.dev
- Best Practices: https://playwright.dev/docs/best-practices
- API Reference: https://playwright.dev/docs/api/class-playwright

**Angular Testing:**
- Angular + Playwright: https://playwright.dev/docs/test-components

**Python Testing:**
- Pytest Playwright: https://playwright.dev/python/docs/intro
- Async Testing: https://playwright.dev/python/docs/test-runners

**Community:**
- GitHub Discussions: https://github.com/microsoft/playwright/discussions
- Stack Overflow: Tag `playwright`
- Discord: https://aka.ms/playwright/discord
