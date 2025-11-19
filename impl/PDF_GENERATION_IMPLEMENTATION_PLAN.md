# PDF Generation and Email Implementation Plan

## Overview

Add PDF export and email functionality to Compare Contracts and Query Contracts pages, with support for batch processing through stored results.

## Architecture Components

### 1. Results Storage Layer
**Purpose**: Store analysis results for PDF generation and historical tracking

**CosmosDB Container**: `analysis_results`

**Schema**:
```python
{
    "id": "result_uuid",
    "result_type": "comparison" | "query",
    "user_id": "user@example.com",
    "created_at": "2025-10-23T10:30:00Z",
    "status": "completed" | "in_progress" | "failed",

    # Common metadata
    "metadata": {
        "title": "Contract Comparison Report",
        "description": "Analysis of 3 contracts",
        "execution_time_seconds": 12.5
    },

    # For comparison results
    "comparison_data": {
        "standard_contract_id": "contract_abc",
        "compare_contract_ids": ["contract_xyz", "contract_def"],
        "comparison_mode": "full" | "clauses",
        "selected_clauses": ["ClauseType1", "ClauseType2"] | "all",
        "results": { ... }  # Full comparison response
    },

    # For query results (natural language queries against multiple contracts)
    "query_data": {
        "query_text": "Which of these contracts have the broadest indemnification for the contracting party?",
        "query_type": "natural_language",
        "contracts_queried": [
            {
                "contract_id": "contract_abc_123",
                "filename": "Westervelt_Standard_MSA.json",
                "contract_title": "Westervelt Standard MSA"
            },
            {
                "contract_id": "contract_def_456",
                "filename": "ACME_Corp_Agreement.json",
                "contract_title": "ACME Corp Service Agreement"
            }
        ],
        "results": {
            "answer_summary": "Contracts ranked by indemnification breadth...",
            "ranked_contracts": [
                {
                    "contract_id": "contract_abc_123",
                    "filename": "Westervelt_Standard_MSA.json",
                    "rank": 1,
                    "score": 0.95,
                    "reasoning": "This contract provides the broadest indemnification...",
                    "relevant_clauses": [
                        {
                            "clause_type": "Indemnification",
                            "clause_text": "Party A shall indemnify...",
                            "analysis": "Covers all potential liabilities..."
                        }
                    ]
                }
            ],
            "execution_metadata": {
                "contracts_analyzed": 5,
                "query_time_seconds": 3.2,
                "llm_model": "gpt-4"
            }
        }
    },

    # PDF metadata (once generated)
    "pdf_metadata": {
        "generated_at": "2025-10-23T10:35:00Z",
        "file_size_bytes": 245678,
        "page_count": 15,
        "blob_url": "https://storage.../result_uuid.pdf"  # Optional: if storing PDFs
    }
}
```

**Index Policy**:
- Partition Key: `/user_id`
- Indexed: `/result_type`, `/created_at`, `/status`

### 2. Backend Services

#### 2.1 Results Storage Service (`web_app/src/services/analysis_results_service.py`)

```python
class AnalysisResultsService:
    """Manages storage and retrieval of analysis results"""

    async def save_comparison_result(
        self,
        user_id: str,
        standard_contract_id: str,
        compare_contract_ids: List[str],
        comparison_mode: str,
        results: dict
    ) -> str:
        """Store comparison results and return result_id"""

    async def save_query_result(
        self,
        user_id: str,
        query_text: str,
        query_type: str,
        contracts_queried: List[dict],  # List of {contract_id, filename, title}
        results: dict  # Query answer and ranked results
    ) -> str:
        """Store query results and return result_id"""

    async def get_result(self, result_id: str, user_id: str) -> dict:
        """Retrieve stored result by ID"""

    async def list_user_results(
        self,
        user_id: str,
        result_type: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """List results for a user with pagination"""
```

#### 2.2 PDF Generation Service (`web_app/src/services/pdf_generation_service.py`)

**Technology Choice**: **WeasyPrint** (recommended)
- Converts HTML/CSS to PDF
- Excellent CSS support (Paged Media, Flexbox, Grid)
- Professional pagination and formatting
- Python native, good for FastAPI

**Alternative**: ReportLab (more control but more complex)

```python
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader

class PDFGenerationService:
    """Generates PDFs from analysis results using HTML templates"""

    def __init__(self):
        self.template_env = Environment(
            loader=FileSystemLoader('web_app/templates/pdf')
        )

    async def generate_comparison_pdf(
        self,
        result_id: str,
        result_data: dict
    ) -> bytes:
        """Generate PDF from comparison results"""
        template = self.template_env.get_template('comparison_report.html')
        html_content = template.render(
            result=result_data,
            generated_at=datetime.utcnow(),
            # ... other context
        )

        # Apply custom CSS for PDF styling
        pdf_css = CSS(filename='web_app/templates/pdf/styles.css')

        # Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[pdf_css]
        )

        return pdf_bytes

    async def generate_query_pdf(
        self,
        result_id: str,
        result_data: dict
    ) -> bytes:
        """Generate PDF from query results"""
        # Similar to comparison but with query template
```

#### 2.3 Email Service (`web_app/src/services/email_service.py`)

**Technology**: Azure Communication Services Email or SendGrid

```python
from azure.communication.email import EmailClient

class EmailService:
    """Sends emails with PDF attachments"""

    def __init__(self):
        self.email_client = EmailClient.from_connection_string(
            os.getenv('AZURE_COMMUNICATION_EMAIL_CONNECTION_STRING')
        )

    async def send_pdf_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        pdf_content: bytes,
        pdf_filename: str,
        from_address: str = "noreply@yourdomain.com"
    ) -> dict:
        """Send email with PDF attachment"""

        message = {
            "senderAddress": from_address,
            "recipients": {
                "to": [{"address": addr} for addr in to_addresses]
            },
            "content": {
                "subject": subject,
                "plainText": body,
                "html": f"<html><body><p>{body}</p></body></html>"
            },
            "attachments": [
                {
                    "name": pdf_filename,
                    "contentType": "application/pdf",
                    "contentInBase64": base64.b64encode(pdf_content).decode()
                }
            ]
        }

        poller = self.email_client.begin_send(message)
        result = poller.result()

        return {
            "message_id": result.id,
            "status": result.status
        }
```

### 3. API Endpoints (`web_app/routers/analysis_results_router.py`)

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io

router = APIRouter(prefix="/api/analysis-results", tags=["analysis-results"])

@router.post("/comparison")
async def save_comparison_result(request: SaveComparisonRequest):
    """Store comparison results for later PDF generation"""
    result_id = await results_service.save_comparison_result(...)
    return {"result_id": result_id, "message": "Results saved"}

@router.post("/query")
async def save_query_result(request: SaveQueryRequest):
    """Store query results for later PDF generation"""
    result_id = await results_service.save_query_result(...)
    return {"result_id": result_id, "message": "Results saved"}

@router.get("/results/{result_id}")
async def get_result(result_id: str, user_id: str):
    """Retrieve stored result"""
    result = await results_service.get_result(result_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

@router.get("/results/{result_id}/pdf")
async def generate_pdf(result_id: str, user_id: str):
    """Generate and download PDF from stored result"""
    # Fetch result
    result = await results_service.get_result(result_id, user_id)

    # Generate PDF
    if result['result_type'] == 'comparison':
        pdf_bytes = await pdf_service.generate_comparison_pdf(result_id, result)
    else:
        pdf_bytes = await pdf_service.generate_query_pdf(result_id, result)

    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=report_{result_id}.pdf"
        }
    )

@router.post("/results/{result_id}/email")
async def email_pdf(result_id: str, request: EmailPDFRequest):
    """Generate PDF and email to recipients"""
    # Fetch result
    result = await results_service.get_result(result_id, request.user_id)

    # Generate PDF
    if result['result_type'] == 'comparison':
        pdf_bytes = await pdf_service.generate_comparison_pdf(result_id, result)
    else:
        pdf_bytes = await pdf_service.generate_query_pdf(result_id, result)

    # Send email
    email_result = await email_service.send_pdf_email(
        to_addresses=request.recipients,
        subject=f"Analysis Report: {result['metadata']['title']}",
        body=request.message or "Please find attached your analysis report.",
        pdf_content=pdf_bytes,
        pdf_filename=f"report_{result_id}.pdf"
    )

    return {"message": "Email sent", "email_id": email_result['message_id']}

@router.get("/user/{user_id}/results")
async def list_user_results(
    user_id: str,
    result_type: Optional[str] = None,
    limit: int = 50
):
    """List all results for a user"""
    results = await results_service.list_user_results(user_id, result_type, limit)
    return {"results": results, "count": len(results)}
```

### 4. PDF Templates

**Template Structure**: `web_app/templates/pdf/`

#### 4.1 Comparison Report Template (`comparison_report.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contract Comparison Report</title>
    <style>
        /* PDF-specific CSS with page breaks */
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Contract Comparison Report";
            }
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
            }
        }

        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 10pt;
            line-height: 1.5;
        }

        h1 {
            color: #2c3e50;
            page-break-after: avoid;
        }

        h2 {
            color: #34495e;
            margin-top: 1.5em;
            page-break-after: avoid;
        }

        .summary-box {
            background-color: #f8f9fa;
            padding: 1em;
            border-left: 4px solid #3498db;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        .comparison-section {
            margin: 2em 0;
            page-break-inside: avoid;
        }

        .risk-high { color: #e74c3c; font-weight: bold; }
        .risk-medium { color: #f39c12; }
        .risk-low { color: #27ae60; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }

        th, td {
            padding: 0.5em;
            border: 1px solid #ddd;
            text-align: left;
        }

        th {
            background-color: #34495e;
            color: white;
        }

        .clause-analysis {
            margin: 1em 0;
            padding: 1em;
            background-color: #f8f9fa;
            page-break-inside: avoid;
        }
    </style>
</head>
<body>
    <!-- Report Header -->
    <h1>Contract Comparison Report</h1>
    <div class="summary-box">
        <p><strong>Generated:</strong> {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }} UTC</p>
        <p><strong>Standard Contract:</strong> {{ result.comparison_data.standard_contract_id }}</p>
        <p><strong>Compared Contracts:</strong> {{ result.comparison_data.compare_contract_ids | join(', ') }}</p>
        <p><strong>Comparison Mode:</strong> {{ result.comparison_data.comparison_mode }}</p>
    </div>

    <!-- Executive Summary -->
    <h2>Executive Summary</h2>
    {% for comparison in result.comparison_data.results.comparisons %}
    <div class="comparison-section">
        <h3>Contract: {{ comparison.contract_id }}</h3>
        <p>
            <strong>Overall Similarity:</strong> {{ "%.1f" | format(comparison.overall_similarity_score * 100) }}%
            <span class="risk-{{ comparison.risk_level }}">
                ({{ comparison.risk_level | upper }} RISK)
            </span>
        </p>

        {% if comparison.critical_findings %}
        <h4>Critical Findings</h4>
        <ul>
            {% for finding in comparison.critical_findings %}
            <li>{{ finding }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    {% endfor %}

    <!-- Detailed Clause Analysis -->
    <h2 style="page-break-before: always;">Detailed Clause Analysis</h2>
    {% for comparison in result.comparison_data.results.comparisons %}
    <h3>{{ comparison.contract_id }}</h3>

    {% if comparison.clause_analyses %}
        {% for clause in comparison.clause_analyses %}
        <div class="clause-analysis">
            <h4>{{ clause.clause_type }}</h4>
            <p><strong>Similarity:</strong> {{ "%.1f" | format(clause.similarity_score * 100) }}%</p>
            <p><strong>Risk Level:</strong> <span class="risk-{{ clause.risk_level }}">{{ clause.risk_level | upper }}</span></p>

            {% if clause.key_differences %}
            <p><strong>Key Differences:</strong></p>
            <ul>
                {% for diff in clause.key_differences %}
                <li>{{ diff }}</li>
                {% endfor %}
            </ul>
            {% endif %}

            {% if clause.recommendations %}
            <p><strong>Recommendations:</strong></p>
            <ul>
                {% for rec in clause.recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    {% endif %}
    {% endfor %}

    <!-- Missing/Additional Clauses -->
    {% for comparison in result.comparison_data.results.comparisons %}
    {% if comparison.missing_clauses or comparison.additional_clauses %}
    <h2 style="page-break-before: always;">Clause Presence Analysis - {{ comparison.contract_id }}</h2>

    {% if comparison.missing_clauses %}
    <h3>Missing Clauses</h3>
    <ul>
        {% for clause in comparison.missing_clauses %}
        <li>{{ clause }}</li>
        {% endfor %}
    </ul>
    {% endif %}

    {% if comparison.additional_clauses %}
    <h3>Additional Clauses</h3>
    <ul>
        {% for clause in comparison.additional_clauses %}
        <li>{{ clause }}</li>
        {% endfor %}
    </ul>
    {% endif %}
    {% endif %}
    {% endfor %}
</body>
</html>
```

#### 4.2 Query Results Template (`query_report.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contract Query Report</title>
    <style>
        /* PDF-specific CSS with page breaks */
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Contract Query Report";
            }
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
            }
        }

        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 10pt;
            line-height: 1.5;
        }

        h1 {
            color: #2c3e50;
            page-break-after: avoid;
        }

        h2 {
            color: #34495e;
            margin-top: 1.5em;
            page-break-after: avoid;
        }

        .query-box {
            background-color: #e8f4f8;
            padding: 1.5em;
            border-left: 4px solid #3498db;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        .query-text {
            font-size: 12pt;
            font-style: italic;
            color: #2c3e50;
        }

        .summary-box {
            background-color: #f8f9fa;
            padding: 1em;
            border-left: 4px solid #27ae60;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        .contracts-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            page-break-inside: avoid;
        }

        .contracts-table th,
        .contracts-table td {
            padding: 0.5em;
            border: 1px solid #ddd;
            text-align: left;
        }

        .contracts-table th {
            background-color: #34495e;
            color: white;
            font-weight: bold;
        }

        .contracts-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        .rank-badge {
            display: inline-block;
            width: 30px;
            height: 30px;
            line-height: 30px;
            text-align: center;
            border-radius: 50%;
            font-weight: bold;
            color: white;
        }

        .rank-1 { background-color: #f39c12; }
        .rank-2 { background-color: #95a5a6; }
        .rank-3 { background-color: #e67e22; }
        .rank-other { background-color: #7f8c8d; }

        .score-bar {
            display: inline-block;
            height: 20px;
            background-color: #3498db;
            border-radius: 3px;
        }

        .contract-result {
            margin: 2em 0;
            padding: 1em;
            border: 1px solid #ddd;
            page-break-inside: avoid;
        }

        .contract-header {
            display: flex;
            align-items: center;
            margin-bottom: 1em;
        }

        .reasoning-text {
            background-color: #f8f9fa;
            padding: 1em;
            border-left: 3px solid #3498db;
            margin: 1em 0;
        }

        .clause-section {
            margin: 1em 0;
            padding: 1em;
            background-color: #fffbf0;
            border-left: 3px solid #f39c12;
        }

        .clause-text {
            font-style: italic;
            color: #555;
            margin: 0.5em 0;
            padding: 0.5em;
            background-color: white;
            border-left: 2px solid #ccc;
        }

        .metadata-footer {
            margin-top: 2em;
            padding-top: 1em;
            border-top: 2px solid #ddd;
            font-size: 9pt;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <!-- Report Header -->
    <h1>Contract Query Report</h1>

    <!-- Query Information -->
    <div class="query-box">
        <p><strong>Query:</strong></p>
        <p class="query-text">"{{ result.query_data.query_text }}"</p>
    </div>

    <div class="summary-box">
        <p><strong>Generated:</strong> {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }} UTC</p>
        <p><strong>Contracts Analyzed:</strong> {{ result.query_data.contracts_queried | length }}</p>
        <p><strong>Query Time:</strong> {{ "%.2f" | format(result.query_data.results.execution_metadata.query_time_seconds) }} seconds</p>
    </div>

    <!-- Contracts Queried -->
    <h2>Contracts Analyzed</h2>
    <table class="contracts-table">
        <thead>
            <tr>
                <th>Contract ID</th>
                <th>Filename</th>
                <th>Title</th>
            </tr>
        </thead>
        <tbody>
            {% for contract in result.query_data.contracts_queried %}
            <tr>
                <td>{{ contract.contract_id }}</td>
                <td>{{ contract.filename }}</td>
                <td>{{ contract.contract_title or 'N/A' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <!-- Answer Summary -->
    <h2 style="page-break-before: always;">Analysis Results</h2>
    {% if result.query_data.results.answer_summary %}
    <div class="summary-box">
        <h3>Summary</h3>
        <p>{{ result.query_data.results.answer_summary }}</p>
    </div>
    {% endif %}

    <!-- Ranked Results -->
    <h2>Detailed Contract Rankings</h2>
    {% for contract_result in result.query_data.results.ranked_contracts %}
    <div class="contract-result">
        <!-- Contract Header with Rank -->
        <div class="contract-header">
            <span class="rank-badge rank-{{ contract_result.rank if contract_result.rank <= 3 else 'other' }}">
                {{ contract_result.rank }}
            </span>
            <div style="margin-left: 1em; flex-grow: 1;">
                <h3 style="margin: 0;">{{ contract_result.filename }}</h3>
                <p style="margin: 0.25em 0; color: #7f8c8d;">{{ contract_result.contract_id }}</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0;"><strong>Score:</strong> {{ "%.1f" | format(contract_result.score * 100) }}%</p>
                <div class="score-bar" style="width: {{ contract_result.score * 100 }}px;"></div>
            </div>
        </div>

        <!-- Reasoning -->
        {% if contract_result.reasoning %}
        <div class="reasoning-text">
            <strong>Analysis:</strong>
            <p>{{ contract_result.reasoning }}</p>
        </div>
        {% endif %}

        <!-- Relevant Clauses -->
        {% if contract_result.relevant_clauses %}
        <h4>Relevant Clauses</h4>
        {% for clause in contract_result.relevant_clauses %}
        <div class="clause-section">
            <p><strong>{{ clause.clause_type }}</strong></p>

            {% if clause.clause_text %}
            <div class="clause-text">
                {{ clause.clause_text[:500] }}{% if clause.clause_text|length > 500 %}...{% endif %}
            </div>
            {% endif %}

            {% if clause.analysis %}
            <p><strong>Analysis:</strong> {{ clause.analysis }}</p>
            {% endif %}
        </div>
        {% endfor %}
        {% endif %}
    </div>
    {% endfor %}

    <!-- Footer -->
    <div class="metadata-footer">
        <p><strong>Report Generation Details:</strong></p>
        <p>Contracts Analyzed: {{ result.query_data.results.execution_metadata.contracts_analyzed }}</p>
        <p>LLM Model: {{ result.query_data.results.execution_metadata.llm_model }}</p>
        <p>Query Execution Time: {{ "%.2f" | format(result.query_data.results.execution_metadata.query_time_seconds) }}s</p>
        <p>Report Generated: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }} UTC</p>
    </div>
</body>
</html>
```

### 5. Frontend Integration (Angular)

#### 5.1 Results Storage Service (`query-builder/src/app/services/results-storage.service.ts`)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface SaveResultResponse {
  result_id: string;
  message: string;
}

interface EmailRequest {
  user_id: string;
  recipients: string[];
  message?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ResultsStorageService {
  private apiUrl = 'https://localhost:8000/api/analysis-results';

  constructor(private http: HttpClient) {}

  saveComparisonResult(
    userId: string,
    standardContractId: string,
    compareContractIds: string[],
    comparisonMode: string,
    results: any
  ): Observable<SaveResultResponse> {
    return this.http.post<SaveResultResponse>(`${this.apiUrl}/comparison`, {
      user_id: userId,
      standard_contract_id: standardContractId,
      compare_contract_ids: compareContractIds,
      comparison_mode: comparisonMode,
      results
    });
  }

  saveQueryResult(
    userId: string,
    queryText: string,
    queryType: string,
    contractsQueried: Array<{contract_id: string, filename: string, contract_title?: string}>,
    results: any
  ): Observable<SaveResultResponse> {
    return this.http.post<SaveResultResponse>(`${this.apiUrl}/query`, {
      user_id: userId,
      query_text: queryText,
      query_type: queryType,
      contracts_queried: contractsQueried,
      results
    });
  }

  downloadPDF(resultId: string, userId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/results/${resultId}/pdf?user_id=${userId}`, {
      responseType: 'blob'
    });
  }

  emailPDF(resultId: string, emailRequest: EmailRequest): Observable<any> {
    return this.http.post(`${this.apiUrl}/results/${resultId}/email`, emailRequest);
  }

  getUserResults(userId: string, resultType?: string): Observable<any> {
    let url = `${this.apiUrl}/user/${userId}/results`;
    if (resultType) {
      url += `?result_type=${resultType}`;
    }
    return this.http.get(url);
  }
}
```

#### 5.2 PDF/Email Component (`query-builder/src/app/shared/pdf-email-actions/`)

```typescript
@Component({
  selector: 'app-pdf-email-actions',
  template: `
    <div class="pdf-email-actions">
      <button
        class="btn btn-primary"
        (click)="generatePDF()"
        [disabled]="loading">
        <i class="fas fa-file-pdf"></i> Download PDF
      </button>

      <button
        class="btn btn-secondary"
        (click)="openEmailDialog()"
        [disabled]="loading">
        <i class="fas fa-envelope"></i> Email PDF
      </button>
    </div>

    <!-- Email Dialog -->
    <div *ngIf="showEmailDialog" class="modal">
      <div class="modal-content">
        <h3>Email Report</h3>

        <div class="form-group">
          <label>Recipients (comma-separated emails):</label>
          <textarea
            [(ngModel)]="emailRecipients"
            placeholder="user1@example.com, user2@example.com"
            rows="3">
          </textarea>
        </div>

        <div class="form-group">
          <label>Message (optional):</label>
          <textarea
            [(ngModel)]="emailMessage"
            placeholder="Optional message to include in email"
            rows="4">
          </textarea>
        </div>

        <div class="modal-actions">
          <button (click)="sendEmail()" [disabled]="!isValidEmail()">Send</button>
          <button (click)="closeEmailDialog()">Cancel</button>
        </div>
      </div>
    </div>
  `
})
export class PdfEmailActionsComponent {
  @Input() resultId!: string;
  @Input() userId!: string;

  loading = false;
  showEmailDialog = false;
  emailRecipients = '';
  emailMessage = '';

  constructor(
    private resultsService: ResultsStorageService,
    private toastr: ToastrService
  ) {}

  async generatePDF() {
    this.loading = true;

    try {
      const blob = await firstValueFrom(
        this.resultsService.downloadPDF(this.resultId, this.userId)
      );

      // Download the PDF
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `report_${this.resultId}.pdf`;
      link.click();

      this.toastr.success('PDF downloaded successfully');
    } catch (error) {
      this.toastr.error('Failed to generate PDF');
      console.error(error);
    } finally {
      this.loading = false;
    }
  }

  openEmailDialog() {
    this.showEmailDialog = true;
  }

  closeEmailDialog() {
    this.showEmailDialog = false;
    this.emailRecipients = '';
    this.emailMessage = '';
  }

  isValidEmail(): boolean {
    const emails = this.emailRecipients.split(',').map(e => e.trim());
    return emails.every(email => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
  }

  async sendEmail() {
    if (!this.isValidEmail()) {
      this.toastr.error('Invalid email addresses');
      return;
    }

    this.loading = true;

    try {
      const recipients = this.emailRecipients.split(',').map(e => e.trim());

      await firstValueFrom(
        this.resultsService.emailPDF(this.resultId, {
          user_id: this.userId,
          recipients,
          message: this.emailMessage || undefined
        })
      );

      this.toastr.success('Email sent successfully');
      this.closeEmailDialog();
    } catch (error) {
      this.toastr.error('Failed to send email');
      console.error(error);
    } finally {
      this.loading = false;
    }
  }
}
```

#### 5.3 Integration in Compare/Query Components

**Compare Contracts Component**:
```typescript
// After comparison completes
async onComparisonComplete(results: any) {
  this.comparisonResults = results;

  // Save results to backend
  try {
    const saveResponse = await firstValueFrom(
      this.resultsService.saveComparisonResult(
        this.userId,
        this.standardContractId,
        this.compareContractIds,
        this.comparisonMode,
        results
      )
    );

    this.currentResultId = saveResponse.result_id;
    console.log('Results saved with ID:', this.currentResultId);
  } catch (error) {
    console.error('Failed to save results:', error);
    // Still show results even if save fails
  }
}
```

**Compare Contracts Template addition**:
```html
<div *ngIf="comparisonResults && currentResultId" class="results-actions">
  <app-pdf-email-actions
    [resultId]="currentResultId"
    [userId]="userId">
  </app-pdf-email-actions>
</div>

<div class="results-section">
  <!-- Existing results display -->
</div>
```

**Query Contracts Component Integration**:
```typescript
// In query-contracts.component.ts

// Store the selected contracts
selectedContracts: Array<{contract_id: string, filename: string, title?: string}> = [];

// When user selects contracts for query
onContractsSelected(contracts: any[]) {
  this.selectedContracts = contracts.map(c => ({
    contract_id: c.id || c.contract_id,
    filename: c.filename || c.file_name,
    contract_title: c.title || c.contract_title
  }));
}

// After query completes
async onQueryComplete(queryText: string, results: any) {
  this.queryResults = results;

  // Save results with contract list
  try {
    const saveResponse = await firstValueFrom(
      this.resultsService.saveQueryResult(
        this.userId,
        queryText,
        'natural_language',
        this.selectedContracts,  // Pass the contracts list
        results
      )
    );

    this.currentResultId = saveResponse.result_id;
    console.log('Query results saved with ID:', this.currentResultId);
  } catch (error) {
    console.error('Failed to save query results:', error);
  }
}
```

**Query Contracts Template addition**:
```html
<!-- Contract Selection Section -->
<div class="contract-selection">
  <h3>Select Contracts to Query</h3>
  <div class="contract-list">
    <div *ngFor="let contract of availableContracts" class="contract-item">
      <input
        type="checkbox"
        [id]="contract.contract_id"
        [(ngModel)]="contract.selected"
        (change)="updateSelectedContracts()">
      <label [for]="contract.contract_id">
        {{ contract.filename }} - {{ contract.contract_title }}
      </label>
    </div>
  </div>
</div>

<!-- Query Input Section -->
<div class="query-section">
  <textarea
    [(ngModel)]="queryText"
    placeholder="Ask a question about the selected contracts...
Example: Which of these contracts have the broadest indemnification for the contracting party?"
    rows="4">
  </textarea>
  <button (click)="executeQuery()" [disabled]="!hasSelectedContracts()">
    Submit Query
  </button>
</div>

<!-- Results Section with PDF/Email Actions -->
<div *ngIf="queryResults && currentResultId" class="results-container">
  <div class="results-actions">
    <app-pdf-email-actions
      [resultId]="currentResultId"
      [userId]="userId">
    </app-pdf-email-actions>
  </div>

  <div class="results-section">
    <!-- Existing query results display -->
  </div>
</div>
```

## Implementation Phases

### Phase 1: Backend Infrastructure (Week 1)
1. Create CosmosDB container for analysis_results
2. Implement AnalysisResultsService
3. Add API endpoints for saving/retrieving results
4. Test storage and retrieval

### Phase 2: PDF Generation (Week 2)
1. Install WeasyPrint: `pip install weasyprint`
2. Create HTML templates for both report types
3. Implement PDFGenerationService
4. Add PDF generation endpoint
5. Test PDF generation with sample data

### Phase 3: Email Integration (Week 3)
1. Set up Azure Communication Services Email
2. Implement EmailService
3. Add email endpoint
4. Test email delivery with attachments

### Phase 4: Frontend Integration (Week 4)
1. Create ResultsStorageService in Angular
2. Build PdfEmailActionsComponent
3. Integrate into Compare Contracts page
4. Integrate into Query Contracts page
5. Add user feedback (loading states, success/error messages)
6. End-to-end testing

### Phase 5: Polish & Optimization (Week 5)
1. Optimize PDF styling and pagination
2. Add result history page (view past reports)
3. Add bulk email functionality
4. Performance testing and optimization
5. Documentation

## Technology Stack Summary

### Backend
- **Storage**: CosmosDB (analysis_results container)
- **PDF Generation**: WeasyPrint (HTML/CSS to PDF)
- **Templates**: Jinja2 (Python templating)
- **Email**: Azure Communication Services Email
- **Framework**: FastAPI

### Frontend
- **Framework**: Angular
- **HTTP Client**: Angular HttpClient
- **UI Components**: Bootstrap + Custom components
- **Notifications**: ngx-toastr (for success/error messages)

## Configuration Requirements

### Environment Variables (`.env`)
```bash
# Email Service
AZURE_COMMUNICATION_EMAIL_CONNECTION_STRING=your_connection_string
EMAIL_FROM_ADDRESS=noreply@yourdomain.com

# PDF Generation
PDF_LOGO_PATH=web_app/static/images/logo.png
PDF_FOOTER_TEXT="Confidential - Internal Use Only"
```

### Python Dependencies (`requirements.txt`)
```
weasyprint==60.2
jinja2==3.1.2
azure-communication-email==1.0.0
```

## Cost Considerations

1. **CosmosDB Storage**: ~$0.25/GB/month (results are typically <1MB each)
2. **Azure Email**: ~$0.001 per email
3. **Compute**: Minimal - PDF generation is fast (<2 seconds per report)

## Security Considerations

1. **Access Control**: Verify user_id matches result owner
2. **Email Validation**: Sanitize and validate recipient addresses
3. **Rate Limiting**: Prevent email spam (max 10 emails per minute per user)
4. **PDF Size Limits**: Cap at 10MB to prevent abuse
5. **Data Retention**: Auto-delete results older than 90 days

## Future Enhancements

1. **Scheduled Reports**: Cron jobs for regular report generation
2. **PDF Customization**: User-selectable templates and branding
3. **Blob Storage**: Store generated PDFs in Azure Blob Storage for caching
4. **Analytics**: Track PDF downloads and email opens
5. **Export Formats**: Add Excel, Word export options

Would you like me to start implementing any specific phase?
