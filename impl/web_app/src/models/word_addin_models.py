"""
Models for Word Add-in Evaluation Sessions

These models represent evaluation sessions initiated from the Word Add-in,
tracking both track changes comparisons and compliance evaluations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TrackChangesInfo(BaseModel):
    """Information about track changes in the document"""
    is_enabled: bool
    change_tracking_mode: str  # 'Off', 'TrackAll', 'TrackMineOnly'
    changes_count: Optional[int] = None


class ComparisonSummary(BaseModel):
    """Summary of the comparison between original and revised versions"""
    overall_similarity_score: float
    risk_level: str  # 'low', 'medium', 'high'
    critical_findings_count: int
    missing_clauses_count: int
    additional_clauses_count: int


class ComplianceSummary(BaseModel):
    """Summary of compliance evaluation results"""
    original_pass: int
    original_fail: int
    original_partial: int
    revised_pass: int
    revised_fail: int
    revised_partial: int
    changed_rules_count: int


class WordAddinEvaluationSession(BaseModel):
    """
    Represents a single evaluation session from the Word Add-in

    Tracks the complete lifecycle of a track changes analysis,
    including comparison and optional compliance evaluation.
    """

    # Primary identifiers
    evaluation_id: str = Field(..., description="Unique session identifier")
    session_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Document information
    document_title: Optional[str] = None
    document_character_count: Optional[int] = None

    # Track changes information
    track_changes_info: TrackChangesInfo

    # Contract identifiers
    original_contract_id: str = Field(..., description="Contract ID for original version")
    revised_contract_id: str = Field(..., description="Contract ID for revised version")

    # Rule set used for evaluation
    rule_set_id: str
    rule_set_name: Optional[str] = None

    # Analysis mode
    compliance_mode: str = Field(..., description="'both' or 'revised'")

    # Comparison results
    comparison_completed: bool = False
    comparison_summary: Optional[ComparisonSummary] = None
    comparison_error: Optional[str] = None

    # Compliance evaluation results
    compliance_completed: bool = False
    original_evaluation_job_id: Optional[str] = None
    revised_evaluation_job_id: Optional[str] = None
    compliance_summary: Optional[ComplianceSummary] = None
    compliance_error: Optional[str] = None

    # Timing information
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Status
    status: str = Field(default="in_progress")  # 'in_progress', 'completed', 'failed'

    # Metadata
    user_id: Optional[str] = None
    client_version: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "evaluation_id": "session_1729537800123",
                "session_timestamp": "2024-10-21T19:30:00.123Z",
                "track_changes_info": {
                    "is_enabled": True,
                    "change_tracking_mode": "TrackAll",
                    "changes_count": 15
                },
                "original_contract_id": "word_original_1729537800123",
                "revised_contract_id": "word_revised_1729537800123",
                "rule_set_id": "ruleset_xyz",
                "rule_set_name": "Standard Contract Rules",
                "compliance_mode": "both",
                "status": "completed"
            }
        }


class CreateSessionRequest(BaseModel):
    """Request to create a new evaluation session"""

    document_title: Optional[str] = None
    document_character_count: Optional[int] = None
    track_changes_info: TrackChangesInfo
    original_contract_id: str
    revised_contract_id: str
    rule_set_id: str
    rule_set_name: Optional[str] = None
    compliance_mode: str = "both"
    user_id: Optional[str] = None
    client_version: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Request to update an existing session"""

    comparison_completed: Optional[bool] = None
    comparison_summary: Optional[ComparisonSummary] = None
    comparison_error: Optional[str] = None

    compliance_completed: Optional[bool] = None
    original_evaluation_job_id: Optional[str] = None
    revised_evaluation_job_id: Optional[str] = None
    compliance_summary: Optional[ComplianceSummary] = None
    compliance_error: Optional[str] = None

    status: Optional[str] = None


class SessionListResponse(BaseModel):
    """Response containing a list of evaluation sessions"""

    sessions: List[WordAddinEvaluationSession]
    total_count: int
    page: int = 1
    page_size: int = 50
