# Playwright Quick Start - Step-by-Step Implementation

This guide provides the exact commands and code changes needed to add Playwright to your project.

---

## Part 1: Angular Frontend Setup (30 minutes)

### Step 1: Install Playwright

```bash
cd query-builder

# Install Playwright
npm install --save-dev @playwright/test

# Install browsers
npx playwright install
```

### Step 2: Initialize Configuration

```bash
# Generate initial config (select defaults)
npx playwright init
```

This creates:
- `playwright.config.ts`
- `tests/` directory
- Example test file

### Step 3: Update Playwright Configuration

Replace the generated `playwright.config.ts` with:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30 * 1000,
  expect: { timeout: 5000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }]
  ],

  use: {
    baseURL: 'https://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: {
    command: 'npm run start',
    url: 'https://localhost:4200',
    reuseExistingServer: !process.env.CI,
    ignoreHTTPSErrors: true,
    timeout: 120 * 1000,
  },
});
```

### Step 4: Create Directory Structure

```bash
# Create test directories
mkdir -p e2e/pages
mkdir -p e2e/tests
mkdir -p e2e/fixtures

# Remove default tests directory
rm -rf tests
```

### Step 5: Add NPM Scripts

Add to `package.json` scripts section:

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:report": "playwright show-report"
  }
}
```

### Step 6: Create Your First Page Object

Create `e2e/pages/contracts-list.page.ts`:

```typescript
import { Page, Locator } from '@playwright/test';

export class ContractsListPage {
  readonly page: Page;
  readonly uploadButton: Locator;
  readonly contractsTable: Locator;

  constructor(page: Page) {
    this.page = page;
    this.uploadButton = page.locator('[data-testid="upload-contract-btn"]');
    this.contractsTable = page.locator('[data-testid="contracts-table"]');
  }

  async goto() {
    await this.page.goto('/contracts');
    await this.page.waitForLoadState('networkidle');
  }

  async getContractCount(): Promise<number> {
    const rows = await this.contractsTable.locator('tr').count();
    return rows - 1; // Subtract header row
  }
}
```

### Step 7: Create Your First Test

Create `e2e/tests/contracts-list.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { ContractsListPage } from '../pages/contracts-list.page';

test.describe('Contracts List', () => {
  test('should load contracts page', async ({ page }) => {
    const contractsPage = new ContractsListPage(page);

    await contractsPage.goto();

    await expect(contractsPage.contractsTable).toBeVisible();
  });

  test('should display contracts', async ({ page }) => {
    const contractsPage = new ContractsListPage(page);

    await contractsPage.goto();

    const count = await contractsPage.getContractCount();
    expect(count).toBeGreaterThan(0);
  });
});
```

### Step 8: Add Test IDs to Angular Components

Update your components to include test IDs. Example:

**Before:**
```html
<button (click)="upload()">Upload</button>
```

**After:**
```html
<button data-testid="upload-contract-btn" (click)="upload()">Upload</button>
```

**Apply to these components:**
- `contracts-list.component.html`
- `compare-contracts.component.html`
- `query-contracts.component.html`
- `jobs-page.component.html`

### Step 9: Run Your First Test

```bash
# Make sure backend and frontend are running
# In one terminal:
cd web_app
.\web_app.ps1

# In another terminal:
cd query-builder
npm start

# In a third terminal (or use UI mode):
cd query-builder
npm run test:e2e:ui
```

---

## Part 2: Python Backend Setup (20 minutes)

### Step 1: Install Playwright for Python

```bash
cd web_app

# Activate virtual environment
.\venv.ps1  # Windows

# Install Playwright
pip install playwright pytest-playwright pytest-asyncio

# Install browsers
playwright install chromium

# Update requirements
pip freeze > requirements.txt
```

### Step 2: Create Pytest Configuration

Create `web_app/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    e2e: End-to-end tests
    api: API endpoint tests
    slow: Slow running tests
```

### Step 3: Create Directory Structure

```bash
cd web_app
mkdir -p tests/api
mkdir -p tests/fixtures
mkdir -p tests/utils
```

### Step 4: Create Base Test Configuration

Create `web_app/tests/conftest.py`:

```python
import pytest
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import AsyncGenerator

BASE_API_URL = "https://localhost:8000"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture(scope="function")
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    context = await browser.new_context(
        ignore_https_errors=True,
    )
    yield context
    await context.close()

@pytest.fixture(scope="function")
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    page = await context.new_page()
    yield page
    await page.close()
```

### Step 5: Create API Test Helper

Create `web_app/tests/utils/api_client.py`:

```python
from playwright.async_api import Page
from typing import Dict, Any

class APIClient:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    async def get(self, endpoint: str) -> Dict[str, Any]:
        response = await self.page.request.get(f"{self.base_url}{endpoint}")
        return await response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        response = await self.page.request.post(
            f"{self.base_url}{endpoint}",
            data=data
        )
        return await response.json()
```

### Step 6: Add API Client Fixture

Add to `web_app/tests/conftest.py`:

```python
from tests.utils.api_client import APIClient

@pytest.fixture(scope="function")
async def api_client(page: Page):
    return APIClient(page, BASE_API_URL)
```

### Step 7: Create Your First API Test

Create `web_app/tests/api/test_health.py`:

```python
import pytest
from tests.utils.api_client import APIClient

@pytest.mark.api
@pytest.mark.asyncio
async def test_health_endpoint(api_client: APIClient):
    """Test health check endpoint."""
    response = await api_client.get("/api/health")

    assert response["status"] == "healthy"
    assert "timestamp" in response
```

### Step 8: Add Health Endpoint to Backend

Add to `web_app/web_app.py`:

```python
from datetime import datetime

@app.get("/api/health")
async def health_check():
    """Health check endpoint for testing."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
```

### Step 9: Run Your First API Test

```bash
# Make sure backend is running
cd web_app

# Run tests
pytest tests/api/test_health.py -v
```

---

## Part 3: Code Updates for Testability (1 hour)

### Priority 1: Add Test IDs to All Interactive Elements

**File: `query-builder/src/app/contracts/contracts-list/contracts-list.component.html`**

Find and update:

```html
<!-- Upload button -->
<button data-testid="upload-contract-btn" ...>Upload Contract</button>

<!-- Search input -->
<input data-testid="search-input" ...>

<!-- Filter dropdowns -->
<select data-testid="filter-contract-type" ...>

<!-- Contracts table -->
<table data-testid="contracts-table" ...>

<!-- Contract rows -->
<tr *ngFor="let contract of contracts"
    [attr.data-testid]="'contract-row-' + contract.id">

<!-- Action buttons -->
<button [attr.data-testid]="'view-btn-' + contract.id">View</button>
<button [attr.data-testid]="'delete-btn-' + contract.id">Delete</button>

<!-- Pagination -->
<div data-testid="pagination-info">Total: {{ totalContracts }}</div>
```

### Priority 2: Add Loading States

**File: `query-builder/src/app/contracts/contracts-list/contracts-list.component.ts`**

Add:

```typescript
export class ContractsListComponent {
  @HostBinding('attr.data-loading')
  get isLoading() { return this.loading; }

  @HostBinding('attr.data-error')
  get hasError() { return !!this.errorMessage; }

  private loading = false;
  errorMessage: string | null = null;

  async loadContracts() {
    this.loading = true;
    this.errorMessage = null;

    try {
      this.contracts = await this.contractService.getContracts().toPromise();
    } catch (error) {
      this.errorMessage = error.message;
    } finally {
      this.loading = false;
    }
  }
}
```

### Priority 3: Update All Major Components

Apply similar updates to:
- `compare-contracts.component.html` and `.ts`
- `query-contracts.component.html` and `.ts`
- `jobs-page.component.html` and `.ts`
- `clause-library.component.html` and `.ts`

### Priority 4: Add Backend Test Endpoints

**File: `web_app/web_app.py`**

Add at the end of file:

```python
import os

# Test endpoints (only in development/test)
if os.getenv("ENVIRONMENT") in ["development", "test"]:

    @app.get("/api/health")
    async def health_check():
        """Health check for testing."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }

    @app.post("/api/test/reset")
    async def reset_test_data():
        """Reset test data."""
        # TODO: Implement cleanup logic
        return {"status": "reset"}
```

---

## Part 4: Create Essential Page Objects (45 minutes)

### Create Base Page Object

Create `e2e/pages/base.page.ts`:

```typescript
import { Page } from '@playwright/test';

export class BasePage {
  constructor(protected page: Page) {}

  async goto(path: string) {
    await this.page.goto(path);
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForSelector('[data-loading="false"]', {
      state: 'attached',
      timeout: 10000
    }).catch(() => {
      // Loading attribute may not exist, that's ok
    });
  }
}
```

### Create Compare Contracts Page Object

Create `e2e/pages/compare-contracts.page.ts`:

```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class CompareContractsPage extends BasePage {
  readonly standardContractSelect: Locator;
  readonly comparisonContractSelect: Locator;
  readonly comparisonModeRadio: Locator;
  readonly submitButton: Locator;
  readonly resultsContainer: Locator;

  constructor(page: Page) {
    super(page);
    this.standardContractSelect = page.locator('[data-testid="standard-contract-select"]');
    this.comparisonContractSelect = page.locator('[data-testid="comparison-contract-select"]');
    this.comparisonModeRadio = page.locator('[data-testid="comparison-mode-clauses"]');
    this.submitButton = page.locator('[data-testid="submit-comparison-btn"]');
    this.resultsContainer = page.locator('[data-testid="comparison-results"]');
  }

  async goto() {
    await super.goto('/compare-contracts');
  }

  async compareContracts(standardId: string, comparisonId: string) {
    await this.standardContractSelect.selectOption(standardId);
    await this.comparisonContractSelect.selectOption(comparisonId);
    await this.submitButton.click();
    await this.resultsContainer.waitFor({ state: 'visible', timeout: 30000 });
  }
}
```

### Create Query Contracts Page Object

Create `e2e/pages/query-contracts.page.ts`:

```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class QueryContractsPage extends BasePage {
  readonly questionInput: Locator;
  readonly contractSelectionList: Locator;
  readonly submitButton: Locator;
  readonly resultsContainer: Locator;

  constructor(page: Page) {
    super(page);
    this.questionInput = page.locator('[data-testid="question-input"]');
    this.contractSelectionList = page.locator('[data-testid="contract-selection-list"]');
    this.submitButton = page.locator('[data-testid="submit-query-btn"]');
    this.resultsContainer = page.locator('[data-testid="query-results"]');
  }

  async goto() {
    await super.goto('/query-contracts');
  }

  async queryContracts(question: string, contractIds: string[]) {
    await this.questionInput.fill(question);

    for (const id of contractIds) {
      await this.page.locator(`[data-testid="contract-checkbox-${id}"]`).check();
    }

    await this.submitButton.click();
    await this.resultsContainer.waitFor({ state: 'visible', timeout: 30000 });
  }
}
```

### Create Jobs Page Object

Create `e2e/pages/jobs.page.ts`:

```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class JobsPage extends BasePage {
  readonly jobList: Locator;

  constructor(page: Page) {
    super(page);
    this.jobList = page.locator('[data-testid="job-list"]');
  }

  async goto() {
    await super.goto('/jobs');
  }

  async waitForJobCompletion(jobId: string, timeout: number = 60000) {
    await this.page.waitForSelector(
      `[data-testid="job-${jobId}"][data-status="completed"]`,
      { timeout }
    );
  }

  async getJobStatus(jobId: string): Promise<string> {
    const statusElement = this.page.locator(`[data-testid="job-${jobId}"] [data-testid="job-status"]`);
    return await statusElement.textContent() || '';
  }
}
```

---

## Part 5: Write Core Tests (1 hour)

### Test 1: Contract Upload Workflow

Create `e2e/tests/workflows/contract-upload.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { ContractsListPage } from '../../pages/contracts-list.page';
import { JobsPage } from '../../pages/jobs.page';

test.describe('Contract Upload Workflow', () => {
  test('should upload contract and process successfully', async ({ page }) => {
    const contractsPage = new ContractsListPage(page);
    const jobsPage = new JobsPage(page);

    // Go to contracts page
    await contractsPage.goto();

    // Note initial count
    const initialCount = await contractsPage.getContractCount();

    // Upload contract
    const testFile = 'e2e/fixtures/sample_contract.pdf';
    await contractsPage.uploadButton.click();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFile);

    // Go to jobs page
    await jobsPage.goto();

    // Wait for job completion
    await page.waitForSelector('[data-testid="job-type-CONTRACT_UPLOAD"]', {
      state: 'visible'
    });

    // Verify job completed
    await expect(page.locator('[data-status="completed"]').first())
      .toBeVisible({ timeout: 60000 });

    // Return to contracts and verify new contract
    await contractsPage.goto();
    const newCount = await contractsPage.getContractCount();
    expect(newCount).toBe(initialCount + 1);
  });
});
```

### Test 2: Contract Comparison

Create `e2e/tests/comparison/basic-comparison.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { CompareContractsPage } from '../../pages/compare-contracts.page';

test.describe('Contract Comparison', () => {
  test('should compare two contracts', async ({ page }) => {
    const comparePage = new CompareContractsPage(page);

    await comparePage.goto();

    // Select contracts
    await comparePage.standardContractSelect.selectOption({ index: 1 });
    await comparePage.comparisonContractSelect.selectOption({ index: 2 });

    // Select mode
    await comparePage.comparisonModeRadio.check();

    // Submit
    await comparePage.submitButton.click();

    // Verify results appear
    await expect(comparePage.resultsContainer).toBeVisible({ timeout: 30000 });

    // Check for comparison data
    await expect(page.locator('[data-testid="clause-comparison"]').first())
      .toBeVisible();
  });
});
```

### Test 3: Contract Query

Create `e2e/tests/query/basic-query.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { QueryContractsPage } from '../../pages/query-contracts.page';

test.describe('Contract Query', () => {
  test('should query contracts and get results', async ({ page }) => {
    const queryPage = new QueryContractsPage(page);

    await queryPage.goto();

    // Enter question
    await queryPage.questionInput.fill('What are the termination provisions?');

    // Select contracts
    await page.locator('[data-testid="select-all-contracts"]').check();

    // Submit query
    await queryPage.submitButton.click();

    // Verify results
    await expect(queryPage.resultsContainer).toBeVisible({ timeout: 30000 });

    // Check for answer content
    await expect(page.locator('[data-testid="query-answer"]'))
      .toContainText('termination');
  });
});
```

---

## Part 6: Run Tests

### Run All Tests

```bash
# Angular E2E tests
cd query-builder
npm run test:e2e

# Python API tests
cd web_app
pytest tests/api -v
```

### Run in UI Mode (Recommended for Development)

```bash
# Angular E2E tests
cd query-builder
npm run test:e2e:ui

# Opens interactive UI where you can:
# - See all tests
# - Run individual tests
# - Watch test execution
# - Debug failures
# - View screenshots/videos
```

### Run Specific Tests

```bash
# Run specific test file
npx playwright test e2e/tests/contracts-list.spec.ts

# Run tests matching pattern
npx playwright test --grep "upload"

# Run only failed tests
npx playwright test --last-failed
```

### Debug Tests

```bash
# Debug mode (stops at breakpoints)
npx playwright test --debug

# Headed mode (see browser)
npx playwright test --headed

# Specific browser
npx playwright test --project=chromium
```

---

## Troubleshooting

### Issue: "locator.click: Target closed"

**Solution:** Add wait before click:
```typescript
await page.waitForSelector('[data-testid="button"]', { state: 'visible' });
await page.locator('[data-testid="button"]').click();
```

### Issue: "Test timeout exceeded"

**Solution:** Increase timeout:
```typescript
test('long test', async ({ page }) => {
  test.setTimeout(60000); // 60 seconds
  // ...
});
```

### Issue: "Element not found"

**Solution:** Check selector and add wait:
```typescript
// Wait for element to exist
await page.waitForSelector('[data-testid="element"]');

// Or use expect with timeout
await expect(page.locator('[data-testid="element"]'))
  .toBeVisible({ timeout: 10000 });
```

### Issue: "Self-signed certificate error"

**Solution:** Already configured in `playwright.config.ts`:
```typescript
use: {
  ignoreHTTPSErrors: true,
}
```

---

## Next Steps

1. **Add more test IDs** to remaining components
2. **Create page objects** for all pages
3. **Write tests** for critical workflows
4. **Set up CI/CD** to run tests automatically
5. **Add visual regression tests** (optional)
6. **Add accessibility tests** (optional)
7. **Monitor test flakiness** and fix unstable tests

---

## Resources

- **Playwright Docs:** https://playwright.dev
- **Best Practices:** https://playwright.dev/docs/best-practices
- **Debugging:** https://playwright.dev/docs/debug
- **Selectors:** https://playwright.dev/docs/selectors
- **Assertions:** https://playwright.dev/docs/test-assertions
