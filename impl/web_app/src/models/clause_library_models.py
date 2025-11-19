"""
Data models for Clause Library functionality.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ClauseVariable(BaseModel):
    """Model for clause variables/placeholders."""
    name: str
    type: str  # "system" or "custom"
    default_value: str
    description: Optional[str] = None
    data_type: Optional[str] = "string"
    source: Optional[str] = None
    metadata_field: Optional[str] = None


class ClauseContent(BaseModel):
    """Model for clause content in various formats."""
    html: str
    plain_text: str
    word_compatible_xml: Optional[str] = None


class ClauseMetadata(BaseModel):
    """Model for clause metadata."""
    tags: List[str] = Field(default_factory=list)
    contract_types: List[str] = Field(default_factory=list)
    jurisdictions: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = None  # "low", "medium", "high"
    complexity: Optional[str] = None  # "low", "medium", "high"


class ClauseVersion(BaseModel):
    """Model for clause version information."""
    version_number: int
    version_label: str
    is_current: bool = True
    parent_version_id: Optional[str] = None
    created_by: str
    created_date: datetime
    change_notes: Optional[str] = None


class ClauseUsageStats(BaseModel):
    """Model for clause usage statistics."""
    times_used: int = 0
    last_used_date: Optional[datetime] = None
    average_comparison_score: Optional[float] = None


class AuditInfo(BaseModel):
    """Model for audit information."""
    created_by: str
    created_date: datetime
    modified_by: Optional[str] = None
    modified_date: Optional[datetime] = None


class Clause(BaseModel):
    """Complete clause document model."""
    id: Optional[str] = None
    type: str = "clause"
    name: str
    description: Optional[str] = None
    category_id: str
    category_path: List[str]
    category_path_display: str
    content: ClauseContent
    variables: List[ClauseVariable] = Field(default_factory=list)
    metadata: ClauseMetadata
    version: ClauseVersion
    usage_stats: ClauseUsageStats = Field(default_factory=ClauseUsageStats)
    embedding: Optional[List[float]] = None
    audit: AuditInfo
    status: str = "active"


class ClauseCategory(BaseModel):
    """Model for clause categories."""
    id: Optional[str] = None
    type: str = "category"
    level: int  # 1, 2, or 3
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    path: List[str]
    display_path: str
    order: int
    icon: Optional[str] = None
    is_predefined: bool = False
    clause_count: int = 0
    audit: Optional[AuditInfo] = None
    status: str = "active"


class SystemVariables(BaseModel):
    """Model for system variables configuration."""
    id: str = "system_variables"
    type: str = "system_variables"
    variables: List[ClauseVariable]
    custom_variables: List[ClauseVariable] = Field(default_factory=list)
    audit: AuditInfo


class ComparisonDifference(BaseModel):
    """Model for individual difference in comparison."""
    type: str  # "missing", "different", "extra"
    location: str
    library_text: Optional[str] = None
    contract_text: Optional[str] = None
    severity: str  # "low", "medium", "high"


class ComparisonResult(BaseModel):
    """Model for text comparison results."""
    similarity_score: float
    differences: List[ComparisonDifference]


class RiskItem(BaseModel):
    """Model for individual risk item."""
    category: str
    description: str
    severity: str  # "low", "medium", "high"
    impact: str
    location: Optional[str] = None


class RiskAnalysis(BaseModel):
    """Model for risk analysis results."""
    overall_risk: str  # "low", "medium", "high"
    risk_score: float
    risks: List[RiskItem]


class Recommendation(BaseModel):
    """Model for clause recommendations."""
    type: str  # "replacement", "addition", "deletion", "modification"
    priority: str  # "low", "medium", "high"
    description: str
    original_text: Optional[str] = None
    suggested_text: Optional[str] = None
    location: Optional[str] = None
    rationale: str


class AIAnalysisInfo(BaseModel):
    """Model for AI analysis metadata."""
    model: str
    completion_tokens: int
    analysis_date: datetime


class ClauseComparison(BaseModel):
    """Complete clause comparison result model."""
    id: Optional[str] = None
    type: str = "comparison_result"
    clause_library_id: str
    contract_id: Optional[str] = None
    contract_text: str
    clause_library_text: str
    comparison: ComparisonResult
    risk_analysis: RiskAnalysis
    recommendations: List[Recommendation]
    ai_analysis: AIAnalysisInfo
    audit: AuditInfo


# Request/Response Models for API

class CreateClauseRequest(BaseModel):
    """Request model for creating a new clause."""
    name: str
    description: Optional[str] = None
    category_id: str
    content_html: str
    tags: List[str] = Field(default_factory=list)
    contract_types: List[str] = Field(default_factory=list)
    jurisdictions: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = None
    complexity: Optional[str] = None


class UpdateClauseRequest(BaseModel):
    """Request model for updating a clause."""
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    content_html: Optional[str] = None
    tags: Optional[List[str]] = None
    contract_types: Optional[List[str]] = None
    jurisdictions: Optional[List[str]] = None
    risk_level: Optional[str] = None
    complexity: Optional[str] = None


class CreateVersionRequest(BaseModel):
    """Request model for creating a new clause version."""
    change_notes: Optional[str] = None


class CompareClauseRequest(BaseModel):
    """Request model for comparing contract text with clause."""
    clause_id: str
    contract_text: str
    contract_id: Optional[str] = None
    contract_metadata: Optional[Dict[str, Any]] = None


class SuggestClauseRequest(BaseModel):
    """Request model for AI-suggested clause matching."""
    contract_text: str
    category_id: Optional[str] = None
    top_k: int = 5


class CreateCategoryRequest(BaseModel):
    """Request model for creating a category."""
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    icon: Optional[str] = None


class CreateCustomVariableRequest(BaseModel):
    """Request model for creating a custom variable."""
    name: str
    display_name: str
    description: Optional[str] = None
    data_type: str = "string"


class ClauseListResponse(BaseModel):
    """Response model for clause list."""
    clauses: List[Clause]
    total_count: int
    page: int
    page_size: int


class CategoryTreeNode(BaseModel):
    """Model for category tree node."""
    category: ClauseCategory
    children: List['CategoryTreeNode'] = Field(default_factory=list)
    clause_count: int = 0


CategoryTreeNode.model_rebuild()


class SearchClausesRequest(BaseModel):
    """Request model for searching clauses."""
    query: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    contract_types: Optional[List[str]] = None
    risk_level: Optional[str] = None
    page: int = 1
    page_size: int = 20
