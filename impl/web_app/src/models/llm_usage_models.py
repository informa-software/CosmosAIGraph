"""
LLM Usage Tracking Models

Pydantic models for LLM usage tracking and analytics.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class UsageRecord(BaseModel):
    """Model for a single LLM usage record."""
    id: str
    type: str = "model_usage"
    api_type: str  # "completion" or "embedding"
    user_email: str
    operation: str
    operation_details: Dict[str, Any] = Field(default_factory=dict)
    model: str
    prompt_tokens: Optional[int] = None  # For completions
    completion_tokens: Optional[int] = None  # For completions
    total_tokens: Optional[int] = None  # For completions
    tokens: Optional[int] = None  # For embeddings
    elapsed_time: float
    timestamp: str
    estimated_cost: float
    success: bool = True
    error_message: Optional[str] = None


class UsageSummary(BaseModel):
    """Model for usage summary response."""
    period_days: int
    start_date: str
    end_date: str
    user_email: str
    models: List[Dict[str, Any]]
    totals: Dict[str, Any]


class OperationBreakdown(BaseModel):
    """Model for operation breakdown response."""
    period_days: int
    start_date: str
    end_date: str
    user_email: str
    operations: List[Dict[str, Any]]
    totals: Dict[str, Any]


class TokenEfficiency(BaseModel):
    """Model for token efficiency analysis response."""
    period_days: int
    user_email: str
    operation_filter: Optional[str] = None
    summary: Dict[str, Any]
    data: List[Dict[str, Any]]


class ErrorAnalysis(BaseModel):
    """Model for error analysis response."""
    period_days: int
    user_email: str
    operations: List[Dict[str, Any]]
    overall: Dict[str, Any]


class CostSavings(BaseModel):
    """Model for cost savings analysis response."""
    period_days: int
    user_email: str
    primary_model_usage: Dict[str, Any]
    if_using_secondary: Dict[str, Any]
    recommendation: str
