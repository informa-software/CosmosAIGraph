"""
Models for Batch Job Processing

These models represent batch processing jobs for contract comparisons
and natural language queries, including job queue management, progress
tracking, and status updates.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class JobStatus(str, Enum):
    """Job status values"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type values"""
    CONTRACT_COMPARISON = "contract_comparison"
    CONTRACT_QUERY = "contract_query"
    CONTRACT_UPLOAD = "contract_upload"


class ProcessingStep(str, Enum):
    """Processing step values"""
    QUEUED = "queued"
    UPLOADING = "uploading"  # For contract upload jobs
    EXTRACTING = "extracting"  # For contract upload jobs - Azure CU extraction
    PROCESSING = "processing"  # For contract upload jobs - generating embeddings
    LOADING = "loading"  # For contract upload jobs - loading to CosmosDB
    RETRIEVING_DATA = "retrieving_data"
    GENERATING_PROMPT = "generating_prompt"
    CALLING_LLM = "calling_llm"
    PROCESSING_RESULTS = "processing_results"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Progress Tracking Models
# ============================================================================

class JobProgress(BaseModel):
    """Progress tracking information"""
    current_step: ProcessingStep = ProcessingStep.QUEUED
    current_item: int = 0
    total_items: int = 0
    percentage: float = 0.0
    message: str = "Job queued"
    estimated_time_remaining: Optional[float] = None  # seconds

    class Config:
        json_schema_extra = {
            "example": {
                "current_step": "calling_llm",
                "current_item": 2,
                "total_items": 5,
                "percentage": 40.0,
                "message": "Analyzing contract 2 of 5...",
                "estimated_time_remaining": 30.0
            }
        }


# ============================================================================
# Request Models
# ============================================================================

class ComparisonJobRequest(BaseModel):
    """Request parameters for contract comparison job"""
    standardContractId: str
    compareContractIds: List[str]
    comparisonMode: str  # "full" | "clauses"
    selectedClauses: Optional[List[str]] = None
    modelSelection: str = "primary"  # "primary" | "secondary"
    userEmail: str = "system"

    class Config:
        json_schema_extra = {
            "example": {
                "standardContractId": "contract_123",
                "compareContractIds": ["contract_456", "contract_789"],
                "comparisonMode": "clauses",
                "selectedClauses": ["Indemnity", "Payment Terms"],
                "modelSelection": "primary",
                "userEmail": "system"
            }
        }


class QueryJobRequest(BaseModel):
    """Request parameters for contract query job"""
    question: str
    contract_ids: List[str]
    userEmail: str = "system"
    modelSelection: str = "primary"  # "primary" | "secondary"

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the payment terms in these contracts?",
                "contract_ids": ["contract_123", "contract_456"],
                "userEmail": "system",
                "modelSelection": "primary"
            }
        }


class ContractUploadJobRequest(BaseModel):
    """Request parameters for contract upload job"""
    filename: str
    original_filename: str
    blob_url: str
    uploaded_by: str
    file_size_bytes: int

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "contract.pdf",
                "original_filename": "contract.pdf",
                "blob_url": "https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/contract.pdf",
                "uploaded_by": "system_admin",
                "file_size_bytes": 1048576
            }
        }


# ============================================================================
# Main Job Model
# ============================================================================

class BatchJob(BaseModel):
    """
    Main model for batch processing jobs

    Supports both comparison and query job types.
    Tracks job status, progress, and results.
    """

    # Primary identifiers
    id: str = Field(..., description="CosmosDB document ID (same as job_id)")
    type: str = Field(default="batch_job", description="Document type for filtering")

    # Job identification
    job_id: str = Field(..., description="Unique job identifier")
    job_type: JobType = Field(..., description="Type of job")
    user_id: str = Field(..., description="User who submitted the job")

    # Job status
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Current job status")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1-10, 10 is highest)")

    # Request parameters (stored as dict to support different job types)
    request: Dict[str, Any] = Field(..., description="Job request parameters")

    # Progress tracking
    progress: JobProgress = Field(default_factory=JobProgress, description="Job progress information")

    # Results
    result_id: Optional[str] = Field(None, description="ID of result in analysis_results container")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")

    # Timing metadata
    created_date: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")
    started_date: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_date: Optional[datetime] = Field(None, description="Job completion timestamp")
    elapsed_time: Optional[float] = Field(None, description="Job execution time in seconds")

    # TTL for automatic cleanup (7 days = 604800 seconds)
    ttl: int = Field(default=604800, description="Time to live in seconds (7 days)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "job_1729795200_abc123",
                "type": "batch_job",
                "job_id": "job_1729795200_abc123",
                "job_type": "contract_comparison",
                "user_id": "system",
                "status": "processing",
                "priority": 5,
                "request": {
                    "standardContractId": "contract_123",
                    "compareContractIds": ["contract_456", "contract_789"],
                    "comparisonMode": "clauses",
                    "selectedClauses": ["Indemnity"],
                    "modelSelection": "primary"
                },
                "progress": {
                    "current_step": "calling_llm",
                    "current_item": 1,
                    "total_items": 2,
                    "percentage": 50.0,
                    "message": "Analyzing contract 1 of 2...",
                    "estimated_time_remaining": 30.0
                },
                "result_id": None,
                "error_message": None,
                "error_details": None,
                "created_date": "2024-10-24T12:00:00Z",
                "started_date": "2024-10-24T12:00:05Z",
                "completed_date": None,
                "elapsed_time": None,
                "ttl": 604800
            }
        }


# ============================================================================
# API Request/Response Models
# ============================================================================

class SubmitJobRequest(BaseModel):
    """Request to submit a new job"""
    request: Dict[str, Any] = Field(..., description="Job request parameters")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1-10, 10 is highest)")

    class Config:
        json_schema_extra = {
            "example": {
                "request": {
                    "standardContractId": "contract_123",
                    "compareContractIds": ["contract_456"],
                    "comparisonMode": "full",
                    "modelSelection": "primary"
                },
                "priority": 5
            }
        }


class SubmitJobResponse(BaseModel):
    """Response after submitting a job"""
    job_id: str
    status: JobStatus
    message: str = "Job submitted successfully"

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_1729795200_abc123",
                "status": "queued",
                "message": "Job submitted successfully"
            }
        }


class JobStatusResponse(BaseModel):
    """Response for job status query"""
    job: BatchJob

    class Config:
        json_schema_extra = {
            "example": {
                "job": {
                    "id": "job_1729795200_abc123",
                    "job_id": "job_1729795200_abc123",
                    "job_type": "contract_comparison",
                    "status": "processing",
                    "progress": {
                        "current_step": "calling_llm",
                        "percentage": 50.0,
                        "message": "Analyzing contracts..."
                    }
                }
            }
        }


class UserJobsResponse(BaseModel):
    """Response for listing user jobs"""
    jobs: List[BatchJob]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [],
                "total": 0
            }
        }


class CancelJobResponse(BaseModel):
    """Response after cancelling a job"""
    job_id: str
    success: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_1729795200_abc123",
                "success": True,
                "message": "Job cancelled successfully"
            }
        }


class RetryJobResponse(BaseModel):
    """Response after retrying a failed job"""
    new_job_id: str
    original_job_id: str
    message: str = "Job retry submitted successfully"

    class Config:
        json_schema_extra = {
            "example": {
                "new_job_id": "job_1729795300_def456",
                "original_job_id": "job_1729795200_abc123",
                "message": "Job retry submitted successfully"
            }
        }
