"""
Pydantic models for Rule Sets in the compliance system.

Rule Sets are collections of compliance rules that can be applied to contracts.
A rule can belong to multiple rule sets, and a rule set can contain multiple rules.

Author: Aleksey Savateyev, Microsoft, 2025
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RuleSetBase(BaseModel):
    """Base model for rule set with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Name of the rule set")
    description: str | None = Field(None, description="Detailed description of the rule set")
    suggested_contract_types: list[str] | None = Field(
        None,
        description="Suggested contract types this rule set applies to (e.g., ['MSA', 'NDA'])"
    )
    is_active: bool = Field(True, description="Whether this rule set is active")


class RuleSetCreate(RuleSetBase):
    """Model for creating a new rule set"""
    rule_ids: list[str] | None = Field(
        None,
        description="Initial list of rule IDs to include in this set"
    )


class RuleSetUpdate(BaseModel):
    """Model for updating an existing rule set (all fields optional)"""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    suggested_contract_types: list[str] | None = None
    is_active: bool | None = None


class RuleSet(RuleSetBase):
    """Complete rule set model with all fields"""
    id: str = Field(..., description="Unique identifier for the rule set")
    doctype: str = Field(default="rule_set", description="Document type identifier")
    rule_ids: list[str] = Field(default_factory=list, description="List of rule IDs in this set")
    created_date: str = Field(..., description="ISO format creation timestamp")
    modified_date: str = Field(..., description="ISO format last modification timestamp")
    created_by: str = Field(default="system", description="User who created this rule set")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ruleset_msa_001",
                "doctype": "rule_set",
                "name": "Master Service Agreements",
                "description": "Standard compliance rules for MSA contracts",
                "suggested_contract_types": ["MSA"],
                "rule_ids": ["rule_payment_001", "rule_liability_002"],
                "is_active": True,
                "created_date": "2025-01-15T10:00:00Z",
                "modified_date": "2025-01-15T10:00:00Z",
                "created_by": "admin"
            }
        }


class RuleSetListResponse(BaseModel):
    """Response model for listing rule sets"""
    rule_sets: list[RuleSet]
    total: int


class RuleSetWithRuleCount(RuleSet):
    """Rule set model with additional computed fields"""
    rule_count: int = Field(..., description="Number of rules in this set")


class AddRulesToSetRequest(BaseModel):
    """Request model for adding rules to a rule set"""
    rule_ids: list[str] = Field(..., min_items=1, description="Rule IDs to add to the set")


class RemoveRulesFromSetRequest(BaseModel):
    """Request model for removing rules from a rule set"""
    rule_ids: list[str] = Field(..., min_items=1, description="Rule IDs to remove from the set")


class CloneRuleSetRequest(BaseModel):
    """Request model for cloning a rule set"""
    new_name: str = Field(..., min_length=1, max_length=200, description="Name for the cloned rule set")
    clone_rules: bool = Field(
        True,
        description="Whether to copy the rule IDs to the new set"
    )
