"""
Models for Analysis Results Storage

These models represent stored analysis results from both contract comparisons
and natural language queries, used for PDF generation and historical tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Common Models
# ============================================================================

class AnalysisMetadata(BaseModel):
    """Common metadata for all analysis results"""
    title: str
    description: Optional[str] = None
    execution_time_seconds: Optional[float] = None


class PDFMetadata(BaseModel):
    """Metadata about generated PDFs"""
    generated_at: datetime
    file_size_bytes: int
    page_count: Optional[int] = None
    blob_url: Optional[str] = None  # If storing PDFs in blob storage


# ============================================================================
# Comparison-Specific Models
# ============================================================================

class ComparisonData(BaseModel):
    """Data specific to contract comparisons"""
    standard_contract_id: str
    compare_contract_ids: List[str]
    comparison_mode: str  # "full" | "clauses"
    selected_clauses: Optional[List[str]] = None
    results: Dict[str, Any]  # Full comparison response from API


# ============================================================================
# Query-Specific Models
# ============================================================================

class ContractQueried(BaseModel):
    """Information about a contract that was queried"""
    contract_id: str
    filename: str
    contract_title: Optional[str] = None


class QueryData(BaseModel):
    """Data specific to natural language queries"""
    query_text: str
    query_type: str = "natural_language"  # or "sparql"
    contracts_queried: List[ContractQueried]
    results: Dict[str, Any]  # Query results with rankings and analysis


# ============================================================================
# Main Storage Model
# ============================================================================

class AnalysisResult(BaseModel):
    """
    Main model for storing analysis results

    Supports both comparison and query result types.
    Used for PDF generation and historical tracking.
    """

    # Primary identifiers
    id: str = Field(..., description="CosmosDB document ID (same as result_id)")
    result_id: str = Field(..., description="Unique result identifier")
    result_type: str = Field(..., description="'comparison' or 'query'")

    # User and timing
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="completed")  # "completed", "in_progress", "failed"

    # Common metadata
    metadata: AnalysisMetadata

    # Type-specific data (only one will be populated)
    comparison_data: Optional[ComparisonData] = None
    query_data: Optional[QueryData] = None

    # PDF metadata (populated after PDF generation)
    pdf_metadata: Optional[PDFMetadata] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "result_1729795200_abc123",
                "result_id": "result_1729795200_abc123",
                "result_type": "query",
                "user_id": "user@example.com",
                "created_at": "2025-10-23T14:30:00Z",
                "status": "completed",
                "metadata": {
                    "title": "Indemnification Analysis",
                    "description": "Query across 5 contracts",
                    "execution_time_seconds": 3.2
                },
                "query_data": {
                    "query_text": "Which contracts have the broadest indemnification?",
                    "query_type": "natural_language",
                    "contracts_queried": [
                        {
                            "contract_id": "contract_abc",
                            "filename": "Westervelt_MSA.json",
                            "contract_title": "Westervelt Standard MSA"
                        }
                    ],
                    "results": {
                        "answer_summary": "Analysis summary...",
                        "ranked_contracts": []
                    }
                }
            }
        }


# ============================================================================
# Request/Response Models
# ============================================================================

class SaveComparisonRequest(BaseModel):
    """Request to save comparison results"""
    user_id: str
    standard_contract_id: str
    compare_contract_ids: List[str]
    comparison_mode: str
    selected_clauses: Optional[List[str]] = None
    results: Dict[str, Any]
    metadata: Optional[AnalysisMetadata] = None


class SaveQueryRequest(BaseModel):
    """Request to save query results"""
    user_id: str
    query_text: str
    query_type: str = "natural_language"
    contracts_queried: List[ContractQueried]
    results: Dict[str, Any]
    metadata: Optional[AnalysisMetadata] = None


class SaveResultResponse(BaseModel):
    """Response after saving a result"""
    result_id: str
    message: str = "Results saved successfully"


class EmailPDFRequest(BaseModel):
    """Request to email a PDF"""
    user_id: str
    recipients: List[str]
    message: Optional[str] = None


class ResultListResponse(BaseModel):
    """Response containing a list of results"""
    results: List[AnalysisResult]
    total_count: int
    page: int = 1
    page_size: int = 50
