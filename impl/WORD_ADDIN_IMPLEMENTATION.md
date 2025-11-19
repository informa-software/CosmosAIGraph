# Word Add-in for Contract Compliance Analysis - Implementation Guide

**Version:** 1.0
**Date:** January 2025
**Target Platform:** Microsoft Word 2016+, Word Online

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema](#2-database-schema)
3. [Backend Implementation](#3-backend-implementation)
4. [Frontend Implementation](#4-frontend-implementation)
5. [Office Add-in Configuration](#5-office-add-in-configuration)
6. [Development Setup](#6-development-setup)
7. [Implementation Phases](#7-implementation-phases)
8. [Testing Guide](#8-testing-guide)
9. [Deployment Instructions](#9-deployment-instructions)

---

## 1. Architecture Overview

### 1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Microsoft Word                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │    Task Pane (Angular App - Port 4200)               │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ WordAddinModule (New)                           │ │  │
│  │  │  - DocumentAnalyzerComponent                    │ │  │
│  │  │  - AnalysisResultsComponent                     │ │  │
│  │  │  - WordIntegrationService                       │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │ ComplianceModule (Existing)                     │ │  │
│  │  │  - ComplianceService                            │ │  │
│  │  │  - RuleSetService                               │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│           Office.js API (Document Access)                    │
└─────────────────────────────────────────────────────────────┘
                           ↕ HTTPS (8000)
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ POST /api/compliance/evaluate/document-text          │  │
│  │ GET  /api/compliance/word-addin/evaluations          │  │
│  │ GET  /api/compliance/word-addin/evaluations/{id}     │  │
│  │ POST /api/compliance/word-addin/export-pdf           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ WordAddinEvaluationService (New)                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│         Azure CosmosDB NoSQL                                 │
│  - word_addin_evaluations (New Container)                   │
│  - compliance_rules (Existing)                               │
│  - rule_sets (Existing)                                      │
└─────────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────────┐
│              Azure OpenAI                                    │
│  - gpt-4 for compliance evaluation                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

**Document Analysis Flow:**
1. User triggers analysis in Word add-in
2. Office.js extracts document text + metadata
3. Angular app sends to backend API
4. Backend evaluates against selected rule set
5. Results stored in CosmosDB
6. Results returned to add-in
7. Add-in displays results and inserts comments/highlights

**PDF Export Flow:**
1. User clicks "Export PDF" button
2. Frontend sends evaluation_id to backend
3. Backend generates side-by-side PDF
4. PDF streamed back to browser for download

---

## 2. Database Schema

### 2.1 New Container: `word_addin_evaluations`

**Container Configuration:**
```json
{
  "id": "word_addin_evaluations",
  "partitionKey": {
    "paths": ["/evaluation_id"],
    "kind": "Hash"
  },
  "indexingPolicy": {
    "indexingMode": "consistent",
    "automatic": true,
    "includedPaths": [
      {"path": "/*"}
    ],
    "excludedPaths": [
      {"path": "/document_text/?"},
      {"path": "/_etag/?"}
    ]
  }
}
```

**Document Schema:**
```json
{
  "id": "eval_word_20250115_103045_abc123",
  "evaluation_id": "eval_word_20250115_103045_abc123",
  "doctype": "word_addin_evaluation",

  "document_metadata": {
    "filename": "Contract_ABC_Corp.docx",
    "title": "Master Service Agreement - ABC Corp",
    "author": "John Doe",
    "created_date": "2025-01-10T08:00:00Z",
    "word_version": "16.0.14326.20450",
    "user_email": "john.doe@company.com"
  },

  "document_text": "MASTER SERVICE AGREEMENT\n\nThis Agreement...",
  "document_scope": "entire | selection",
  "word_count": 2500,
  "char_count": 15000,

  "evaluation_config": {
    "rule_set_id": "ruleset_msa_20250101_120000",
    "rule_set_name": "MSA Compliance Rules",
    "rule_ids": ["rule_001", "rule_002", "rule_003"],
    "evaluation_mode": "sync"
  },

  "results": [
    {
      "rule_id": "rule_001",
      "rule_name": "Payment Terms Present",
      "rule_description": "Contract must specify payment terms",
      "severity": "high",
      "category": "payment_terms",
      "evaluation_result": "pass",
      "confidence": 0.95,
      "explanation": "Payment terms found in Section 3.2. Net 30 payment terms clearly specified.",
      "evidence": [
        "Net 30 payment terms specified",
        "Payment due within thirty (30) days of invoice date"
      ],
      "text_location": {
        "paragraph_index": 15,
        "section_name": "Payment Terms",
        "character_offset": 3250
      },
      "highlight_color": "green",
      "comment_text": "✅ Payment Terms Present - Payment terms found in Section 3.2. (Confidence: 95%)"
    },
    {
      "rule_id": "rule_002",
      "rule_name": "Liability Cap Required",
      "rule_description": "Contract must include limitation of liability clause",
      "severity": "critical",
      "category": "liability",
      "evaluation_result": "fail",
      "confidence": 0.92,
      "explanation": "No limitation of liability clause found in document. This is a critical requirement.",
      "evidence": [],
      "text_location": null,
      "highlight_color": "red",
      "comment_text": "❌ Liability Cap Required - No limitation of liability clause found. This is critical. (Confidence: 92%)"
    },
    {
      "rule_id": "rule_003",
      "rule_name": "Governing Law Specified",
      "rule_description": "Contract must specify governing law and jurisdiction",
      "severity": "medium",
      "category": "governing_law",
      "evaluation_result": "partial",
      "confidence": 0.78,
      "explanation": "Governing law mentioned but jurisdiction for disputes not clearly specified.",
      "evidence": [
        "This Agreement shall be governed by Delaware law"
      ],
      "text_location": {
        "paragraph_index": 45,
        "section_name": "Miscellaneous",
        "character_offset": 12500
      },
      "highlight_color": "yellow",
      "comment_text": "⚠️ Governing Law Specified - Law mentioned but jurisdiction unclear. (Confidence: 78%)"
    }
  ],

  "summary": {
    "total_rules": 10,
    "passed": 6,
    "failed": 3,
    "partial": 1,
    "not_applicable": 0,
    "pass_rate": 0.60,
    "overall_status": "needs_attention"
  },

  "evaluation_metadata": {
    "evaluated_date": "2025-01-15T10:30:45Z",
    "processing_time_ms": 3500,
    "source": "word_addin",
    "api_version": "1.0"
  },

  "annotations_applied": {
    "highlights_count": 8,
    "comments_count": 4,
    "applied_date": "2025-01-15T10:31:00Z"
  }
}
```

**Index Policy Details:**
- Exclude `document_text` from indexing (large field)
- Index all other fields for querying
- Partition by `evaluation_id` for efficient lookups

---

## 3. Backend Implementation

### 3.1 New Service: `WordAddinEvaluationService`

**File:** `web_app/src/services/word_addin_evaluation_service.py`

```python
"""
Word Add-in Evaluation Service

Handles document text evaluation and storage for Word add-in.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.compliance_evaluation_service import ComplianceEvaluationService
from src.services.compliance_rules_service import ComplianceRulesService
from src.services.rule_set_service import RuleSetService

logger = logging.getLogger(__name__)


class WordAddinEvaluationService:
    """Service for Word add-in document evaluations"""

    def __init__(
        self,
        cosmos_service: CosmosNoSQLService,
        rules_service: ComplianceRulesService,
        rule_set_service: RuleSetService,
        evaluation_service: ComplianceEvaluationService
    ):
        self.cosmos_service = cosmos_service
        self.rules_service = rules_service
        self.rule_set_service = rule_set_service
        self.evaluation_service = evaluation_service
        self.container_name = "word_addin_evaluations"

    async def evaluate_document_text(
        self,
        document_text: str,
        document_metadata: Dict[str, Any],
        rule_set_id: Optional[str] = None,
        rule_ids: Optional[List[str]] = None,
        document_scope: str = "entire"
    ) -> Dict[str, Any]:
        """
        Evaluate document text against compliance rules.

        Args:
            document_text: Full text content of the Word document
            document_metadata: Document metadata (title, author, filename, etc.)
            rule_set_id: Optional rule set ID to evaluate against
            rule_ids: Optional list of specific rule IDs
            document_scope: 'entire' or 'selection'

        Returns:
            Evaluation results with annotations
        """
        start_time = datetime.utcnow()

        try:
            # Generate evaluation ID
            evaluation_id = self._generate_evaluation_id()

            # Get rules to evaluate
            rules_to_evaluate = await self._get_rules_for_evaluation(
                rule_set_id, rule_ids
            )

            if not rules_to_evaluate:
                raise ValueError("No rules selected for evaluation")

            # Perform compliance evaluation
            evaluation_results = await self._evaluate_rules(
                document_text,
                rules_to_evaluate
            )

            # Calculate summary statistics
            summary = self._calculate_summary(evaluation_results)

            # Prepare annotations
            annotations = self._prepare_annotations(evaluation_results)

            # Build evaluation document
            evaluation_doc = {
                "id": evaluation_id,
                "evaluation_id": evaluation_id,
                "doctype": "word_addin_evaluation",
                "document_metadata": document_metadata,
                "document_text": document_text,
                "document_scope": document_scope,
                "word_count": len(document_text.split()),
                "char_count": len(document_text),
                "evaluation_config": {
                    "rule_set_id": rule_set_id,
                    "rule_set_name": await self._get_rule_set_name(rule_set_id) if rule_set_id else None,
                    "rule_ids": [r["rule_id"] for r in evaluation_results],
                    "evaluation_mode": "sync"
                },
                "results": evaluation_results,
                "summary": summary,
                "evaluation_metadata": {
                    "evaluated_date": datetime.utcnow().isoformat() + "Z",
                    "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    "source": "word_addin",
                    "api_version": "1.0"
                },
                "annotations_applied": {
                    "highlights_count": 0,
                    "comments_count": 0,
                    "applied_date": None
                }
            }

            # Store in CosmosDB
            await self._store_evaluation(evaluation_doc)

            logger.info(f"Word add-in evaluation completed: {evaluation_id}")

            return {
                "evaluation_id": evaluation_id,
                "results": evaluation_results,
                "summary": summary,
                "annotations": annotations,
                "document_metadata": document_metadata
            }

        except Exception as e:
            logger.error(f"Error evaluating document text: {str(e)}")
            raise

    async def get_evaluation(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Get evaluation by ID"""
        try:
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.point_read(evaluation_id, evaluation_id)
            return doc
        except Exception as e:
            logger.error(f"Error retrieving evaluation {evaluation_id}: {str(e)}")
            return None

    async def list_evaluations(
        self,
        limit: int = 50,
        user_email: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List recent evaluations"""
        try:
            self.cosmos_service.set_container(self.container_name)

            if user_email:
                query = """
                    SELECT * FROM c
                    WHERE c.doctype = 'word_addin_evaluation'
                    AND c.document_metadata.user_email = @user_email
                    ORDER BY c.evaluation_metadata.evaluated_date DESC
                    OFFSET 0 LIMIT @limit
                """
                params = [
                    {"name": "@user_email", "value": user_email},
                    {"name": "@limit", "value": limit}
                ]
            else:
                query = """
                    SELECT * FROM c
                    WHERE c.doctype = 'word_addin_evaluation'
                    ORDER BY c.evaluation_metadata.evaluated_date DESC
                    OFFSET 0 LIMIT @limit
                """
                params = [{"name": "@limit", "value": limit}]

            results = await self.cosmos_service.query_items(
                query,
                parameters=params,
                cross_partition=True
            )
            return results

        except Exception as e:
            logger.error(f"Error listing evaluations: {str(e)}")
            return []

    def _generate_evaluation_id(self) -> str:
        """Generate unique evaluation ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"eval_word_{timestamp}_{unique_id}"

    async def _get_rules_for_evaluation(
        self,
        rule_set_id: Optional[str],
        rule_ids: Optional[List[str]]
    ) -> List[Any]:
        """Get rules to evaluate (from rule set or specific IDs)"""
        if rule_set_id:
            # Get all rules from rule set
            rule_set = await self.rule_set_service.get_rule_set(rule_set_id)
            if not rule_set:
                raise ValueError(f"Rule set not found: {rule_set_id}")

            rules = []
            for rule_id in rule_set.rule_ids:
                rule = await self.rules_service.get_rule(rule_id)
                if rule and rule.active:
                    rules.append(rule)
            return rules
        elif rule_ids:
            # Get specific rules
            rules = []
            for rule_id in rule_ids:
                rule = await self.rules_service.get_rule(rule_id)
                if rule and rule.active:
                    rules.append(rule)
            return rules
        else:
            raise ValueError("Must provide either rule_set_id or rule_ids")

    async def _get_rule_set_name(self, rule_set_id: str) -> Optional[str]:
        """Get rule set name"""
        rule_set = await self.rule_set_service.get_rule_set(rule_set_id)
        return rule_set.name if rule_set else None

    async def _evaluate_rules(
        self,
        document_text: str,
        rules: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate document text against rules using AI.

        NOTE: This is a simplified version. In production, this would:
        1. Call Azure OpenAI with proper prompt engineering
        2. Handle rate limiting and retries
        3. Parse structured responses
        """
        results = []

        for rule in rules:
            try:
                # TODO: Implement actual AI evaluation
                # For now, return mock structure
                result = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_description": rule.description,
                    "severity": rule.severity,
                    "category": rule.category,
                    "evaluation_result": "pass",  # TODO: AI evaluation
                    "confidence": 0.85,
                    "explanation": f"Evaluated against: {rule.description}",
                    "evidence": [],
                    "text_location": None,
                    "highlight_color": self._get_highlight_color("pass"),
                    "comment_text": self._format_comment("pass", rule.name, "Evaluated successfully", 0.85)
                }
                results.append(result)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {str(e)}")
                continue

        return results

    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        total = len(results)
        passed = sum(1 for r in results if r["evaluation_result"] == "pass")
        failed = sum(1 for r in results if r["evaluation_result"] == "fail")
        partial = sum(1 for r in results if r["evaluation_result"] == "partial")
        not_applicable = sum(1 for r in results if r["evaluation_result"] == "not_applicable")

        pass_rate = passed / total if total > 0 else 0.0

        if pass_rate >= 0.8:
            overall_status = "compliant"
        elif pass_rate >= 0.6:
            overall_status = "needs_attention"
        else:
            overall_status = "non_compliant"

        return {
            "total_rules": total,
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "not_applicable": not_applicable,
            "pass_rate": round(pass_rate, 2),
            "overall_status": overall_status
        }

    def _prepare_annotations(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare annotation data for Word add-in"""
        highlights = []
        comments = []

        for result in results:
            if result["evaluation_result"] != "not_applicable":
                # Prepare highlight
                if result["text_location"]:
                    highlights.append({
                        "rule_id": result["rule_id"],
                        "color": result["highlight_color"],
                        "location": result["text_location"]
                    })

                # Prepare comment
                comments.append({
                    "rule_id": result["rule_id"],
                    "text": result["comment_text"],
                    "location": result["text_location"]
                })

        return {
            "highlights": highlights,
            "comments": comments
        }

    def _get_highlight_color(self, evaluation_result: str) -> str:
        """Get highlight color based on result"""
        color_map = {
            "pass": "green",
            "fail": "red",
            "partial": "yellow",
            "not_applicable": "gray"
        }
        return color_map.get(evaluation_result, "gray")

    def _format_comment(
        self,
        evaluation_result: str,
        rule_name: str,
        explanation: str,
        confidence: float
    ) -> str:
        """Format comment text"""
        emoji_map = {
            "pass": "✅",
            "fail": "❌",
            "partial": "⚠️",
            "not_applicable": "ℹ️"
        }
        emoji = emoji_map.get(evaluation_result, "ℹ️")

        return f"{emoji} {rule_name} - {explanation} (Confidence: {int(confidence * 100)}%)"

    async def _store_evaluation(self, evaluation_doc: Dict[str, Any]) -> None:
        """Store evaluation in CosmosDB"""
        try:
            self.cosmos_service.set_container(self.container_name)
            await self.cosmos_service.create_item(evaluation_doc)
            logger.info(f"Stored evaluation: {evaluation_doc['evaluation_id']}")
        except Exception as e:
            logger.error(f"Error storing evaluation: {str(e)}")
            raise
```

### 3.2 New API Endpoints

**File:** `web_app/routers/word_addin_router.py`

```python
"""
Word Add-in Router

API endpoints for Word add-in functionality.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
from src.services.compliance_rules_service import ComplianceRulesService
from src.services.compliance_evaluation_service import ComplianceEvaluationService
from src.services.evaluation_job_service import EvaluationJobService
from src.services.rule_set_service import RuleSetService
from src.services.word_addin_evaluation_service import WordAddinEvaluationService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/compliance/word-addin",
    tags=["word-addin"]
)


# ============================================================================
# Pydantic Models
# ============================================================================

class DocumentMetadata(BaseModel):
    """Document metadata from Word"""
    filename: str = Field(..., description="Document filename")
    title: Optional[str] = Field(None, description="Document title")
    author: Optional[str] = Field(None, description="Document author")
    created_date: Optional[str] = Field(None, description="Document creation date")
    word_version: Optional[str] = Field(None, description="Word version")
    user_email: Optional[str] = Field(None, description="User email")


class EvaluateDocumentTextRequest(BaseModel):
    """Request to evaluate document text"""
    document_text: str = Field(..., min_length=1, description="Full document text")
    document_metadata: DocumentMetadata = Field(..., description="Document metadata")
    document_scope: str = Field(default="entire", pattern="^(entire|selection)$")
    rule_set_id: Optional[str] = Field(None, description="Rule set ID to evaluate")
    rule_ids: Optional[List[str]] = Field(None, description="Specific rule IDs")


class EvaluateDocumentTextResponse(BaseModel):
    """Response from document evaluation"""
    evaluation_id: str
    results: List[dict]
    summary: dict
    annotations: dict
    document_metadata: dict


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_services():
    """Initialize and return all required services"""
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()
    cosmos_service.set_db(ConfigService.graph_source_db())

    ai_service = AiService()

    rules_service = ComplianceRulesService(cosmos_service)
    job_service = EvaluationJobService(cosmos_service)
    evaluation_service = ComplianceEvaluationService(
        cosmos_service,
        rules_service,
        job_service,
        ai_service
    )

    rule_set_service = RuleSetService()
    await rule_set_service.initialize()

    word_addin_service = WordAddinEvaluationService(
        cosmos_service,
        rules_service,
        rule_set_service,
        evaluation_service
    )

    return {
        "word_addin": word_addin_service,
        "rule_sets": rule_set_service,
        "rules": rules_service
    }


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/evaluate", response_model=EvaluateDocumentTextResponse)
async def evaluate_document_text(
    request: EvaluateDocumentTextRequest,
    services: dict = Depends(get_services)
):
    """
    Evaluate document text from Word add-in against compliance rules.

    This endpoint:
    - Accepts raw document text (not contract_id)
    - Evaluates against rule set or specific rules
    - Stores evaluation with full document text
    - Returns results with annotation data
    """
    try:
        result = await services["word_addin"].evaluate_document_text(
            document_text=request.document_text,
            document_metadata=request.document_metadata.model_dump(),
            rule_set_id=request.rule_set_id,
            rule_ids=request.rule_ids,
            document_scope=request.document_scope
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error evaluating document text: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please try again or contact support."
        )


@router.get("/evaluations/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    services: dict = Depends(get_services)
):
    """Get a specific evaluation by ID"""
    try:
        evaluation = await services["word_addin"].get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        return evaluation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluations")
async def list_evaluations(
    limit: int = 50,
    user_email: Optional[str] = None,
    services: dict = Depends(get_services)
):
    """List recent evaluations"""
    try:
        evaluations = await services["word_addin"].list_evaluations(
            limit=limit,
            user_email=user_email
        )

        return {
            "evaluations": evaluations,
            "total": len(evaluations)
        }

    except Exception as e:
        logger.error(f"Error listing evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 3.3 Register Router

**File:** `web_app/web_app.py`

Add the new router:

```python
from routers import word_addin_router

# Register routers
app.include_router(word_addin_router.router)
```

---

## 4. Frontend Implementation

### 4.1 New Module Structure

```
query-builder/src/app/
├── word-addin/                          (NEW MODULE)
│   ├── word-addin.module.ts
│   ├── word-addin-routing.module.ts
│   ├── components/
│   │   ├── document-analyzer/
│   │   │   ├── document-analyzer.component.ts
│   │   │   ├── document-analyzer.component.html
│   │   │   └── document-analyzer.component.scss
│   │   ├── analysis-results/
│   │   │   ├── analysis-results.component.ts
│   │   │   ├── analysis-results.component.html
│   │   │   └── analysis-results.component.scss
│   │   └── evaluation-history/
│   │       ├── evaluation-history.component.ts
│   │       ├── evaluation-history.component.html
│   │       └── evaluation-history.component.scss
│   ├── services/
│   │   ├── word-integration.service.ts
│   │   └── word-addin-evaluation.service.ts
│   └── models/
│       └── word-addin.models.ts
└── compliance/                          (EXISTING)
    └── services/
        └── compliance.service.ts        (Extend)
```

### 4.2 Word Add-in Models

**File:** `query-builder/src/app/word-addin/models/word-addin.models.ts`

```typescript
// Word Add-in specific models

export interface DocumentMetadata {
  filename: string;
  title?: string;
  author?: string;
  created_date?: string;
  word_version?: string;
  user_email?: string;
}

export interface EvaluateDocumentTextRequest {
  document_text: string;
  document_metadata: DocumentMetadata;
  document_scope: 'entire' | 'selection';
  rule_set_id?: string;
  rule_ids?: string[];
}

export interface TextLocation {
  paragraph_index?: number;
  section_name?: string;
  character_offset?: number;
}

export interface RuleEvaluationResult {
  rule_id: string;
  rule_name: string;
  rule_description: string;
  severity: string;
  category: string;
  evaluation_result: 'pass' | 'fail' | 'partial' | 'not_applicable';
  confidence: number;
  explanation: string;
  evidence: string[];
  text_location: TextLocation | null;
  highlight_color: string;
  comment_text: string;
}

export interface EvaluationSummary {
  total_rules: number;
  passed: number;
  failed: number;
  partial: number;
  not_applicable: number;
  pass_rate: number;
  overall_status: 'compliant' | 'needs_attention' | 'non_compliant';
}

export interface AnnotationData {
  highlights: Array<{
    rule_id: string;
    color: string;
    location: TextLocation;
  }>;
  comments: Array<{
    rule_id: string;
    text: string;
    location: TextLocation | null;
  }>;
}

export interface EvaluateDocumentTextResponse {
  evaluation_id: string;
  results: RuleEvaluationResult[];
  summary: EvaluationSummary;
  annotations: AnnotationData;
  document_metadata: DocumentMetadata;
}

export interface WordAddinEvaluation {
  id: string;
  evaluation_id: string;
  document_metadata: DocumentMetadata;
  document_scope: string;
  summary: EvaluationSummary;
  evaluation_metadata: {
    evaluated_date: string;
    processing_time_ms: number;
  };
}
```

### 4.3 Word Integration Service

**File:** `query-builder/src/app/word-addin/services/word-integration.service.ts`

```typescript
import { Injectable } from '@angular/core';

// Declare Office global for TypeScript
declare const Office: any;
declare const Word: any;

@Injectable({
  providedIn: 'root'
})
export class WordIntegrationService {
  private initialized = false;
  private context: any = null;

  constructor() {}

  /**
   * Initialize Office.js
   */
  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (typeof Office === 'undefined') {
        reject(new Error('Office.js not loaded'));
        return;
      }

      Office.onReady((info: any) => {
        if (info.host === Office.HostType.Word) {
          this.initialized = true;
          this.context = Office.context;
          console.log('Word add-in initialized');
          resolve();
        } else {
          reject(new Error('Not running in Word'));
        }
      });
    });
  }

  /**
   * Check if Office.js is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Get entire document text
   */
  async getDocumentText(): Promise<string> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      const body = context.document.body;
      body.load('text');

      await context.sync();

      return body.text;
    });
  }

  /**
   * Get selected text
   */
  async getSelectedText(): Promise<string> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      const selection = context.document.getSelection();
      selection.load('text');

      await context.sync();

      if (!selection.text || selection.text.trim() === '') {
        throw new Error('No text selected');
      }

      return selection.text;
    });
  }

  /**
   * Get document metadata
   */
  async getDocumentMetadata(): Promise<any> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      const properties = context.document.properties;
      properties.load(['title', 'author', 'creationDate']);

      await context.sync();

      // Get additional metadata
      const filename = this.context.document.url
        ? this.context.document.url.split('/').pop() || 'Untitled.docx'
        : 'Untitled.docx';

      return {
        filename: filename,
        title: properties.title || filename,
        author: properties.author || 'Unknown',
        created_date: properties.creationDate?.toISOString() || new Date().toISOString(),
        word_version: Office.context.diagnostics.version,
        user_email: Office.context.mailbox?.userProfile?.emailAddress || null
      };
    });
  }

  /**
   * Highlight text with specified color
   */
  async highlightText(
    searchText: string,
    color: 'red' | 'green' | 'yellow' | 'gray'
  ): Promise<void> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      const searchResults = context.document.body.search(searchText, {
        matchCase: false,
        matchWholeWord: false
      });

      searchResults.load('font');
      await context.sync();

      // Map colors to Word highlight colors
      const colorMap: { [key: string]: any } = {
        red: Word.HighlightColor.red,
        green: Word.HighlightColor.green,
        yellow: Word.HighlightColor.yellow,
        gray: Word.HighlightColor.gray
      };

      for (let i = 0; i < searchResults.items.length; i++) {
        searchResults.items[i].font.highlightColor = colorMap[color];
      }

      await context.sync();
    });
  }

  /**
   * Insert comment at specified location
   */
  async insertComment(
    commentText: string,
    searchText?: string
  ): Promise<void> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      let range;

      if (searchText) {
        // Find text and add comment there
        const searchResults = context.document.body.search(searchText, {
          matchCase: false,
          matchWholeWord: false
        });

        searchResults.load();
        await context.sync();

        if (searchResults.items.length > 0) {
          range = searchResults.items[0];
        } else {
          // If not found, add at end of document
          range = context.document.body.getRange(Word.RangeLocation.end);
        }
      } else {
        // Add at end of document
        range = context.document.body.getRange(Word.RangeLocation.end);
      }

      range.insertComment(commentText);

      await context.sync();
    });
  }

  /**
   * Clear all highlights
   */
  async clearAllHighlights(): Promise<void> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      const body = context.document.body;
      body.font.highlightColor = null;

      await context.sync();
    });
  }

  /**
   * Get word count
   */
  async getWordCount(): Promise<number> {
    if (!this.initialized) {
      throw new Error('Word integration not initialized');
    }

    return Word.run(async (context: any) => {
      const body = context.document.body;
      body.load('text');

      await context.sync();

      const words = body.text.trim().split(/\s+/);
      return words.length;
    });
  }
}
```

### 4.4 Word Add-in Evaluation Service

**File:** `query-builder/src/app/word-addin/services/word-addin-evaluation.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  EvaluateDocumentTextRequest,
  EvaluateDocumentTextResponse,
  WordAddinEvaluation
} from '../models/word-addin.models';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class WordAddinEvaluationService {
  private readonly baseUrl = `${environment.apiBaseUrl}/api/compliance/word-addin`;

  constructor(private http: HttpClient) {}

  /**
   * Evaluate document text
   */
  evaluateDocumentText(
    request: EvaluateDocumentTextRequest
  ): Observable<EvaluateDocumentTextResponse> {
    return this.http.post<EvaluateDocumentTextResponse>(
      `${this.baseUrl}/evaluate`,
      request
    );
  }

  /**
   * Get evaluation by ID
   */
  getEvaluation(evaluationId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/evaluations/${evaluationId}`);
  }

  /**
   * List evaluations
   */
  listEvaluations(
    limit: number = 50,
    userEmail?: string
  ): Observable<{ evaluations: WordAddinEvaluation[]; total: number }> {
    let url = `${this.baseUrl}/evaluations?limit=${limit}`;
    if (userEmail) {
      url += `&user_email=${encodeURIComponent(userEmail)}`;
    }
    return this.http.get<{ evaluations: WordAddinEvaluation[]; total: number }>(url);
  }
}
```

### 4.5 Document Analyzer Component

**File:** `query-builder/src/app/word-addin/components/document-analyzer/document-analyzer.component.ts`

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WordIntegrationService } from '../../services/word-integration.service';
import { WordAddinEvaluationService } from '../../services/word-addin-evaluation.service';
import { RuleSetService } from '../../../compliance/services/rule-set.service';
import { ToastService } from '../../../shared/services/toast.service';
import {
  DocumentMetadata,
  EvaluateDocumentTextRequest,
  EvaluateDocumentTextResponse,
  RuleSetWithRuleCount
} from '../../models/word-addin.models';

@Component({
  selector: 'app-document-analyzer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './document-analyzer.component.html',
  styleUrls: ['./document-analyzer.component.scss']
})
export class DocumentAnalyzerComponent implements OnInit {
  // State
  documentScope: 'entire' | 'selection' = 'entire';
  selectedRuleSetId: string = '';
  analyzing: boolean = false;
  progress: number = 0;

  // Data
  ruleSets: RuleSetWithRuleCount[] = [];
  results: EvaluateDocumentTextResponse | null = null;
  error: string | null = null;

  // Metadata
  documentMetadata: DocumentMetadata | null = null;
  wordCount: number = 0;

  constructor(
    private wordService: WordIntegrationService,
    private evaluationService: WordAddinEvaluationService,
    private ruleSetService: RuleSetService,
    private toastService: ToastService
  ) {}

  async ngOnInit(): Promise<void> {
    try {
      // Initialize Word integration
      await this.wordService.initialize();

      // Load metadata
      await this.loadDocumentMetadata();

      // Load rule sets
      this.loadRuleSets();

    } catch (error: any) {
      console.error('Initialization error:', error);
      this.error = 'Failed to initialize add-in. Please reload.';
      this.toastService.error('Initialization failed');
    }
  }

  /**
   * Load document metadata
   */
  async loadDocumentMetadata(): Promise<void> {
    try {
      this.documentMetadata = await this.wordService.getDocumentMetadata();
      this.wordCount = await this.wordService.getWordCount();
    } catch (error) {
      console.error('Error loading metadata:', error);
    }
  }

  /**
   * Load available rule sets
   */
  loadRuleSets(): void {
    this.ruleSetService.getRuleSetsWithCounts(false).subscribe({
      next: (ruleSets) => {
        this.ruleSets = ruleSets.filter(rs => rs.is_active);
      },
      error: (error) => {
        console.error('Error loading rule sets:', error);
        this.toastService.error('Failed to load rule sets');
      }
    });
  }

  /**
   * Analyze document
   */
  async analyzeDocument(): Promise<void> {
    if (!this.selectedRuleSetId) {
      this.toastService.warning('Please select a rule set');
      return;
    }

    this.analyzing = true;
    this.error = null;
    this.progress = 10;

    try {
      // Get document text
      let documentText: string;

      if (this.documentScope === 'entire') {
        documentText = await this.wordService.getDocumentText();
      } else {
        documentText = await this.wordService.getSelectedText();
      }

      this.progress = 30;

      if (!documentText || documentText.trim() === '') {
        throw new Error('No text to analyze');
      }

      // Prepare request
      const request: EvaluateDocumentTextRequest = {
        document_text: documentText,
        document_metadata: this.documentMetadata!,
        document_scope: this.documentScope,
        rule_set_id: this.selectedRuleSetId
      };

      this.progress = 50;

      // Call API
      this.evaluationService.evaluateDocumentText(request).subscribe({
        next: async (response) => {
          this.progress = 80;
          this.results = response;

          // Apply annotations
          await this.applyAnnotations(response);

          this.progress = 100;
          this.analyzing = false;

          this.toastService.success('Analysis complete!');
        },
        error: (error) => {
          console.error('Analysis error:', error);
          this.error = 'Analysis failed. Please try again.';
          this.analyzing = false;
          this.progress = 0;
          this.toastService.error('Analysis failed');
        }
      });

    } catch (error: any) {
      console.error('Error during analysis:', error);
      this.error = error.message || 'Failed to analyze document';
      this.analyzing = false;
      this.progress = 0;
      this.toastService.error(this.error);
    }
  }

  /**
   * Apply highlights and comments to document
   */
  async applyAnnotations(response: EvaluateDocumentTextResponse): Promise<void> {
    try {
      // Clear existing highlights
      await this.wordService.clearAllHighlights();

      // Apply highlights
      for (const highlight of response.annotations.highlights) {
        // Find corresponding result for evidence text
        const result = response.results.find(r => r.rule_id === highlight.rule_id);
        if (result && result.evidence.length > 0) {
          // Highlight first evidence text
          await this.wordService.highlightText(
            result.evidence[0],
            highlight.color as any
          );
        }
      }

      // Apply comments
      for (const comment of response.annotations.comments) {
        const result = response.results.find(r => r.rule_id === comment.rule_id);
        if (result && result.evidence.length > 0) {
          // Insert comment at first evidence location
          await this.wordService.insertComment(
            comment.text,
            result.evidence[0]
          );
        }
      }

      this.toastService.success('Annotations applied');

    } catch (error) {
      console.error('Error applying annotations:', error);
      this.toastService.warning('Some annotations could not be applied');
    }
  }

  /**
   * Get rule set name
   */
  getRuleSetName(): string {
    const ruleSet = this.ruleSets.find(rs => rs.id === this.selectedRuleSetId);
    return ruleSet ? ruleSet.name : '';
  }

  /**
   * Get pass rate percentage
   */
  getPassRatePercentage(): number {
    return this.results ? Math.round(this.results.summary.pass_rate * 100) : 0;
  }

  /**
   * Get overall status badge class
   */
  getStatusBadgeClass(): string {
    if (!this.results) return 'badge-secondary';

    const status = this.results.summary.overall_status;
    if (status === 'compliant') return 'badge-success';
    if (status === 'needs_attention') return 'badge-warning';
    return 'badge-danger';
  }
}
```

**File:** `query-builder/src/app/word-addin/components/document-analyzer/document-analyzer.component.html`

```html
<div class="document-analyzer-container">
  <!-- Header -->
  <div class="addin-header">
    <h3>📄 Contract Compliance Analyzer</h3>
    <p class="subtitle">Analyze your document against compliance rules</p>
  </div>

  <!-- Error Message -->
  <div *ngIf="error" class="alert alert-danger">
    <strong>Error:</strong> {{ error }}
  </div>

  <!-- Configuration Panel -->
  <div class="config-panel" *ngIf="!analyzing && !results">
    <!-- Document Info -->
    <div class="info-section" *ngIf="documentMetadata">
      <h4>Document Information</h4>
      <div class="info-row">
        <span class="info-label">Filename:</span>
        <span class="info-value">{{ documentMetadata.filename }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Word Count:</span>
        <span class="info-value">{{ wordCount | number }}</span>
      </div>
    </div>

    <!-- Scope Selection -->
    <div class="form-group">
      <label>📄 Document Scope</label>
      <div class="radio-group">
        <label class="radio-label">
          <input
            type="radio"
            [(ngModel)]="documentScope"
            value="entire"
            [disabled]="analyzing"
          />
          Entire Document
        </label>
        <label class="radio-label">
          <input
            type="radio"
            [(ngModel)]="documentScope"
            value="selection"
            [disabled]="analyzing"
          />
          Selected Text
        </label>
      </div>
    </div>

    <!-- Rule Set Selection -->
    <div class="form-group">
      <label for="rule-set-select">📋 Rule Set</label>
      <select
        id="rule-set-select"
        [(ngModel)]="selectedRuleSetId"
        class="form-select"
        [disabled]="analyzing"
      >
        <option value="">-- Select Rule Set --</option>
        <option *ngFor="let ruleSet of ruleSets" [value]="ruleSet.id">
          {{ ruleSet.name }} ({{ ruleSet.rule_count }} rules)
        </option>
      </select>
    </div>

    <!-- Analyze Button -->
    <button
      class="btn btn-primary btn-block"
      (click)="analyzeDocument()"
      [disabled]="!selectedRuleSetId || analyzing"
    >
      <span *ngIf="!analyzing">🔍 Analyze Document</span>
      <span *ngIf="analyzing">⏳ Analyzing...</span>
    </button>
  </div>

  <!-- Progress -->
  <div class="progress-panel" *ngIf="analyzing">
    <div class="spinner"></div>
    <p class="progress-text">Analyzing document...</p>
    <div class="progress-bar-container">
      <div class="progress-bar" [style.width.%]="progress"></div>
    </div>
    <p class="progress-percentage">{{ progress }}%</p>
  </div>

  <!-- Results Panel -->
  <div class="results-panel" *ngIf="results && !analyzing">
    <!-- Summary -->
    <div class="results-summary">
      <h4>Analysis Results</h4>

      <div class="summary-stats">
        <div class="stat-card">
          <div class="stat-value">{{ getPassRatePercentage() }}%</div>
          <div class="stat-label">Pass Rate</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ results.summary.passed }}</div>
          <div class="stat-label">Passed</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ results.summary.failed }}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>

      <div class="overall-status">
        <span [class]="'badge ' + getStatusBadgeClass()">
          {{ results.summary.overall_status | uppercase }}
        </span>
      </div>
    </div>

    <!-- Rule Results -->
    <div class="results-list">
      <h5>Rule Details</h5>
      <div
        class="result-item"
        *ngFor="let result of results.results"
        [class.result-pass]="result.evaluation_result === 'pass'"
        [class.result-fail]="result.evaluation_result === 'fail'"
        [class.result-partial]="result.evaluation_result === 'partial'"
      >
        <div class="result-header">
          <span class="result-icon">
            <span *ngIf="result.evaluation_result === 'pass'">✅</span>
            <span *ngIf="result.evaluation_result === 'fail'">❌</span>
            <span *ngIf="result.evaluation_result === 'partial'">⚠️</span>
          </span>
          <span class="result-name">{{ result.rule_name }}</span>
        </div>
        <div class="result-explanation">
          {{ result.explanation }}
        </div>
        <div class="result-confidence">
          Confidence: {{ (result.confidence * 100).toFixed(0) }}%
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="results-actions">
      <button class="btn btn-outline" (click)="results = null">
        🔄 New Analysis
      </button>
      <button class="btn btn-primary" disabled>
        📊 Export PDF (Coming Soon)
      </button>
    </div>
  </div>
</div>
```

**File:** `query-builder/src/app/word-addin/components/document-analyzer/document-analyzer.component.scss`

```scss
.document-analyzer-container {
  padding: 16px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.addin-header {
  text-align: center;
  margin-bottom: 24px;

  h3 {
    margin: 0 0 8px 0;
    color: #2b579a;
    font-size: 20px;
  }

  .subtitle {
    margin: 0;
    color: #666;
    font-size: 14px;
  }
}

.alert {
  padding: 12px;
  margin-bottom: 16px;
  border-radius: 4px;

  &.alert-danger {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
  }
}

.config-panel {
  .info-section {
    background: #f5f5f5;
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 4px;

    h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: #333;
    }

    .info-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 13px;

      .info-label {
        font-weight: 600;
        color: #666;
      }

      .info-value {
        color: #333;
      }
    }
  }

  .form-group {
    margin-bottom: 16px;

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      font-size: 14px;
      color: #333;
    }

    .radio-group {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .radio-label {
        display: flex;
        align-items: center;
        font-weight: normal;
        font-size: 14px;
        cursor: pointer;

        input[type="radio"] {
          margin-right: 8px;
        }
      }
    }

    .form-select {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: #2b579a;
      }
    }
  }

  .btn-block {
    width: 100%;
    padding: 12px;
    font-size: 16px;
    font-weight: 600;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;

    &.btn-primary {
      background-color: #2b579a;
      color: white;

      &:hover:not(:disabled) {
        background-color: #1e4279;
      }

      &:disabled {
        background-color: #ccc;
        cursor: not-allowed;
      }
    }
  }
}

.progress-panel {
  text-align: center;
  padding: 32px 0;

  .spinner {
    width: 40px;
    height: 40px;
    margin: 0 auto 16px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #2b579a;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .progress-text {
    font-size: 16px;
    color: #333;
    margin-bottom: 16px;
  }

  .progress-bar-container {
    width: 100%;
    height: 8px;
    background: #f0f0f0;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 8px;

    .progress-bar {
      height: 100%;
      background: #2b579a;
      transition: width 0.3s ease;
    }
  }

  .progress-percentage {
    font-size: 14px;
    color: #666;
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.results-panel {
  .results-summary {
    background: #f9f9f9;
    padding: 16px;
    margin-bottom: 16px;
    border-radius: 4px;

    h4 {
      margin: 0 0 16px 0;
      color: #333;
      font-size: 16px;
    }

    .summary-stats {
      display: flex;
      justify-content: space-around;
      margin-bottom: 16px;

      .stat-card {
        text-align: center;

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: #2b579a;
        }

        .stat-label {
          font-size: 12px;
          color: #666;
        }
      }
    }

    .overall-status {
      text-align: center;

      .badge {
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;

        &.badge-success {
          background-color: #d4edda;
          color: #155724;
        }

        &.badge-warning {
          background-color: #fff3cd;
          color: #856404;
        }

        &.badge-danger {
          background-color: #f8d7da;
          color: #721c24;
        }
      }
    }
  }

  .results-list {
    margin-bottom: 16px;

    h5 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    }

    .result-item {
      background: white;
      border-left: 4px solid #ccc;
      padding: 12px;
      margin-bottom: 12px;
      border-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);

      &.result-pass {
        border-left-color: #28a745;
      }

      &.result-fail {
        border-left-color: #dc3545;
      }

      &.result-partial {
        border-left-color: #ffc107;
      }

      .result-header {
        display: flex;
        align-items: center;
        margin-bottom: 8px;

        .result-icon {
          font-size: 18px;
          margin-right: 8px;
        }

        .result-name {
          font-weight: 600;
          font-size: 14px;
          color: #333;
        }
      }

      .result-explanation {
        font-size: 13px;
        color: #666;
        margin-bottom: 8px;
        line-height: 1.4;
      }

      .result-confidence {
        font-size: 12px;
        color: #999;
      }
    }
  }

  .results-actions {
    display: flex;
    gap: 8px;

    .btn {
      flex: 1;
      padding: 10px;
      font-size: 14px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;

      &.btn-outline {
        background: white;
        border: 1px solid #2b579a;
        color: #2b579a;

        &:hover {
          background: #f0f5ff;
        }
      }

      &.btn-primary {
        background: #2b579a;
        color: white;

        &:hover:not(:disabled) {
          background: #1e4279;
        }

        &:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
      }
    }
  }
}
```

---

## 5. Office Add-in Configuration

### 5.1 Manifest File

**File:** `query-builder/manifest.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp
  xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0"
  xsi:type="TaskPaneApp">

  <!-- App ID - Generate new GUID -->
  <Id>a1b2c3d4-e5f6-7890-abcd-ef1234567890</Id>

  <!-- Version -->
  <Version>1.0.0.0</Version>

  <!-- Provider -->
  <ProviderName>Your Company Name</ProviderName>
  <DefaultLocale>en-US</DefaultLocale>

  <!-- Display Name -->
  <DisplayName DefaultValue="Compliance Analyzer" />
  <Description DefaultValue="Analyze contracts for compliance with customizable rule sets" />
  <IconUrl DefaultValue="https://localhost:4200/assets/icon-32.png" />
  <HighResolutionIconUrl DefaultValue="https://localhost:4200/assets/icon-64.png" />

  <!-- Hosts -->
  <Hosts>
    <Host Name="Document" />
  </Hosts>

  <!-- Default Settings -->
  <DefaultSettings>
    <SourceLocation DefaultValue="https://localhost:4200/word-addin" />
  </DefaultSettings>

  <!-- Permissions -->
  <Permissions>ReadWriteDocument</Permissions>

  <!-- Requirements -->
  <Requirements>
    <Sets DefaultMinVersion="1.1">
      <Set Name="WordApi" MinVersion="1.3" />
    </Sets>
  </Requirements>

  <!-- Ribbon -->
  <VersionOverrides xmlns="http://schemas.microsoft.com/office/taskpaneappversionoverrides" xsi:type="VersionOverridesV1_0">
    <Hosts>
      <Host xsi:type="Document">
        <DesktopFormFactor>
          <!-- Function Commands -->
          <GetStarted>
            <Title resid="GetStarted.Title"/>
            <Description resid="GetStarted.Description"/>
            <LearnMoreUrl resid="GetStarted.LearnMoreUrl"/>
          </GetStarted>

          <!-- Ribbon Tab -->
          <ExtensionPoint xsi:type="PrimaryCommandSurface">
            <OfficeTab id="TabHome">
              <Group id="ComplianceGroup">
                <Label resid="ComplianceGroup.Label" />
                <Icon>
                  <bt:Image size="16" resid="Icon.16x16" />
                  <bt:Image size="32" resid="Icon.32x32" />
                  <bt:Image size="80" resid="Icon.80x80" />
                </Icon>

                <!-- Task Pane Button -->
                <Control xsi:type="Button" id="TaskpaneButton">
                  <Label resid="TaskpaneButton.Label" />
                  <Supertip>
                    <Title resid="TaskpaneButton.Label" />
                    <Description resid="TaskpaneButton.Tooltip" />
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="Icon.16x16" />
                    <bt:Image size="32" resid="Icon.32x32" />
                    <bt:Image size="80" resid="Icon.80x80" />
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <TaskpaneId>ButtonId1</TaskpaneId>
                    <SourceLocation resid="Taskpane.Url" />
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
        </DesktopFormFactor>
      </Host>
    </Hosts>

    <!-- Resources -->
    <Resources>
      <bt:Images>
        <bt:Image id="Icon.16x16" DefaultValue="https://localhost:4200/assets/icon-16.png" />
        <bt:Image id="Icon.32x32" DefaultValue="https://localhost:4200/assets/icon-32.png" />
        <bt:Image id="Icon.80x80" DefaultValue="https://localhost:4200/assets/icon-80.png" />
      </bt:Images>
      <bt:Urls>
        <bt:Url id="GetStarted.LearnMoreUrl" DefaultValue="https://go.microsoft.com/fwlink/?LinkId=276812" />
        <bt:Url id="Taskpane.Url" DefaultValue="https://localhost:4200/word-addin" />
      </bt:Urls>
      <bt:ShortStrings>
        <bt:String id="GetStarted.Title" DefaultValue="Get started with Compliance Analyzer" />
        <bt:String id="ComplianceGroup.Label" DefaultValue="Compliance" />
        <bt:String id="TaskpaneButton.Label" DefaultValue="Analyze Contract" />
      </bt:ShortStrings>
      <bt:LongStrings>
        <bt:String id="GetStarted.Description" DefaultValue="Analyze your contract for compliance" />
        <bt:String id="TaskpaneButton.Tooltip" DefaultValue="Opens the compliance analyzer task pane" />
      </bt:LongStrings>
    </Resources>
  </VersionOverrides>
</OfficeApp>
```

### 5.2 Angular Routing Configuration

**File:** `query-builder/src/app/app.routes.ts`

Add route for Word add-in:

```typescript
import { Routes } from '@angular/router';
import { DocumentAnalyzerComponent } from './word-addin/components/document-analyzer/document-analyzer.component';

export const routes: Routes = [
  // ... existing routes ...

  {
    path: 'word-addin',
    component: DocumentAnalyzerComponent,
    data: { title: 'Compliance Analyzer' }
  },

  // ... other routes ...
];
```

### 5.3 Environment Configuration

**File:** `query-builder/src/environments/environment.ts`

```typescript
export const environment = {
  production: false,
  apiBaseUrl: 'https://localhost:8000',
  officeAddinMode: false
};
```

**File:** `query-builder/src/environments/environment.office.ts` (NEW)

```typescript
export const environment = {
  production: false,
  apiBaseUrl: 'https://localhost:8000',
  officeAddinMode: true
};
```

---

## 6. Development Setup

### 6.1 HTTPS Certificate Setup (Required for Office Add-ins)

Office add-ins require HTTPS, even for local development.

**Option A: Using Angular Dev Server with HTTPS**

1. Generate self-signed certificate:

```bash
# Windows (PowerShell)
cd query-builder
New-SelfSignedCertificate -DnsName "localhost" -CertStoreLocation "cert:\LocalMachine\My" -NotAfter (Get-Date).AddYears(5)

# Export certificate
$cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {$_.Subject -match "localhost"}
Export-PfxCertificate -Cert $cert -FilePath "localhost.pfx" -Password (ConvertTo-SecureString -String "your-password" -Force -AsPlainText)

# Convert to PEM format (requires OpenSSL)
openssl pkcs12 -in localhost.pfx -out localhost.pem -nodes -password pass:your-password
openssl pkcs12 -in localhost.pfx -out localhost.key -nocerts -nodes -password pass:your-password
openssl pkcs12 -in localhost.pfx -out localhost.crt -clcerts -nokeys -password pass:your-password
```

2. Update `package.json`:

```json
{
  "scripts": {
    "start": "ng serve --ssl --ssl-cert localhost.crt --ssl-key localhost.key --port 4200",
    "start:addin": "ng serve --ssl --ssl-cert localhost.crt --ssl-key localhost.key --port 4200 --configuration office"
  }
}
```

3. Trust the certificate:
   - Double-click `localhost.crt`
   - Install certificate to "Trusted Root Certification Authorities"

**Option B: Using webpack-dev-server (Alternative)**

Update `angular.json`:

```json
{
  "serve": {
    "options": {
      "ssl": true,
      "sslKey": "localhost.key",
      "sslCert": "localhost.crt",
      "host": "localhost",
      "port": 4200
    }
  }
}
```

### 6.2 Backend HTTPS Setup (FastAPI)

For development, FastAPI can use the same certificates:

**File:** `web_app/web_app.py`

Add SSL configuration:

```python
if __name__ == "__main__":
    import uvicorn

    # For development with Office Add-in
    ssl_keyfile = "localhost.key"
    ssl_certfile = "localhost.crt"

    uvicorn.run(
        "web_app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )
```

### 6.3 Office.js Types Installation

Install Office.js type definitions:

```bash
cd query-builder
npm install --save-dev @types/office-js
```

Update `tsconfig.json`:

```json
{
  "compilerOptions": {
    "types": ["office-js"]
  }
}
```

### 6.4 Sideloading the Add-in

**Windows:**

1. Create a network share or use local folder
2. Copy `manifest.xml` to the share
3. Open Word → File → Options → Trust Center → Trust Center Settings
4. Select "Trusted Add-in Catalogs"
5. Add the folder path containing manifest.xml
6. Check "Show in Menu"
7. Restart Word
8. Insert → Get Add-ins → Shared Folder → Select "Compliance Analyzer"

**Mac:**

1. Copy `manifest.xml` to `~/Library/Containers/com.microsoft.Word/Data/Documents/wef`
2. Restart Word
3. Insert → Add-ins → My Add-ins → Select "Compliance Analyzer"

**Word Online:**

1. Upload manifest to a web server (HTTPS)
2. In Word Online → Insert → Office Add-ins
3. Click "Upload My Add-in"
4. Provide manifest URL

---

## 7. Implementation Phases

### Phase 1: Foundation Setup (Week 1)

**Tasks:**
- [ ] Set up HTTPS certificates for local development
- [ ] Create `word_addin_evaluations` container in CosmosDB
- [ ] Install Office.js types
- [ ] Create manifest.xml
- [ ] Set up Angular routing for `/word-addin`
- [ ] Test sideloading add-in in Word

**Deliverables:**
- Manifest file configured
- Add-in loads in Word task pane
- "Hello World" display in task pane

### Phase 2: Office.js Integration (Week 1-2)

**Tasks:**
- [ ] Implement `WordIntegrationService`
- [ ] Test document text extraction
- [ ] Test metadata retrieval
- [ ] Test selection vs. entire document
- [ ] Implement error handling

**Deliverables:**
- Service can extract document text
- Service can get metadata
- Service handles Word API errors gracefully

### Phase 3: Backend API (Week 2)

**Tasks:**
- [ ] Implement `WordAddinEvaluationService` (Python)
- [ ] Create `/api/compliance/word-addin/evaluate` endpoint
- [ ] Implement evaluation storage in CosmosDB
- [ ] Test with Postman/curl
- [ ] Add error logging

**Deliverables:**
- API accepts document text and returns evaluation
- Results stored in database
- API errors logged for debugging

### Phase 4: Frontend Components (Week 2-3)

**Tasks:**
- [ ] Create `DocumentAnalyzerComponent`
- [ ] Implement rule set selection UI
- [ ] Add progress indicators
- [ ] Build results display component
- [ ] Style with Office UI Fabric patterns

**Deliverables:**
- User can select rule set
- User can trigger analysis
- Progress shown during analysis
- Results displayed clearly

### Phase 5: Annotations (Week 3)

**Tasks:**
- [ ] Implement text highlighting
- [ ] Implement comment insertion
- [ ] Test annotation on different document structures
- [ ] Handle annotation errors gracefully

**Deliverables:**
- Pass/fail results highlighted in green/red
- Comments inserted at relevant locations
- Partial results shown in yellow

### Phase 6: Testing & Refinement (Week 3-4)

**Tasks:**
- [ ] Test on Windows Desktop Word
- [ ] Test on Mac Desktop Word
- [ ] Test on Word Online
- [ ] Performance testing with large documents
- [ ] Error scenario testing
- [ ] User acceptance testing

**Deliverables:**
- Works on all target platforms
- Handles errors gracefully
- Performance acceptable (<5s for 10 pages)

### Phase 7: Documentation & Deployment (Week 4)

**Tasks:**
- [ ] Write user guide
- [ ] Create troubleshooting guide
- [ ] Document API endpoints
- [ ] Prepare for Azure deployment
- [ ] Create deployment scripts

**Deliverables:**
- User documentation complete
- Deployment guide ready
- Scripts for automated deployment

---

## 8. Testing Guide

### 8.1 Unit Testing

**Frontend Tests:**

```typescript
// word-integration.service.spec.ts
describe('WordIntegrationService', () => {
  it('should extract document text', async () => {
    // Mock Office.js
    // Test text extraction
  });

  it('should handle selection errors', async () => {
    // Test error when no text selected
  });
});

// document-analyzer.component.spec.ts
describe('DocumentAnalyzerComponent', () => {
  it('should load rule sets on init', () => {
    // Test rule set loading
  });

  it('should validate rule set selection', () => {
    // Test validation
  });
});
```

**Backend Tests:**

```python
# test_word_addin_evaluation_service.py
def test_evaluate_document_text():
    """Test document text evaluation"""
    # Test evaluation logic
    pass

def test_store_evaluation():
    """Test evaluation storage"""
    # Test CosmosDB storage
    pass
```

### 8.2 Integration Testing

**Test Scenarios:**

1. **End-to-End Analysis Flow**
   - Open Word document
   - Launch add-in
   - Select rule set
   - Analyze entire document
   - Verify results displayed
   - Check annotations applied

2. **Selection Mode**
   - Select text in document
   - Choose "Selected Text" option
   - Analyze selection
   - Verify only selected text analyzed

3. **Error Handling**
   - Trigger API error (disconnect network)
   - Verify user sees friendly error message
   - Check detailed error logged

4. **Re-evaluation**
   - Run analysis
   - Make document changes
   - Run analysis again
   - Verify new evaluation stored

### 8.3 Platform Testing Matrix

| Platform | Version | Status | Notes |
|----------|---------|--------|-------|
| Word 2016 (Windows) | 16.0 | ✅ | |
| Word 2019 (Windows) | 16.0 | ✅ | |
| Word 2021 (Windows) | 16.0 | ✅ | |
| Microsoft 365 (Windows) | Latest | ✅ | |
| Word 2016 (Mac) | 16.0 | ⏳ | |
| Microsoft 365 (Mac) | Latest | ⏳ | |
| Word Online (Chrome) | Latest | ⏳ | |
| Word Online (Edge) | Latest | ⏳ | |
| Word Online (Firefox) | Latest | ⏳ | |
| Word Online (Safari) | Latest | ⏳ | |

### 8.4 Performance Testing

**Metrics to Track:**

- **Document Loading**: Time to extract text
- **API Response**: Time for backend evaluation
- **Annotation Application**: Time to apply highlights/comments
- **Total End-to-End**: Complete analysis time

**Targets:**

- 1-page document: <2s
- 5-page document: <5s
- 10-page document: <10s
- 20+ page document: User warned about longer processing time

**Test Documents:**

1. Small contract (1-2 pages, ~500 words)
2. Medium contract (5-7 pages, ~2,500 words)
3. Large contract (10-15 pages, ~5,000 words)
4. Complex formatting (tables, headers, footers)

---

## 9. Deployment Instructions

### 9.1 Local Development Deployment

**Prerequisites:**
- Node.js 18+
- Python 3.12+
- Microsoft Word 2016+ or Word Online access
- SSL certificates configured

**Steps:**

1. **Start Backend:**
```bash
cd web_app
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python web_app.py  # Runs on https://localhost:8000
```

2. **Start Frontend:**
```bash
cd query-builder
npm install
npm run start:addin  # Runs on https://localhost:4200
```

3. **Sideload Add-in:**
   - Follow platform-specific sideloading steps (Section 6.4)

### 9.2 Azure Deployment (Future)

**Architecture:**

```
Azure Front Door (CDN)
    ↓
Azure Static Web Apps (Angular)
    ↓
Azure App Service (FastAPI)
    ↓
Azure CosmosDB + Azure OpenAI
```

**Steps:**

1. **Build Angular App:**
```bash
cd query-builder
ng build --configuration production
```

2. **Deploy Static Web App:**
```bash
az staticwebapp create \
  --name compliance-analyzer-web \
  --resource-group rg-compliance \
  --source ./dist/query-builder
```

3. **Deploy FastAPI to App Service:**
```bash
az webapp up \
  --name compliance-analyzer-api \
  --resource-group rg-compliance \
  --runtime "PYTHON:3.12"
```

4. **Update Manifest:**
   - Change URLs from `https://localhost:4200` to production URLs
   - Change API base URL to production API

5. **Publish Add-in:**
   - Option A: Internal distribution (SharePoint catalog)
   - Option B: Microsoft AppSource (public)

---

## 10. Future Enhancements

### 10.1 Planned Features (Future Phases)

**Async Evaluation Mode:**
- Long-running analysis for large documents
- Job tracking and progress updates
- Email notification when complete

**Lite Mode:**
- Quick compliance check (top 5 critical rules)
- <1s response time
- Summary-only view

**Offline Mode:**
- Cache rule sets locally
- Client-side evaluation (limited AI)
- Sync results when online

**Advanced Annotations:**
- Click on result to jump to location in document
- Inline suggestions for fixes
- Track changes integration

**Collaboration:**
- Share evaluation results with team
- Comments and discussions
- Version comparison

**AI-Powered Suggestions:**
- Suggest text to add for failed rules
- Auto-fix common issues
- Learn from user corrections

### 10.2 Technical Debt & Improvements

**Performance:**
- Implement caching for rule sets
- Optimize text extraction for large documents
- Batch API requests

**UX:**
- Add keyboard shortcuts
- Improve accessibility (WCAG 2.1 AA)
- Dark mode support

**Security:**
- Implement OAuth 2.0 authentication
- Add rate limiting
- Encrypt document text in transit

**Monitoring:**
- Add Application Insights
- Track usage metrics
- Error alerting

---

## Appendix A: Troubleshooting

### Common Issues

**Issue 1: Add-in doesn't load**
- **Cause:** SSL certificate not trusted
- **Fix:** Install certificate to Trusted Root Certification Authorities

**Issue 2: "Office.js not found" error**
- **Cause:** Office.js CDN blocked or not loaded
- **Fix:** Ensure `<script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js"></script>` is in index.html

**Issue 3: API calls fail with CORS error**
- **Cause:** Backend not configured for CORS
- **Fix:** Add CORS middleware to FastAPI with allowed origins

**Issue 4: Annotations don't apply**
- **Cause:** Document protected or insufficient permissions
- **Fix:** Check document protection settings

**Issue 5: Slow performance**
- **Cause:** Large document or complex evaluation
- **Fix:** Implement async mode or warn user about processing time

---

## Appendix B: API Reference

### POST /api/compliance/word-addin/evaluate

Evaluate document text against compliance rules.

**Request:**
```json
{
  "document_text": "string",
  "document_metadata": {
    "filename": "string",
    "title": "string",
    "author": "string",
    "created_date": "string (ISO 8601)",
    "word_version": "string",
    "user_email": "string"
  },
  "document_scope": "entire | selection",
  "rule_set_id": "string (optional)",
  "rule_ids": ["string"] (optional)
}
```

**Response (200 OK):**
```json
{
  "evaluation_id": "string",
  "results": [...],
  "summary": {...},
  "annotations": {...},
  "document_metadata": {...}
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Error message"
}
```

**Response (500 Internal Server Error):**
```json
{
  "detail": "Analysis failed. Please try again or contact support."
}
```

### GET /api/compliance/word-addin/evaluations/{evaluation_id}

Retrieve a specific evaluation.

**Response (200 OK):**
```json
{
  "id": "string",
  "evaluation_id": "string",
  "document_metadata": {...},
  "results": [...],
  "summary": {...}
}
```

### GET /api/compliance/word-addin/evaluations

List recent evaluations.

**Query Parameters:**
- `limit` (int, default: 50): Maximum number of results
- `user_email` (string, optional): Filter by user email

**Response (200 OK):**
```json
{
  "evaluations": [...],
  "total": 10
}
```

---

## Appendix C: Database Queries

### Query Evaluations by User

```sql
SELECT * FROM c
WHERE c.doctype = 'word_addin_evaluation'
  AND c.document_metadata.user_email = 'user@example.com'
ORDER BY c.evaluation_metadata.evaluated_date DESC
```

### Query Failed Evaluations

```sql
SELECT * FROM c
WHERE c.doctype = 'word_addin_evaluation'
  AND c.summary.pass_rate < 0.6
ORDER BY c.evaluation_metadata.evaluated_date DESC
```

### Query by Document Filename

```sql
SELECT * FROM c
WHERE c.doctype = 'word_addin_evaluation'
  AND CONTAINS(c.document_metadata.filename, 'contract', true)
ORDER BY c.evaluation_metadata.evaluated_date DESC
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-15 | Implementation Team | Initial implementation guide |

---

**END OF DOCUMENT**
