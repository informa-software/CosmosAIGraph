"""
Compliance Models

Data models for the contract compliance rules and evaluation system.
Supports CRUD operations on compliance rules, evaluation results, and async job tracking.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class RuleSeverity(str, Enum):
    """Severity levels for compliance rules."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvaluationResult(str, Enum):
    """Possible results of rule evaluation."""
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


class JobStatus(str, Enum):
    """Status of async evaluation jobs."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Types of evaluation jobs."""
    EVALUATE_CONTRACT = "evaluate_contract"
    EVALUATE_RULE = "evaluate_rule"
    REEVALUATE_STALE = "reevaluate_stale"
    BATCH_EVALUATE = "batch_evaluate"


@dataclass
class ComplianceRule:
    """
    Represents a compliance rule that contracts must be evaluated against.

    Attributes:
        id: Unique identifier (auto-generated if not provided)
        name: Short descriptive name for the rule
        description: Natural language description of the compliance requirement
        severity: Importance level of the rule
        category: User-defined category for organizing rules
        active: Whether the rule should be evaluated
        rule_set_ids: List of rule set IDs this rule belongs to
        created_date: When the rule was created (ISO format)
        updated_date: When the rule was last modified (ISO format)
        created_by: User identifier who created the rule
    """
    name: str
    description: str
    severity: str
    category: str
    active: bool = True
    created_by: str = "system"
    rule_set_ids: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __post_init__(self):
        """Validate fields after initialization."""
        if self.severity not in [s.value for s in RuleSeverity]:
            raise ValueError(f"Invalid severity: {self.severity}. Must be one of {[s.value for s in RuleSeverity]}")

        if not self.name or not self.name.strip():
            raise ValueError("Rule name cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Rule description cannot be empty")

        if not self.category or not self.category.strip():
            raise ValueError("Rule category cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceRule':
        """Create instance from dictionary, filtering out CosmosDB system fields."""
        # Filter out CosmosDB system fields
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        return cls(**filtered_data)

    def update(self, **kwargs) -> None:
        """
        Update rule fields and refresh updated_date only for evaluation-affecting changes.

        Only updates the timestamp when description or severity changes, as these are
        the fields that affect rule evaluation and would make existing results stale.

        Args:
            **kwargs: Fields to update (name, description, severity, category, active, rule_set_ids)
        """
        # Track if we're updating fields that affect evaluation
        evaluation_fields_changed = False

        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ['id', 'created_date', 'created_by', 'updated_date']:
                # Check if this is an evaluation-affecting field that's actually changing
                if key in ['description', 'severity']:
                    old_value = getattr(self, key)
                    if old_value != value:
                        evaluation_fields_changed = True

                setattr(self, key, value)

        # Only update timestamp if evaluation-affecting fields changed
        if evaluation_fields_changed:
            self.updated_date = datetime.utcnow().isoformat() + "Z"


@dataclass
class RecommendationData:
    """
    Represents an AI-generated recommendation for fixing a failed/partial compliance rule.

    Attributes:
        original_text: The problematic text found in the contract
        proposed_text: The suggested replacement text
        explanation: Why this change is needed to pass the rule
        location_context: Surrounding text (~50 chars before/after) for matching
        confidence: AI confidence in this recommendation (0.0-1.0)
    """
    original_text: str
    proposed_text: str
    explanation: str
    location_context: str
    confidence: float

    def __post_init__(self):
        """Validate fields after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecommendationData':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class ComplianceResultData:
    """
    Represents the result of evaluating a contract against a compliance rule.

    Attributes:
        id: Unique identifier (auto-generated if not provided)
        contract_id: Reference to the evaluated contract
        rule_id: Reference to the evaluated rule
        rule_name: Denormalized rule name for display
        rule_description: Denormalized rule description for historical tracking
        rule_version_date: Rule's updated_date at time of evaluation
        evaluation_result: Result of the evaluation
        confidence: AI confidence score (0.0-1.0)
        explanation: Human-readable explanation of the evaluation
        evidence: Contract text excerpts supporting the finding
        recommendation: AI-generated suggestion for fixing failed/partial rules (optional)
        evaluated_date: When the evaluation was performed
        evaluated_by: Who/what performed the evaluation
    """
    contract_id: str
    rule_id: str
    rule_name: str
    rule_description: str
    rule_version_date: str
    evaluation_result: str
    confidence: float
    explanation: str
    evidence: List[str] = field(default_factory=list)
    recommendation: Optional[Dict[str, Any]] = None  # Stores RecommendationData as dict
    evaluated_by: str = "system"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evaluated_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __post_init__(self):
        """Validate fields after initialization."""
        if self.evaluation_result not in [r.value for r in EvaluationResult]:
            raise ValueError(f"Invalid result: {self.evaluation_result}. Must be one of {[r.value for r in EvaluationResult]}")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        if not self.contract_id or not self.contract_id.strip():
            raise ValueError("Contract ID cannot be empty")

        if not self.rule_id or not self.rule_id.strip():
            raise ValueError("Rule ID cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceResultData':
        """Create instance from dictionary, filtering out CosmosDB system fields."""
        # Filter out CosmosDB system fields
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        return cls(**filtered_data)

    def is_stale(self, current_rule_updated_date: str) -> bool:
        """
        Check if this result is stale (rule was updated after evaluation).

        Args:
            current_rule_updated_date: The current updated_date of the rule

        Returns:
            True if result is stale and needs re-evaluation
        """
        try:
            result_version = datetime.fromisoformat(self.rule_version_date.replace('Z', '+00:00'))
            current_version = datetime.fromisoformat(current_rule_updated_date.replace('Z', '+00:00'))
            return result_version < current_version
        except Exception:
            # If date parsing fails, consider it stale to be safe
            return True


@dataclass
class EvaluationJob:
    """
    Represents an async evaluation job for tracking progress.

    Attributes:
        id: Unique job identifier
        job_type: Type of evaluation job
        status: Current status of the job
        progress: Completion percentage (0.0-1.0)
        total_items: Total number of items to process
        completed_items: Number of items completed
        failed_items: Number of items that failed
        contract_id: For single contract evaluations
        rule_ids: List of rule IDs being evaluated
        contract_ids: List of contract IDs being evaluated
        started_date: When the job started
        completed_date: When the job completed
        error_message: Error details if job failed
        result_ids: List of result IDs generated by this job
    """
    job_type: str
    status: str = JobStatus.PENDING.value
    progress: float = 0.0
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    contract_id: Optional[str] = None
    rule_ids: List[str] = field(default_factory=list)
    contract_ids: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    completed_date: Optional[str] = None
    error_message: Optional[str] = None
    result_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate fields after initialization."""
        if self.job_type not in [t.value for t in JobType]:
            raise ValueError(f"Invalid job type: {self.job_type}. Must be one of {[t.value for t in JobType]}")

        if self.status not in [s.value for s in JobStatus]:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {[s.value for s in JobStatus]}")

        if not 0.0 <= self.progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {self.progress}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationJob':
        """Create instance from dictionary, filtering out CosmosDB system fields."""
        # Filter out CosmosDB system fields
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        return cls(**filtered_data)

    def update_progress(self, completed: int, failed: int = 0) -> None:
        """
        Update job progress.

        Args:
            completed: Number of items completed
            failed: Number of items that failed
        """
        self.completed_items = completed
        self.failed_items = failed

        if self.total_items > 0:
            self.progress = (completed + failed) / self.total_items

        # Update status based on progress
        if self.status == JobStatus.PENDING.value:
            self.status = JobStatus.IN_PROGRESS.value

    def complete(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        Mark job as completed or failed.

        Args:
            success: Whether the job completed successfully
            error_message: Error message if job failed
        """
        self.completed_date = datetime.utcnow().isoformat() + "Z"
        self.progress = 1.0

        if success:
            self.status = JobStatus.COMPLETED.value
        else:
            self.status = JobStatus.FAILED.value
            self.error_message = error_message

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED.value
        self.completed_date = datetime.utcnow().isoformat() + "Z"


@dataclass
class Category:
    """
    Represents a compliance rule category.

    Attributes:
        name: Internal category identifier (e.g., "payment_terms")
        display_name: Human-readable category name (e.g., "Payment Terms")
        description: Optional description of the category
    """
    name: str
    display_name: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """Create instance from dictionary, filtering out CosmosDB system fields."""
        # Filter out CosmosDB system fields
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        return cls(**filtered_data)


# Predefined categories
PREDEFINED_CATEGORIES = [
    Category("payment_terms", "Payment Terms", "Rules related to payment schedules and terms"),
    Category("confidentiality", "Confidentiality", "Rules about confidentiality and NDA clauses"),
    Category("liability", "Liability", "Rules about liability limitations and damages"),
    Category("termination", "Termination", "Rules about contract termination conditions"),
    Category("indemnification", "Indemnification", "Rules about indemnification clauses"),
    Category("intellectual_property", "Intellectual Property", "Rules about IP ownership and licensing"),
    Category("governing_law", "Governing Law", "Rules about jurisdiction and governing law"),
    Category("warranties", "Warranties", "Rules about warranties and guarantees"),
    Category("compliance", "Compliance", "Rules about regulatory compliance"),
    Category("custom", "Custom", "User-defined category"),
]


def get_predefined_categories() -> List[Category]:
    """Get list of predefined categories."""
    return PREDEFINED_CATEGORIES.copy()


def validate_category_name(name: str) -> bool:
    """
    Validate category name format.

    Args:
        name: Category name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or not name.strip():
        return False

    # Allow alphanumeric, underscores, hyphens
    import re
    return bool(re.match(r'^[a-z0-9_-]+$', name))
