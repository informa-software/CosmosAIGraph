# Phase 2 Testing Guide - PDF Generation

## What We've Implemented

Phase 2 provides PDF generation functionality from stored analysis results:

✅ **PDF Generation Service**: `PDFGenerationService` with xhtml2pdf for HTML-to-PDF conversion
✅ **HTML Templates**: Jinja2 templates for comparison and query reports
✅ **CSS Styling**: Professional PDF styling with branding
✅ **API Endpoint**: `/api/analysis-results/results/{result_id}/pdf` for PDF download
✅ **Metadata Tracking**: PDF generation metadata stored with results

## Prerequisites

### 1. Complete Phase 1 Setup

Ensure Phase 1 is working:
```powershell
cd web_app

# Create analysis_results container
.\setup_analysis_results_container.ps1
```

### 2. Update Python Dependencies

```powershell
cd web_app

# Activate virtual environment (if not already active)
.\venv\Scripts\activate

# Install xhtml2pdf
pip install xhtml2pdf

# Or install all requirements
pip install -r requirements.in
```

**Note**: xhtml2pdf is pure Python and has no system dependencies, making it easy to install on Windows.

### 3. Start the Web Application

```powershell
cd web_app
.\web_app.ps1
```

The API will be available at: https://localhost:8000

## Testing the PDF Generation

### Step 1: Save a Query Result (Test Data)

First, create a test result to generate a PDF from.

**Endpoint:** `POST /api/analysis-results/query`

**Request Body:**
```json
{
  "user_id": "test@example.com",
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
    },
    {
      "contract_id": "contract_ghi_789",
      "filename": "TechCorp_SOW.json",
      "contract_title": "TechCorp Statement of Work"
    }
  ],
  "results": {
    "answer_summary": "Based on the analysis of indemnification clauses across the three contracts, the Westervelt Standard MSA provides the broadest indemnification coverage for the contracting party. This contract includes comprehensive third-party claims coverage, intellectual property indemnification, and unlimited liability provisions.",
    "ranked_contracts": [
      {
        "contract_id": "contract_abc_123",
        "filename": "Westervelt_Standard_MSA.json",
        "rank": 1,
        "score": 0.95,
        "reasoning": "This contract provides the most comprehensive indemnification coverage. It includes broad third-party claims protection, intellectual property indemnification, and does not cap liability for indemnification obligations. The language is favorable to the contracting party with minimal carve-outs.",
        "relevant_clauses": [
          {
            "clause_type": "Indemnification",
            "clause_text": "Contractor shall indemnify, defend, and hold harmless Contracting Party, its officers, directors, employees, and agents from and against any and all claims, damages, losses, and expenses, including reasonable attorneys' fees, arising out of or resulting from Contractor's performance of this Agreement, provided that such claim, damage, loss, or expense is attributable to bodily injury, sickness, disease or death, or to injury to or destruction of tangible property.",
            "analysis": "Broad indemnification covering all types of claims with no monetary cap. Favorable to contracting party."
          },
          {
            "clause_type": "Intellectual Property Indemnity",
            "clause_text": "Contractor warrants that all deliverables provided under this Agreement do not infringe any patent, copyright, trade secret, or other proprietary right of any third party. Contractor shall indemnify Contracting Party against all costs, expenses, and damages arising from any claim of such infringement.",
            "analysis": "Complete IP indemnification with no limitations or exclusions."
          }
        ]
      },
      {
        "contract_id": "contract_def_456",
        "filename": "ACME_Corp_Agreement.json",
        "rank": 2,
        "score": 0.72,
        "reasoning": "This contract offers moderate indemnification protection. While it covers third-party claims, it includes a cap on liability equal to the contract value and excludes certain types of damages. The scope is narrower than the Westervelt MSA.",
        "relevant_clauses": [
          {
            "clause_type": "Indemnification",
            "clause_text": "Contractor agrees to indemnify Contracting Party against third-party claims arising from Contractor's gross negligence or willful misconduct, up to an amount equal to the total fees paid under this Agreement.",
            "analysis": "Limited to gross negligence/willful misconduct with monetary cap. Less favorable than unlimited indemnity."
          }
        ]
      },
      {
        "contract_id": "contract_ghi_789",
        "filename": "TechCorp_SOW.json",
        "rank": 3,
        "score": 0.58,
        "reasoning": "This contract provides the most limited indemnification coverage. It includes multiple carve-outs, a low liability cap ($100,000), and excludes consequential damages entirely. The protection for the contracting party is minimal.",
        "relevant_clauses": [
          {
            "clause_type": "Indemnification",
            "clause_text": "Contractor shall indemnify Contracting Party for direct damages only, up to $100,000, arising from third-party claims related to bodily injury caused by Contractor's gross negligence. This indemnity excludes all consequential, indirect, and special damages.",
            "analysis": "Very narrow scope with low cap and significant exclusions. Least favorable to contracting party."
          }
        ]
      }
    ],
    "execution_metadata": {
      "contracts_analyzed": 3,
      "query_time_seconds": 4.8,
      "llm_model": "gpt-4"
    }
  },
  "metadata": {
    "title": "Indemnification Breadth Analysis",
    "description": "Comparative analysis of indemnification clauses across 3 contracts"
  }
}
```

**Expected Response:**
```json
{
  "result_id": "result_1729795300_abc12345",
  "message": "Query results saved successfully"
}
```

**Save the `result_id` for PDF generation!**
result_1761285225503_02ee988f
---

### Step 2: Generate PDF from Query Result

**Endpoint:** `GET /api/analysis-results/results/{result_id}/pdf?user_id=test@example.com`

**Using cURL:**
```bash
curl -X GET "https://localhost:8000/api/analysis-results/results/result_1729795300_abc12345/pdf?user_id=test@example.com" \
  --output query_report.pdf
```

**Using Browser:**
Navigate to: `https://localhost:8000/api/analysis-results/results/result_1729795300_abc12345/pdf?user_id=test@example.com`

The PDF should download automatically.

**Expected Outcome:**
- PDF file downloads with name like `query_report_20251023_143000.pdf`
- File size: 50-200 KB (depending on content)
- Professional formatting with:
  - Report header with title and metadata
  - Query text highlighted
  - Contracts analyzed table
  - Summary section
  - Ranked results with scores
  - Relevant clauses for each contract
  - Execution metadata footer

---

### Step 3: Save a Comparison Result (Test Data)

**Endpoint:** `POST /api/analysis-results/comparison`

**Request Body:**
```json
{
  "user_id": "test@example.com",
  "standard_contract_id": "contract_standard_001",
  "compare_contract_ids": [
    "contract_vendor_a",
    "contract_vendor_b"
  ],
  "comparison_mode": "full",
  "results": {
    "comparisons": [
      {
        "contract_id": "contract_vendor_a",
        "overall_similarity_score": 0.85,
        "risk_level": "low",
        "critical_findings": [
          "All standard clauses present",
          "No significant deviations detected",
          "Liability limits match standard template"
        ],
        "missing_clauses": [],
        "additional_clauses": [
          "Extended warranty (24 months)",
          "Price protection clause"
        ],
        "differences": [
          {
            "clause_type": "Payment Terms",
            "standard_text": "Net 30 days",
            "compared_text": "Net 45 days",
            "analysis": "Extended payment terms favor contractor. Low risk."
          }
        ]
      },
      {
        "contract_id": "contract_vendor_b",
        "overall_similarity_score": 0.62,
        "risk_level": "high",
        "critical_findings": [
          "Missing critical liability clause",
          "Indemnification scope significantly reduced",
          "No intellectual property protections"
        ],
        "missing_clauses": [
          "Limitation of Liability",
          "Intellectual Property Rights",
          "Data Protection Clause"
        ],
        "additional_clauses": [
          "Arbitration requirement (AAA rules)",
          "Forum selection (Delaware)"
        ],
        "differences": [
          {
            "clause_type": "Indemnification",
            "standard_text": "Contractor shall indemnify Client for all claims arising from Contractor's performance.",
            "compared_text": "Contractor shall indemnify Client only for claims arising from Contractor's gross negligence, up to $100,000.",
            "analysis": "Significantly narrowed indemnification with monetary cap. High risk to client."
          }
        ]
      }
    ],
    "summary": {
      "total_comparisons": 2,
      "average_similarity": 0.735,
      "high_risk_count": 1
    }
  },
  "metadata": {
    "title": "Vendor Contract Comparison",
    "description": "Comparison of vendor contracts against standard template",
    "execution_time_seconds": 5.2
  }
}
```

**Expected Response:**
```json
{
  "result_id": "result_1729795400_def67890",
  "message": "Comparison results saved successfully"
}
```

---

### Step 4: Generate PDF from Comparison Result

**Endpoint:** `GET /api/analysis-results/results/{result_id}/pdf?user_id=test@example.com`

**Using cURL:**
```bash
curl -X GET "https://localhost:8000/api/analysis-results/results/result_1729795400_def67890/pdf?user_id=test@example.com" \
  --output comparison_report.pdf
```

**Expected Outcome:**
- PDF file downloads with name like `comparison_report_20251023_143100.pdf`
- Professional formatting with:
  - Report header with comparison mode
  - Standard contract identifier
  - List of compared contracts
  - For each comparison:
    - Similarity score
    - Risk level badge (color-coded)
    - Critical findings list
    - Missing clauses (highlighted in red)
    - Additional clauses (highlighted in green)
    - Clause differences with side-by-side text
  - Summary statistics

---

### Step 5: Verify PDF Metadata

After generating a PDF, retrieve the result again to see the updated metadata.

**Endpoint:** `GET /api/analysis-results/results/{result_id}?user_id=test@example.com`

**Expected Response (partial):**
```json
{
  "id": "result_1729795300_abc12345",
  "result_id": "result_1729795300_abc12345",
  "result_type": "query",
  "user_id": "test@example.com",
  "created_at": "2025-10-23T14:30:00Z",
  "pdf_metadata": {
    "generated_at": "2025-10-23T14:35:00Z",
    "pdf_size_bytes": 125840,
    "filename": "query_result_1729795300_abc12345_20251023_143500.pdf"
  },
  ...
}
```

---

## Visual Inspection Checklist

When you open the generated PDFs, verify:

### Query Report PDF:
- [ ] Report title: "Contract Query Report"
- [ ] Report ID and generation timestamp visible
- [ ] Query text displayed in highlighted box
- [ ] Contracts analyzed table with all filenames
- [ ] Summary section with answer
- [ ] Ranked results (1, 2, 3) with visual differentiation
- [ ] Each result shows:
  - [ ] Rank number and score
  - [ ] Contract filename
  - [ ] Analysis/reasoning text
  - [ ] Relevant clauses (if present)
  - [ ] Clause text properly formatted
- [ ] Execution metadata at bottom
- [ ] Footer with generation timestamp

### Comparison Report PDF:
- [ ] Report title: "Contract Comparison Report"
- [ ] Comparison mode displayed (Full/Clauses)
- [ ] Standard contract ID shown
- [ ] Compared contracts listed in table
- [ ] Each comparison shows:
  - [ ] Contract ID
  - [ ] Risk level badge (with appropriate color)
  - [ ] Similarity score (%)
  - [ ] Critical findings list
  - [ ] Missing clauses (if any)
  - [ ] Additional clauses (if any)
  - [ ] Clause differences with standard vs. compared text
- [ ] Summary statistics
- [ ] Footer with generation timestamp

### General PDF Quality:
- [ ] Professional typography and spacing
- [ ] Page numbers (if multi-page)
- [ ] No text cutoffs or overflow
- [ ] Color-coding for risk levels
- [ ] Proper page breaks (no awkward splits)
- [ ] Tables render correctly
- [ ] File size reasonable (<500 KB for typical report)

---

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'xhtml2pdf'"
**Solution:** Install xhtml2pdf:
```powershell
cd web_app
.\venv\Scripts\activate
pip install xhtml2pdf
```

### Issue: "Template not found: query_report.html"
**Solution:** Verify templates directory structure:
```
web_app/
  templates/
    pdf/
      query_report.html
      comparison_report.html
      styles.css
```

### Issue: PDF downloads but is blank or malformed
**Solution:** Check logs for template rendering errors:
```powershell
# Check hypercorn logs for errors
# Look for Jinja2 template errors or CSS parsing issues
```

### Issue: "Result not found: {result_id}"
**Solution:** Verify the result was saved:
```bash
curl -X GET "https://localhost:8000/api/analysis-results/results/{result_id}?user_id=test@example.com"
```

---

## Performance Benchmarks

Expected performance (local development):

| Operation | Target Time |
|-----------|-------------|
| Simple query PDF (1-3 contracts) | < 2 seconds |
| Complex query PDF (10+ contracts, many clauses) | < 5 seconds |
| Simple comparison PDF (2-3 comparisons) | < 2 seconds |
| Complex comparison PDF (10+ comparisons) | < 5 seconds |

---

## Next Steps

Once Phase 2 testing is complete:

1. ✅ PDF generation working
2. ⏭️ **Phase 3**: Implement email service to send PDFs
3. ⏭️ **Phase 4**: Update Angular frontend to trigger PDF generation and email

---

## Success Criteria

Phase 2 is complete when:
- ✅ xhtml2pdf dependencies installed
- ✅ PDF endpoint returns properly formatted PDFs
- ✅ Query report PDFs render correctly
- ✅ Comparison report PDFs render correctly
- ✅ PDF metadata is stored with results
- ✅ No template rendering errors
- ✅ PDF file sizes are reasonable
- ✅ All visual elements display properly

---

**Phase 2 Complete!** 🎉

Ready to move to Phase 3 (Email Service) when you're ready.
