Clause Library Implementation Plan

  Executive Summary

  This plan implements a comprehensive Clause Library system for managing standard contract clauses with AI-powered
  comparison, risk analysis, and Word add-in integration. The system will support hierarchical organization, version
   history, rich text formatting, and variable placeholders.

  Table of Contents

  1. #1-data-models--schemas
  2. #2-database-setup
  3. #3-backend-api-implementation
  4. #4-frontend-implementation
  5. #5-word-add-in-integration
  6. #6-ai-service-integration
  7. #7-testing-strategy
  8. #8-implementation-phases
  9. #9-migration--deployment

  ---
  1. Data Models & Schemas

  1.1 Clause Library Document Schema

  Container: clause_library

  {
    "id": "uuid-generated",
    "type": "clause",
    "name": "Mutual Indemnification Clause",
    "description": "Standard mutual indemnification with broad coverage",
    "category_id": "indemnification_mutual",
    "category_path": ["indemnification", "mutual", "broad"],
    "category_path_display": "Indemnification > Mutual > Broad Coverage",

    "content": {
      "html": "<p><strong>Indemnification.</strong> Each party (the \"<span class=\"variable\"
  data-var=\"INDEMNIFYING_PARTY\">Indemnifying Party</span>\")...</p>",
      "plain_text": "Indemnification. Each party (the \"Indemnifying Party\")...",
      "word_compatible_xml": "<?xml version=\"1.0\"?>..."
    },

    "variables": [
      {
        "name": "INDEMNIFYING_PARTY",
        "type": "system",
        "default_value": "[Indemnifying Party]",
        "description": "The party providing indemnification"
      },
      {
        "name": "INDEMNIFIED_PARTY",
        "type": "system",
        "default_value": "[Indemnified Party]",
        "description": "The party receiving indemnification"
      },
      {
        "name": "LIABILITY_CAP",
        "type": "custom",
        "default_value": "[Amount]",
        "description": "Maximum liability amount"
      }
    ],

    "metadata": {
      "tags": ["indemnification", "mutual", "liability"],
      "contract_types": ["MSA", "SOW"],
      "jurisdictions": ["multi-state", "federal"],
      "risk_level": "medium",
      "complexity": "high"
    },

    "version": {
      "version_number": 3,
      "version_label": "v3.0",
      "is_current": true,
      "parent_version_id": "previous-uuid",
      "created_by": "user@example.com",
      "created_date": "2025-10-28T10:00:00Z",
      "change_notes": "Updated liability cap language"
    },

    "usage_stats": {
      "times_used": 45,
      "last_used_date": "2025-10-27T15:30:00Z",
      "average_comparison_score": 0.92
    },

    "embedding": [0.123, -0.456, 0.789, ...],

    "audit": {
      "created_by": "user@example.com",
      "created_date": "2025-01-15T10:00:00Z",
      "modified_by": "user@example.com",
      "modified_date": "2025-10-28T10:00:00Z"
    },

    "status": "active"
  }

  1.2 Clause Categories Schema

  Container: clause_categories

  {
    "id": "indemnification",
    "type": "category",
    "level": 1,
    "name": "Indemnification",
    "description": "Clauses related to indemnification and liability",
    "parent_id": null,
    "path": ["indemnification"],
    "display_path": "Indemnification",
    "order": 1,
    "icon": "shield",
    "is_predefined": true,
    "clause_count": 15,
    "audit": {
      "created_by": "system",
      "created_date": "2025-01-01T00:00:00Z",
      "modified_by": "system",
      "modified_date": "2025-01-01T00:00:00Z"
    },
    "status": "active"
  }

  1.3 System Variables Schema

  Container: clause_library (document type: "system_variables")

  {
    "id": "system_variables",
    "type": "system_variables",
    "variables": [
      {
        "name": "CONTRACTOR_PARTY",
        "display_name": "Contractor Party",
        "description": "The party performing the work/services",
        "data_type": "string",
        "source": "contract_metadata",
        "metadata_field": "contractor_party"
      },
      {
        "name": "CONTRACTING_PARTY",
        "display_name": "Contracting Party",
        "description": "The party requesting the work/services",
        "data_type": "string",
        "source": "contract_metadata",
        "metadata_field": "contracting_party"
      },
      {
        "name": "CONTRACT_TYPE",
        "display_name": "Contract Type",
        "description": "Type of contract (MSA, SOW, NDA, etc.)",
        "data_type": "string",
        "source": "contract_metadata",
        "metadata_field": "contract_type"
      },
      {
        "name": "EFFECTIVE_DATE",
        "display_name": "Effective Date",
        "description": "Contract effective date",
        "data_type": "date",
        "source": "contract_metadata",
        "metadata_field": "effective_date"
      },
      {
        "name": "EXPIRATION_DATE",
        "display_name": "Expiration Date",
        "description": "Contract expiration date",
        "data_type": "date",
        "source": "contract_metadata",
        "metadata_field": "expiration_date"
      },
      {
        "name": "CONTRACT_VALUE",
        "display_name": "Contract Value",
        "description": "Total contract value",
        "data_type": "currency",
        "source": "contract_metadata",
        "metadata_field": "total_amount"
      },
      {
        "name": "GOVERNING_LAW_STATE",
        "display_name": "Governing Law State",
        "description": "State whose laws govern the contract",
        "data_type": "string",
        "source": "contract_metadata",
        "metadata_field": "governing_law"
      }
    ],
    "custom_variables": [
      {
        "id": "custom_var_001",
        "name": "CUSTOM_VARIABLE_NAME",
        "display_name": "Display Name",
        "description": "User-defined variable",
        "data_type": "string",
        "created_by": "user@example.com",
        "created_date": "2025-10-28T10:00:00Z"
      }
    ],
    "audit": {
      "modified_by": "system",
      "modified_date": "2025-10-28T10:00:00Z"
    }
  }

  1.4 Clause Comparison Result Schema

  Container: clause_library (document type: "comparison_result")

  {
    "id": "comparison_uuid",
    "type": "comparison_result",
    "clause_library_id": "clause-uuid",
    "contract_id": "contract-uuid",
    "contract_text": "Original text from contract...",
    "clause_library_text": "Clause library text...",

    "comparison": {
      "similarity_score": 0.78,
      "differences": [
        {
          "type": "missing",
          "location": "paragraph 2",
          "library_text": "indemnify and hold harmless",
          "contract_text": null,
          "severity": "high"
        },
        {
          "type": "different",
          "location": "paragraph 3",
          "library_text": "reasonable attorneys' fees",
          "contract_text": "attorneys' fees",
          "severity": "medium"
        }
      ]
    },

    "risk_analysis": {
      "overall_risk": "medium",
      "risk_score": 0.65,
      "risks": [
        {
          "category": "liability",
          "description": "Missing mutual indemnification language may create one-sided obligation",
          "severity": "high",
          "impact": "Increased liability exposure for one party",
          "location": "paragraph 2"
        },
        {
          "category": "scope",
          "description": "Lack of 'reasonable' qualifier on attorneys' fees",
          "severity": "medium",
          "impact": "Could lead to disputes over fee reasonableness",
          "location": "paragraph 3"
        }
      ]
    },

    "recommendations": [
      {
        "type": "replacement",
        "priority": "high",
        "description": "Replace paragraph 2 with mutual indemnification language",
        "original_text": "...",
        "suggested_text": "...",
        "rationale": "Ensures balanced liability protection for both parties"
      },
      {
        "type": "addition",
        "priority": "medium",
        "description": "Add 'reasonable' qualifier to attorneys' fees clause",
        "location": "paragraph 3, before 'attorneys' fees'",
        "suggested_text": "reasonable ",
        "rationale": "Standard practice to prevent fee disputes"
      }
    ],

    "ai_analysis": {
      "model": "gpt-4",
      "completion_tokens": 450,
      "analysis_date": "2025-10-28T10:30:00Z"
    },

    "audit": {
      "created_by": "user@example.com",
      "created_date": "2025-10-28T10:30:00Z"
    }
  }

  ---
  2. Database Setup

  2.1 CosmosDB Container Configuration

  File: web_app/config/cosmosdb_nosql_clause_library_index_policy.json

  {
    "indexingMode": "consistent",
    "automatic": true,
    "includedPaths": [
      {
        "path": "/*"
      }
    ],
    "excludedPaths": [
      {
        "path": "/embedding/*"
      },
      {
        "path": "/content/word_compatible_xml/*"
      }
    ],
    "vectorIndexes": [
      {
        "path": "/embedding",
        "type": "quantizedFlat"
      }
    ]
  }

  File: web_app/config/cosmosdb_nosql_clause_categories_index_policy.json

  {
    "indexingMode": "consistent",
    "automatic": true,
    "includedPaths": [
      {
        "path": "/*"
      }
    ],
    "excludedPaths": [],
    "compositeIndexes": [
      [
        {
          "path": "/level",
          "order": "ascending"
        },
        {
          "path": "/order",
          "order": "ascending"
        }
      ],
      [
        {
          "path": "/parent_id",
          "order": "ascending"
        },
        {
          "path": "/order",
          "order": "ascending"
        }
      ]
    ]
  }

  2.2 Setup Scripts

  File: web_app/setup_clause_library_containers.py

  """
  Setup script for Clause Library CosmosDB containers.
  """

  import asyncio
  import json
  from pathlib import Path
  from azure.cosmos.aio import CosmosClient
  from azure.cosmos import PartitionKey
  import os

  async def setup_containers():
      """Create and configure Clause Library containers."""

      # Load configuration
      cosmos_uri = os.environ.get("CAIG_COSMOSDB_NOSQL_URI")
      cosmos_key = os.environ.get("CAIG_COSMOSDB_NOSQL_KEY")
      database_name = os.environ.get("CAIG_COSMOSDB_NOSQL_DBNAME", "caig")

      async with CosmosClient(cosmos_uri, cosmos_key) as client:
          database = client.get_database_client(database_name)

          # Create clause_library container
          print("Creating clause_library container...")
          clause_library_policy = json.loads(
              Path("config/cosmosdb_nosql_clause_library_index_policy.json").read_text()
          )

          await database.create_container_if_not_exists(
              id="clause_library",
              partition_key=PartitionKey(path="/type"),
              indexing_policy=clause_library_policy,
              vector_embedding_policy={
                  "vectorEmbeddings": [
                      {
                          "path": "/embedding",
                          "dataType": "float32",
                          "dimensions": 1536,
                          "distanceFunction": "cosine"
                      }
                  ]
              }
          )
          print("✓ clause_library container created")

          # Create clause_categories container
          print("Creating clause_categories container...")
          categories_policy = json.loads(
              Path("config/cosmosdb_nosql_clause_categories_index_policy.json").read_text()
          )

          await database.create_container_if_not_exists(
              id="clause_categories",
              partition_key=PartitionKey(path="/level"),
              indexing_policy=categories_policy
          )
          print("✓ clause_categories container created")

          # Initialize system variables
          print("Initializing system variables...")
          container = database.get_container_client("clause_library")

          system_variables = {
              "id": "system_variables",
              "type": "system_variables",
              "variables": [
                  {
                      "name": "CONTRACTOR_PARTY",
                      "display_name": "Contractor Party",
                      "description": "The party performing the work/services",
                      "data_type": "string",
                      "source": "contract_metadata",
                      "metadata_field": "contractor_party"
                  },
                  {
                      "name": "CONTRACTING_PARTY",
                      "display_name": "Contracting Party",
                      "description": "The party requesting the work/services",
                      "data_type": "string",
                      "source": "contract_metadata",
                      "metadata_field": "contracting_party"
                  },
                  {
                      "name": "CONTRACT_TYPE",
                      "display_name": "Contract Type",
                      "description": "Type of contract (MSA, SOW, NDA, etc.)",
                      "data_type": "string",
                      "source": "contract_metadata",
                      "metadata_field": "contract_type"
                  },
                  {
                      "name": "EFFECTIVE_DATE",
                      "display_name": "Effective Date",
                      "description": "Contract effective date",
                      "data_type": "date",
                      "source": "contract_metadata",
                      "metadata_field": "effective_date"
                  },
                  {
                      "name": "EXPIRATION_DATE",
                      "display_name": "Expiration Date",
                      "description": "Contract expiration date",
                      "data_type": "date",
                      "source": "contract_metadata",
                      "metadata_field": "expiration_date"
                  },
                  {
                      "name": "CONTRACT_VALUE",
                      "display_name": "Contract Value",
                      "description": "Total contract value",
                      "data_type": "currency",
                      "source": "contract_metadata",
                      "metadata_field": "total_amount"
                  },
                  {
                      "name": "GOVERNING_LAW_STATE",
                      "display_name": "Governing Law State",
                      "description": "State whose laws govern the contract",
                      "data_type": "string",
                      "source": "contract_metadata",
                      "metadata_field": "governing_law"
                  }
              ],
              "custom_variables": [],
              "audit": {
                  "modified_by": "system",
                  "modified_date": "2025-10-28T00:00:00Z"
              }
          }

          await container.upsert_item(system_variables)
          print("✓ System variables initialized")

          # Initialize predefined categories
          print("Initializing predefined categories...")
          await initialize_predefined_categories(database)

          print("\n✅ All containers setup completed successfully!")

  async def initialize_predefined_categories(database):
      """Initialize predefined clause categories."""
      container = database.get_container_client("clause_categories")

      predefined_categories = [
          # Level 1 Categories
          {
              "id": "indemnification",
              "type": "category",
              "level": 1,
              "name": "Indemnification",
              "description": "Clauses related to indemnification and liability",
              "parent_id": None,
              "path": ["indemnification"],
              "display_path": "Indemnification",
              "order": 1,
              "icon": "shield",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "confidentiality",
              "type": "category",
              "level": 1,
              "name": "Confidentiality",
              "description": "Clauses related to confidential information and non-disclosure",
              "parent_id": None,
              "path": ["confidentiality"],
              "display_path": "Confidentiality",
              "order": 2,
              "icon": "lock",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "payment_terms",
              "type": "category",
              "level": 1,
              "name": "Payment Terms",
              "description": "Clauses related to payment obligations and terms",
              "parent_id": None,
              "path": ["payment_terms"],
              "display_path": "Payment Terms",
              "order": 3,
              "icon": "currency-dollar",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "termination",
              "type": "category",
              "level": 1,
              "name": "Termination",
              "description": "Clauses related to contract termination and exit",
              "parent_id": None,
              "path": ["termination"],
              "display_path": "Termination",
              "order": 4,
              "icon": "x-circle",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "warranties",
              "type": "category",
              "level": 1,
              "name": "Warranties & Representations",
              "description": "Clauses related to warranties and representations",
              "parent_id": None,
              "path": ["warranties"],
              "display_path": "Warranties & Representations",
              "order": 5,
              "icon": "check-badge",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "intellectual_property",
              "type": "category",
              "level": 1,
              "name": "Intellectual Property",
              "description": "Clauses related to IP rights and ownership",
              "parent_id": None,
              "path": ["intellectual_property"],
              "display_path": "Intellectual Property",
              "order": 6,
              "icon": "light-bulb",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "dispute_resolution",
              "type": "category",
              "level": 1,
              "name": "Dispute Resolution",
              "description": "Clauses related to dispute resolution and arbitration",
              "parent_id": None,
              "path": ["dispute_resolution"],
              "display_path": "Dispute Resolution",
              "order": 7,
              "icon": "scale",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },

          # Level 2 Categories (examples under Indemnification)
          {
              "id": "indemnification_mutual",
              "type": "category",
              "level": 2,
              "name": "Mutual",
              "description": "Mutual indemnification clauses",
              "parent_id": "indemnification",
              "path": ["indemnification", "mutual"],
              "display_path": "Indemnification > Mutual",
              "order": 1,
              "icon": "arrows-right-left",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "indemnification_one_way",
              "type": "category",
              "level": 2,
              "name": "One-Way",
              "description": "One-way indemnification clauses",
              "parent_id": "indemnification",
              "path": ["indemnification", "one_way"],
              "display_path": "Indemnification > One-Way",
              "order": 2,
              "icon": "arrow-right",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "indemnification_limited",
              "type": "category",
              "level": 2,
              "name": "Limited",
              "description": "Limited indemnification clauses",
              "parent_id": "indemnification",
              "path": ["indemnification", "limited"],
              "display_path": "Indemnification > Limited",
              "order": 3,
              "icon": "shield-exclamation",
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },

          # Level 3 Categories (examples under Indemnification > Mutual)
          {
              "id": "indemnification_mutual_broad",
              "type": "category",
              "level": 3,
              "name": "Broad Coverage",
              "description": "Broad mutual indemnification clauses",
              "parent_id": "indemnification_mutual",
              "path": ["indemnification", "mutual", "broad"],
              "display_path": "Indemnification > Mutual > Broad Coverage",
              "order": 1,
              "icon": None,
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          },
          {
              "id": "indemnification_mutual_limited",
              "type": "category",
              "level": 3,
              "name": "Limited Scope",
              "description": "Limited scope mutual indemnification clauses",
              "parent_id": "indemnification_mutual",
              "path": ["indemnification", "mutual", "limited"],
              "display_path": "Indemnification > Mutual > Limited Scope",
              "order": 2,
              "icon": None,
              "is_predefined": True,
              "clause_count": 0,
              "status": "active"
          }
      ]

      for category in predefined_categories:
          await container.upsert_item(category)
          print(f"  ✓ Created category: {category['display_path']}")

  if __name__ == "__main__":
      asyncio.run(setup_containers())

  PowerShell Wrapper: web_app/setup_clause_library_containers.ps1

  #!/usr/bin/env pwsh

  # Load environment variables
  . .\set-caig-env-vars.ps1

  # Activate virtual environment
  . .\venv\Scripts\Activate.ps1

  # Run setup script
  python setup_clause_library_containers.py

  Write-Host "`nSetup complete!" -ForegroundColor Green

  ---
  3. Backend API Implementation

  3.1 Models

  File: web_app/src/models/clause_library_models.py

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

  3.2 Service Layer

  File: web_app/src/services/clause_library_service.py

  """
  Service layer for Clause Library operations.
  """

  import uuid
  from typing import List, Optional, Dict, Any, Tuple
  from datetime import datetime
  import html
  from bs4 import BeautifulSoup
  import re

  from src.models.clause_library_models import (
      Clause, ClauseCategory, SystemVariables, ClauseComparison,
      CreateClauseRequest, UpdateClauseRequest, CompareClauseRequest,
      SuggestClauseRequest, CreateCategoryRequest, CreateCustomVariableRequest,
      ClauseContent, ClauseMetadata, ClauseVersion, AuditInfo, ClauseVariable,
      CategoryTreeNode, ClauseListResponse, SearchClausesRequest
  )
  from src.services.cosmos_nosql_service import CosmosNoSQLService
  from src.services.ai_service import AiService
  import logging

  logger = logging.getLogger(__name__)


  class ClauseLibraryService:
      """Service for managing clause library operations."""

      def __init__(
          self,
          cosmos_service: CosmosNoSQLService,
          ai_service: AiService
      ):
          self.cosmos = cosmos_service
          self.ai = ai_service
          self.clause_container = "clause_library"
          self.category_container = "clause_categories"

          # In-memory cache for categories (performance optimization)
          self._category_cache: Optional[Dict[str, ClauseCategory]] = None
          self._category_tree_cache: Optional[List[CategoryTreeNode]] = None

      async def initialize(self):
          """Initialize the service and load caches."""
          logger.info("Initializing ClauseLibraryService...")
          await self._load_category_cache()
          logger.info("ClauseLibraryService initialized successfully")

      # ========== Clause CRUD Operations ==========

      async def create_clause(
          self,
          request: CreateClauseRequest,
          user_email: str
      ) -> Clause:
          """Create a new clause in the library."""
          logger.info(f"Creating new clause: {request.name}")

          # Get category information
          category = await self.get_category(request.category_id)
          if not category:
              raise ValueError(f"Category not found: {request.category_id}")

          # Generate embedding for content
          plain_text = self._html_to_plain_text(request.content_html)
          embedding = await self.ai.generate_embedding(plain_text)

          # Extract variables from content
          variables = self._extract_variables_from_html(request.content_html)

          # Create clause document
          clause_id = str(uuid.uuid4())
          now = datetime.utcnow()

          clause = Clause(
              id=clause_id,
              type="clause",
              name=request.name,
              description=request.description,
              category_id=request.category_id,
              category_path=category.path,
              category_path_display=category.display_path,
              content=ClauseContent(
                  html=request.content_html,
                  plain_text=plain_text
              ),
              variables=variables,
              metadata=ClauseMetadata(
                  tags=request.tags,
                  contract_types=request.contract_types,
                  jurisdictions=request.jurisdictions,
                  risk_level=request.risk_level,
                  complexity=request.complexity
              ),
              version=ClauseVersion(
                  version_number=1,
                  version_label="v1.0",
                  is_current=True,
                  created_by=user_email,
                  created_date=now
              ),
              embedding=embedding,
              audit=AuditInfo(
                  created_by=user_email,
                  created_date=now
              )
          )

          # Save to CosmosDB
          await self.cosmos.upsert_document(
              self.clause_container,
              clause.model_dump(exclude_none=True)
          )

          # Update category clause count
          await self._increment_category_count(request.category_id)

          logger.info(f"Clause created successfully: {clause_id}")
          return clause

      async def get_clause(self, clause_id: str) -> Optional[Clause]:
          """Get a clause by ID."""
          doc = await self.cosmos.get_document(
              self.clause_container,
              clause_id,
              partition_key="clause"
          )

          if doc:
              return Clause(**doc)
          return None

      async def update_clause(
          self,
          clause_id: str,
          request: UpdateClauseRequest,
          user_email: str
      ) -> Clause:
          """Update an existing clause."""
          logger.info(f"Updating clause: {clause_id}")

          # Get existing clause
          existing = await self.get_clause(clause_id)
          if not existing:
              raise ValueError(f"Clause not found: {clause_id}")

          # Update fields
          update_data = request.model_dump(exclude_none=True)

          if "content_html" in update_data:
              plain_text = self._html_to_plain_text(update_data["content_html"])
              embedding = await self.ai.generate_embedding(plain_text)
              variables = self._extract_variables_from_html(update_data["content_html"])

              existing.content.html = update_data["content_html"]
              existing.content.plain_text = plain_text
              existing.embedding = embedding
              existing.variables = variables

          if "name" in update_data:
              existing.name = update_data["name"]
          if "description" in update_data:
              existing.description = update_data["description"]
          if "category_id" in update_data:
              category = await self.get_category(update_data["category_id"])
              if category:
                  # Update old category count
                  await self._decrement_category_count(existing.category_id)

                  existing.category_id = update_data["category_id"]
                  existing.category_path = category.path
                  existing.category_path_display = category.display_path

                  # Update new category count
                  await self._increment_category_count(update_data["category_id"])

          # Update metadata
          for field in ["tags", "contract_types", "jurisdictions", "risk_level", "complexity"]:
              if field in update_data:
                  setattr(existing.metadata, field, update_data[field])

          # Update audit info
          existing.audit.modified_by = user_email
          existing.audit.modified_date = datetime.utcnow()

          # Save to CosmosDB
          await self.cosmos.upsert_document(
              self.clause_container,
              existing.model_dump(exclude_none=True)
          )

          logger.info(f"Clause updated successfully: {clause_id}")
          return existing

      async def delete_clause(self, clause_id: str) -> bool:
          """Delete a clause (soft delete by setting status)."""
          logger.info(f"Deleting clause: {clause_id}")

          clause = await self.get_clause(clause_id)
          if not clause:
              return False

          clause.status = "deleted"

          await self.cosmos.upsert_document(
              self.clause_container,
              clause.model_dump(exclude_none=True)
          )

          # Update category count
          await self._decrement_category_count(clause.category_id)

          logger.info(f"Clause deleted successfully: {clause_id}")
          return True

      async def create_clause_version(
          self,
          clause_id: str,
          change_notes: Optional[str],
          user_email: str
      ) -> Clause:
          """Create a new version of an existing clause."""
          logger.info(f"Creating new version for clause: {clause_id}")

          # Get existing clause
          existing = await self.get_clause(clause_id)
          if not existing:
              raise ValueError(f"Clause not found: {clause_id}")

          # Mark existing as not current
          existing.version.is_current = False
          await self.cosmos.upsert_document(
              self.clause_container,
              existing.model_dump(exclude_none=True)
          )

          # Create new version
          new_clause = existing.model_copy(deep=True)
          new_clause.id = str(uuid.uuid4())
          new_clause.version.version_number = existing.version.version_number + 1
          new_clause.version.version_label = f"v{new_clause.version.version_number}.0"
          new_clause.version.is_current = True
          new_clause.version.parent_version_id = clause_id
          new_clause.version.created_by = user_email
          new_clause.version.created_date = datetime.utcnow()
          new_clause.version.change_notes = change_notes

          # Save new version
          await self.cosmos.upsert_document(
              self.clause_container,
              new_clause.model_dump(exclude_none=True)
          )

          logger.info(f"New clause version created: {new_clause.id}")
          return new_clause

      async def search_clauses(
          self,
          request: SearchClausesRequest
      ) -> ClauseListResponse:
          """Search clauses with filters and pagination."""
          logger.info(f"Searching clauses with query: {request.query}")

          # Build query
          query = "SELECT * FROM c WHERE c.type = 'clause' AND c.status = 'active'"
          parameters = []

          if request.category_id:
              query += " AND c.category_id = @category_id"
              parameters.append({"name": "@category_id", "value": request.category_id})

          if request.tags:
              query += " AND ARRAY_LENGTH(SetIntersect(c.metadata.tags, @tags)) > 0"
              parameters.append({"name": "@tags", "value": request.tags})

          if request.contract_types:
              query += " AND ARRAY_LENGTH(SetIntersect(c.metadata.contract_types, @contract_types)) > 0"
              parameters.append({"name": "@contract_types", "value": request.contract_types})

          if request.risk_level:
              query += " AND c.metadata.risk_level = @risk_level"
              parameters.append({"name": "@risk_level", "value": request.risk_level})

          if request.query:
              # Text search in name, description, and plain_text
              query += " AND (CONTAINS(c.name, @search_query) OR CONTAINS(c.description, @search_query) OR
  CONTAINS(c.content.plain_text, @search_query))"
              parameters.append({"name": "@search_query", "value": request.query})

          query += " ORDER BY c.name"

          # Execute query
          results = await self.cosmos.query_documents(
              self.clause_container,
              query,
              parameters
          )

          clauses = [Clause(**doc) for doc in results]

          # Apply pagination
          total_count = len(clauses)
          start_idx = (request.page - 1) * request.page_size
          end_idx = start_idx + request.page_size
          paginated_clauses = clauses[start_idx:end_idx]

          return ClauseListResponse(
              clauses=paginated_clauses,
              total_count=total_count,
              page=request.page,
              page_size=request.page_size
          )

      # ========== Category Management ==========

      async def get_category(self, category_id: str) -> Optional[ClauseCategory]:
          """Get a category by ID."""
          if self._category_cache and category_id in self._category_cache:
              return self._category_cache[category_id]

          doc = await self.cosmos.get_document(
              self.category_container,
              category_id,
              partition_key=None  # Query across partitions
          )

          if doc:
              return ClauseCategory(**doc)
          return None

      async def get_category_tree(self) -> List[CategoryTreeNode]:
          """Get the complete category hierarchy as a tree."""
          if self._category_tree_cache:
              return self._category_tree_cache

          # Load all categories
          query = "SELECT * FROM c WHERE c.status = 'active' ORDER BY c.level, c.order"
          results = await self.cosmos.query_documents(
              self.category_container,
              query
          )

          categories = [ClauseCategory(**doc) for doc in results]

          # Build tree structure
          tree = self._build_category_tree(categories)
          self._category_tree_cache = tree

          return tree

      async def create_category(
          self,
          request: CreateCategoryRequest,
          user_email: str
      ) -> ClauseCategory:
          """Create a new category."""
          logger.info(f"Creating new category: {request.name}")

          # Determine level and path
          if request.parent_id:
              parent = await self.get_category(request.parent_id)
              if not parent:
                  raise ValueError(f"Parent category not found: {request.parent_id}")

              if parent.level >= 3:
                  raise ValueError("Maximum category depth is 3 levels")

              level = parent.level + 1
              path = parent.path + [self._sanitize_id(request.name)]
              display_path = f"{parent.display_path} > {request.name}"
          else:
              level = 1
              path = [self._sanitize_id(request.name)]
              display_path = request.name

          # Get next order number
          query = f"SELECT VALUE MAX(c.order) FROM c WHERE c.parent_id = @parent_id"
          params = [{"name": "@parent_id", "value": request.parent_id or "null"}]
          results = await self.cosmos.query_documents(
              self.category_container,
              query,
              params
          )
          max_order = results[0] if results and results[0] else 0

          # Create category
          category = ClauseCategory(
              id=path[-1],
              type="category",
              level=level,
              name=request.name,
              description=request.description,
              parent_id=request.parent_id,
              path=path,
              display_path=display_path,
              order=max_order + 1,
              icon=request.icon,
              is_predefined=False,
              clause_count=0,
              audit=AuditInfo(
                  created_by=user_email,
                  created_date=datetime.utcnow()
              )
          )

          # Save to CosmosDB
          await self.cosmos.upsert_document(
              self.category_container,
              category.model_dump(exclude_none=True)
          )

          # Invalidate cache
          self._category_cache = None
          self._category_tree_cache = None

          logger.info(f"Category created successfully: {category.id}")
          return category

      # ========== Variable Management ==========

      async def get_system_variables(self) -> SystemVariables:
          """Get system variables configuration."""
          doc = await self.cosmos.get_document(
              self.clause_container,
              "system_variables",
              partition_key="system_variables"
          )

          if doc:
              return SystemVariables(**doc)

          # Return empty if not found
          return SystemVariables(
              variables=[],
              custom_variables=[],
              audit=AuditInfo(
                  created_by="system",
                  created_date=datetime.utcnow()
              )
          )

      async def create_custom_variable(
          self,
          request: CreateCustomVariableRequest,
          user_email: str
      ) -> ClauseVariable:
          """Create a new custom variable."""
          logger.info(f"Creating custom variable: {request.name}")

          # Get current system variables
          sys_vars = await self.get_system_variables()

          # Check if variable already exists
          all_vars = sys_vars.variables + sys_vars.custom_variables
          if any(v.name == request.name for v in all_vars):
              raise ValueError(f"Variable already exists: {request.name}")

          # Create new custom variable
          custom_var = ClauseVariable(
              name=request.name,
              type="custom",
              display_name=request.display_name,
              description=request.description,
              data_type=request.data_type,
              default_value=f"[{request.display_name}]"
          )

          sys_vars.custom_variables.append(custom_var)
          sys_vars.audit.modified_by = user_email
          sys_vars.audit.modified_date = datetime.utcnow()

          # Save to CosmosDB
          await self.cosmos.upsert_document(
              self.clause_container,
              sys_vars.model_dump(exclude_none=True)
          )

          logger.info(f"Custom variable created: {request.name}")
          return custom_var

      # ========== Comparison & AI Operations ==========

      async def compare_clause(
          self,
          request: CompareClauseRequest,
          user_email: str
      ) -> ClauseComparison:
          """Compare contract text with a clause from the library using AI."""
          logger.info(f"Comparing clause: {request.clause_id}")

          # Get clause from library
          clause = await self.get_clause(request.clause_id)
          if not clause:
              raise ValueError(f"Clause not found: {request.clause_id}")

          # Build AI prompt for comparison
          prompt = self._build_comparison_prompt(
              clause.content.plain_text,
              request.contract_text,
              clause.name
          )

          # Call Azure OpenAI for analysis
          response = await self.ai.generate_completion(prompt)

          # Parse AI response to extract comparison, risks, and recommendations
          comparison_result = self._parse_ai_comparison_response(response)

          # Create comparison document
          comparison_id = str(uuid.uuid4())
          now = datetime.utcnow()

          comparison = ClauseComparison(
              id=comparison_id,
              type="comparison_result",
              clause_library_id=request.clause_id,
              contract_id=request.contract_id,
              contract_text=request.contract_text,
              clause_library_text=clause.content.plain_text,
              comparison=comparison_result["comparison"],
              risk_analysis=comparison_result["risk_analysis"],
              recommendations=comparison_result["recommendations"],
              ai_analysis={
                  "model": self.ai.completions_deployment,
                  "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
                  "analysis_date": now
              },
              audit=AuditInfo(
                  created_by=user_email,
                  created_date=now
              )
          )

          # Save comparison result
          await self.cosmos.upsert_document(
              self.clause_container,
              comparison.model_dump(exclude_none=True)
          )

          # Update clause usage stats
          clause.usage_stats.times_used += 1
          clause.usage_stats.last_used_date = now
          if clause.usage_stats.average_comparison_score:
              clause.usage_stats.average_comparison_score = (
                  clause.usage_stats.average_comparison_score * 0.9 +
                  comparison.comparison.similarity_score * 0.1
              )
          else:
              clause.usage_stats.average_comparison_score = comparison.comparison.similarity_score

          await self.cosmos.upsert_document(
              self.clause_container,
              clause.model_dump(exclude_none=True)
          )

          logger.info(f"Comparison completed: {comparison_id}")
          return comparison

      async def suggest_clause(
          self,
          request: SuggestClauseRequest
      ) -> List[Tuple[Clause, float]]:
          """Use AI to suggest the best matching clauses for given text."""
          logger.info("Suggesting clauses using AI vector search")

          # Generate embedding for contract text
          embedding = await self.ai.generate_embedding(request.contract_text)

          # Perform vector search
          query = """
          SELECT TOP @top_k c.*, VectorDistance(c.embedding, @embedding) AS similarity
          FROM c
          WHERE c.type = 'clause' AND c.status = 'active'
          """

          if request.category_id:
              query += " AND c.category_id = @category_id"

          query += " ORDER BY VectorDistance(c.embedding, @embedding)"

          parameters = [
              {"name": "@top_k", "value": request.top_k},
              {"name": "@embedding", "value": embedding}
          ]

          if request.category_id:
              parameters.append({"name": "@category_id", "value": request.category_id})

          results = await self.cosmos.query_documents(
              self.clause_container,
              query,
              parameters
          )

          # Return clauses with similarity scores
          suggestions = []
          for doc in results:
              similarity = 1.0 - doc.pop("similarity", 0)  # Convert distance to similarity
              clause = Clause(**doc)
              suggestions.append((clause, similarity))

          logger.info(f"Found {len(suggestions)} clause suggestions")
          return suggestions

      # ========== Helper Methods ==========

      async def _load_category_cache(self):
          """Load categories into memory cache."""
          query = "SELECT * FROM c WHERE c.status = 'active'"
          results = await self.cosmos.query_documents(
              self.category_container,
              query
          )

          self._category_cache = {
              doc["id"]: ClauseCategory(**doc)
              for doc in results
          }

          logger.info(f"Loaded {len(self._category_cache)} categories into cache")

      def _build_category_tree(
          self,
          categories: List[ClauseCategory],
          parent_id: Optional[str] = None
      ) -> List[CategoryTreeNode]:
          """Recursively build category tree."""
          tree = []

          for category in categories:
              if category.parent_id == parent_id:
                  node = CategoryTreeNode(
                      category=category,
                      children=self._build_category_tree(categories, category.id),
                      clause_count=category.clause_count
                  )
                  tree.append(node)

          return tree

      def _html_to_plain_text(self, html_content: str) -> str:
          """Convert HTML to plain text."""
          soup = BeautifulSoup(html_content, 'html.parser')
          return soup.get_text(separator=' ', strip=True)

      def _extract_variables_from_html(self, html_content: str) -> List[ClauseVariable]:
          """Extract variable placeholders from HTML content."""
          soup = BeautifulSoup(html_content, 'html.parser')
          variables = []

          # Find all spans with class "variable"
          var_spans = soup.find_all('span', class_='variable')

          for span in var_spans:
              var_name = span.get('data-var')
              if var_name:
                  variables.append(ClauseVariable(
                      name=var_name,
                      type="custom",  # Will be updated based on system variables
                      default_value=span.get_text(),
                      description=f"Variable: {var_name}"
                  ))

          return variables

      def _sanitize_id(self, name: str) -> str:
          """Sanitize category name to create ID."""
          sanitized = name.lower()
          sanitized = re.sub(r'[^\w\s-]', '', sanitized)
          sanitized = re.sub(r'[\s_-]+', '_', sanitized)
          return sanitized.strip('_')

      async def _increment_category_count(self, category_id: str):
          """Increment clause count for a category."""
          category = await self.get_category(category_id)
          if category:
              category.clause_count += 1
              await self.cosmos.upsert_document(
                  self.category_container,
                  category.model_dump(exclude_none=True)
              )

              # Invalidate cache
              self._category_cache = None
              self._category_tree_cache = None

      async def _decrement_category_count(self, category_id: str):
          """Decrement clause count for a category."""
          category = await self.get_category(category_id)
          if category:
              category.clause_count = max(0, category.clause_count - 1)
              await self.cosmos.upsert_document(
                  self.category_container,
                  category.model_dump(exclude_none=True)
              )

              # Invalidate cache
              self._category_cache = None
              self._category_tree_cache = None

      def _build_comparison_prompt(
          self,
          library_text: str,
          contract_text: str,
          clause_name: str
      ) -> str:
          """Build AI prompt for clause comparison."""
          return f"""You are a legal contract analysis expert. Compare the following two clause texts and provide a
  detailed analysis.

  **Standard Clause from Library** ("{clause_name}"):
  {library_text}

  **Clause from Contract**:
  {contract_text}

  Please analyze and provide:

  1. **Similarity Score**: A number between 0 and 1 indicating how similar the texts are (1 = identical, 0 =
  completely different)

  2. **Differences**: Identify all significant differences between the two texts. For each difference, specify:
     - Type: "missing" (in contract but not library), "different" (different wording), or "extra" (in contract but
  not needed)
     - Location: Which paragraph or section
     - Library text vs Contract text
     - Severity: "low", "medium", or "high"

  3. **Risk Analysis**: Analyze potential legal risks with:
     - Overall risk level: "low", "medium", or "high"
     - Risk score: 0 to 1
     - List of specific risks with category, description, severity, impact, and location

  4. **Recommendations**: Provide specific actionable recommendations:
     - Type: "replacement", "addition", "deletion", or "modification"
     - Priority: "low", "medium", or "high"
     - Description and rationale
     - Original text and suggested text

  Return your analysis in the following JSON format:
  {{
    "similarity_score": 0.0,
    "differences": [
      {{
        "type": "missing|different|extra",
        "location": "paragraph X",
        "library_text": "text from library",
        "contract_text": "text from contract",
        "severity": "low|medium|high"
      }}
    ],
    "risk_analysis": {{
      "overall_risk": "low|medium|high",
      "risk_score": 0.0,
      "risks": [
        {{
          "category": "risk category",
          "description": "description",
          "severity": "low|medium|high",
          "impact": "impact description",
          "location": "location in text"
        }}
      ]
    }},
    "recommendations": [
      {{
        "type": "replacement|addition|deletion|modification",
        "priority": "low|medium|high",
        "description": "what to do",
        "original_text": "original text",
        "suggested_text": "suggested text",
        "location": "where to apply",
        "rationale": "why this is recommended"
      }}
    ]
  }}"""

      def _parse_ai_comparison_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
          """Parse AI response into structured comparison result."""
          import json

          # Extract content from response
          content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

          # Parse JSON from content
          try:
              # Try to find JSON block in response
              start = content.find('{')
              end = content.rfind('}') + 1
              if start >= 0 and end > start:
                  json_str = content[start:end]
                  parsed = json.loads(json_str)

                  # Convert to Pydantic models
                  from src.models.clause_library_models import (
                      ComparisonResult, ComparisonDifference,
                      RiskAnalysis, RiskItem, Recommendation
                  )

                  return {
                      "comparison": ComparisonResult(
                          similarity_score=parsed.get("similarity_score", 0.0),
                          differences=[
                              ComparisonDifference(**diff)
                              for diff in parsed.get("differences", [])
                          ]
                      ),
                      "risk_analysis": RiskAnalysis(
                          overall_risk=parsed["risk_analysis"].get("overall_risk", "medium"),
                          risk_score=parsed["risk_analysis"].get("risk_score", 0.5),
                          risks=[
                              RiskItem(**risk)
                              for risk in parsed["risk_analysis"].get("risks", [])
                          ]
                      ),
                      "recommendations": [
                          Recommendation(**rec)
                          for rec in parsed.get("recommendations", [])
                      ]
                  }
          except Exception as e:
              logger.error(f"Error parsing AI response: {e}")
              logger.error(f"Response content: {content}")

          # Fallback to empty result
          from src.models.clause_library_models import (
              ComparisonResult, RiskAnalysis
          )

          return {
              "comparison": ComparisonResult(
                  similarity_score=0.0,
                  differences=[]
              ),
              "risk_analysis": RiskAnalysis(
                  overall_risk="medium",
                  risk_score=0.5,
                  risks=[]
              ),
              "recommendations": []
          }

  3.3 API Router

  File: web_app/routers/clause_library_router.py

  """
  FastAPI router for Clause Library endpoints.
  """

  from fastapi import APIRouter, Depends, HTTPException, status
  from typing import List, Optional
  import logging

  from src.models.clause_library_models import (
      Clause, ClauseCategory, SystemVariables, ClauseComparison,
      CreateClauseRequest, UpdateClauseRequest, CreateVersionRequest,
      CompareClauseRequest, SuggestClauseRequest, CreateCategoryRequest,
      CreateCustomVariableRequest, CategoryTreeNode, ClauseListResponse,
      SearchClausesRequest, ClauseVariable
  )
  from src.services.clause_library_service import ClauseLibraryService

  logger = logging.getLogger(__name__)

  router = APIRouter(prefix="/api/clause-library", tags=["clause-library"])


  # Dependency to get service instance
  # NOTE: In actual implementation, this would be injected properly
  _clause_service: Optional[ClauseLibraryService] = None


  def get_clause_service() -> ClauseLibraryService:
      """Get clause library service instance."""
      if _clause_service is None:
          raise HTTPException(
              status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
              detail="Clause library service not initialized"
          )
      return _clause_service


  def set_clause_service(service: ClauseLibraryService):
      """Set clause library service instance."""
      global _clause_service
      _clause_service = service


  # ========== Clause Endpoints ==========

  @router.post("/clauses", response_model=Clause, status_code=status.HTTP_201_CREATED)
  async def create_clause(
      request: CreateClauseRequest,
      user_email: str = "user@example.com",  # TODO: Get from auth
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Create a new clause in the library."""
      try:
          return await service.create_clause(request, user_email)
      except ValueError as e:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
      except Exception as e:
          logger.error(f"Error creating clause: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to create clause"
          )


  @router.get("/clauses/{clause_id}", response_model=Clause)
  async def get_clause(
      clause_id: str,
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Get a clause by ID."""
      clause = await service.get_clause(clause_id)
      if not clause:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Clause not found: {clause_id}"
          )
      return clause


  @router.put("/clauses/{clause_id}", response_model=Clause)
  async def update_clause(
      clause_id: str,
      request: UpdateClauseRequest,
      user_email: str = "user@example.com",  # TODO: Get from auth
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Update an existing clause."""
      try:
          return await service.update_clause(clause_id, request, user_email)
      except ValueError as e:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
      except Exception as e:
          logger.error(f"Error updating clause: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to update clause"
          )


  @router.delete("/clauses/{clause_id}", status_code=status.HTTP_204_NO_CONTENT)
  async def delete_clause(
      clause_id: str,
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Delete a clause (soft delete)."""
      success = await service.delete_clause(clause_id)
      if not success:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Clause not found: {clause_id}"
          )


  @router.post("/clauses/{clause_id}/versions", response_model=Clause)
  async def create_clause_version(
      clause_id: str,
      request: CreateVersionRequest,
      user_email: str = "user@example.com",  # TODO: Get from auth
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Create a new version of a clause."""
      try:
          return await service.create_clause_version(
              clause_id,
              request.change_notes,
              user_email
          )
      except ValueError as e:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
      except Exception as e:
          logger.error(f"Error creating clause version: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to create clause version"
          )


  @router.post("/clauses/search", response_model=ClauseListResponse)
  async def search_clauses(
      request: SearchClausesRequest,
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Search clauses with filters and pagination."""
      try:
          return await service.search_clauses(request)
      except Exception as e:
          logger.error(f"Error searching clauses: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to search clauses"
          )


  # ========== Category Endpoints ==========

  @router.get("/categories/tree", response_model=List[CategoryTreeNode])
  async def get_category_tree(
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Get the complete category hierarchy as a tree."""
      try:
          return await service.get_category_tree()
      except Exception as e:
          logger.error(f"Error getting category tree: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to get category tree"
          )


  @router.get("/categories/{category_id}", response_model=ClauseCategory)
  async def get_category(
      category_id: str,
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Get a category by ID."""
      category = await service.get_category(category_id)
      if not category:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Category not found: {category_id}"
          )
      return category


  @router.post("/categories", response_model=ClauseCategory, status_code=status.HTTP_201_CREATED)
  async def create_category(
      request: CreateCategoryRequest,
      user_email: str = "user@example.com",  # TODO: Get from auth
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Create a new category."""
      try:
          return await service.create_category(request, user_email)
      except ValueError as e:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
      except Exception as e:
          logger.error(f"Error creating category: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to create category"
          )


  # ========== Variable Endpoints ==========

  @router.get("/variables", response_model=SystemVariables)
  async def get_system_variables(
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Get system variables configuration."""
      try:
          return await service.get_system_variables()
      except Exception as e:
          logger.error(f"Error getting system variables: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to get system variables"
          )


  @router.post("/variables/custom", response_model=ClauseVariable, status_code=status.HTTP_201_CREATED)
  async def create_custom_variable(
      request: CreateCustomVariableRequest,
      user_email: str = "user@example.com",  # TODO: Get from auth
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Create a new custom variable."""
      try:
          return await service.create_custom_variable(request, user_email)
      except ValueError as e:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
      except Exception as e:
          logger.error(f"Error creating custom variable: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to create custom variable"
          )


  # ========== Comparison & AI Endpoints ==========

  @router.post("/compare", response_model=ClauseComparison)
  async def compare_clause(
      request: CompareClauseRequest,
      user_email: str = "user@example.com",  # TODO: Get from auth
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Compare contract text with a clause from the library."""
      try:
          return await service.compare_clause(request, user_email)
      except ValueError as e:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
      except Exception as e:
          logger.error(f"Error comparing clause: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to compare clause"
          )


  @router.post("/suggest")
  async def suggest_clause(
      request: SuggestClauseRequest,
      service: ClauseLibraryService = Depends(get_clause_service)
  ):
      """Use AI to suggest the best matching clauses for given text."""
      try:
          suggestions = await service.suggest_clause(request)
          return {
              "suggestions": [
                  {
                      "clause": clause.model_dump(),
                      "similarity_score": score
                  }
                  for clause, score in suggestions
              ]
          }
      except Exception as e:
          logger.error(f"Error suggesting clause: {e}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Failed to suggest clause"
          )

  3.4 Web App Integration

  Update: web_app/web_app.py

  # Add import
  from routers.clause_library_router import router as clause_library_router, set_clause_service
  from src.services.clause_library_service import ClauseLibraryService

  # In startup event, initialize service
  @app.on_event("startup")
  async def startup_event():
      # ... existing code ...

      # Initialize Clause Library Service
      clause_service = ClauseLibraryService(
          cosmos_service=cosmos_service,
          ai_service=ai_service
      )
      await clause_service.initialize()
      set_clause_service(clause_service)
      logger.info("Clause Library Service initialized")

  # Include router
  app.include_router(clause_library_router)

  ---
  4. Frontend Implementation

  4.1 Angular Module Structure

  Create new module: query-builder/src/app/clause-library/

  clause-library/
  ├── models/
  │   ├── clause.models.ts
  │   └── category.models.ts
  ├── services/
  │   ├── clause-library.service.ts
  │   └── clause-editor-state.service.ts
  ├── components/
  │   ├── clause-list/
  │   │   ├── clause-list.component.ts
  │   │   ├── clause-list.component.html
  │   │   └── clause-list.component.scss
  │   ├── clause-editor/
  │   │   ├── clause-editor.component.ts
  │   │   ├── clause-editor.component.html
  │   │   └── clause-editor.component.scss
  │   ├── clause-viewer/
  │   │   ├── clause-viewer.component.ts
  │   │   ├── clause-viewer.component.html
  │   │   └── clause-viewer.component.scss
  │   ├── category-tree/
  │   │   ├── category-tree.component.ts
  │   │   ├── category-tree.component.html
  │   │   └── category-tree.component.scss
  │   └── variable-manager/
  │       ├── variable-manager.component.ts
  │       ├── variable-manager.component.html
  │       └── variable-manager.component.scss
  ├── clause-library-routing.module.ts
  └── clause-library.module.ts

  4.2 TypeScript Models

  File: query-builder/src/app/clause-library/models/clause.models.ts

  export interface ClauseVariable {
    name: string;
    type: 'system' | 'custom';
    default_value: string;
    description?: string;
    data_type?: string;
    source?: string;
    metadata_field?: string;
  }

  export interface ClauseContent {
    html: string;
    plain_text: string;
    word_compatible_xml?: string;
  }

  export interface ClauseMetadata {
    tags: string[];
    contract_types: string[];
    jurisdictions: string[];
    risk_level?: 'low' | 'medium' | 'high';
    complexity?: 'low' | 'medium' | 'high';
  }

  export interface ClauseVersion {
    version_number: number;
    version_label: string;
    is_current: boolean;
    parent_version_id?: string;
    created_by: string;
    created_date: string;
    change_notes?: string;
  }

  export interface ClauseUsageStats {
    times_used: number;
    last_used_date?: string;
    average_comparison_score?: number;
  }

  export interface AuditInfo {
    created_by: string;
    created_date: string;
    modified_by?: string;
    modified_date?: string;
  }

  export interface Clause {
    id: string;
    type: 'clause';
    name: string;
    description?: string;
    category_id: string;
    category_path: string[];
    category_path_display: string;
    content: ClauseContent;
    variables: ClauseVariable[];
    metadata: ClauseMetadata;
    version: ClauseVersion;
    usage_stats: ClauseUsageStats;
    embedding?: number[];
    audit: AuditInfo;
    status: 'active' | 'deleted';
  }

  export interface CreateClauseRequest {
    name: string;
    description?: string;
    category_id: string;
    content_html: string;
    tags?: string[];
    contract_types?: string[];
    jurisdictions?: string[];
    risk_level?: 'low' | 'medium' | 'high';
    complexity?: 'low' | 'medium' | 'high';
  }

  export interface UpdateClauseRequest {
    name?: string;
    description?: string;
    category_id?: string;
    content_html?: string;
    tags?: string[];
    contract_types?: string[];
    jurisdictions?: string[];
    risk_level?: 'low' | 'medium' | 'high';
    complexity?: 'low' | 'medium' | 'high';
  }

  export interface SearchClausesRequest {
    query?: string;
    category_id?: string;
    tags?: string[];
    contract_types?: string[];
    risk_level?: string;
    page?: number;
    page_size?: number;
  }

  export interface ClauseListResponse {
    clauses: Clause[];
    total_count: number;
    page: number;
    page_size: number;
  }

  File: query-builder/src/app/clause-library/models/category.models.ts

  export interface ClauseCategory {
    id: string;
    type: 'category';
    level: 1 | 2 | 3;
    name: string;
    description?: string;
    parent_id?: string;
    path: string[];
    display_path: string;
    order: number;
    icon?: string;
    is_predefined: boolean;
    clause_count: number;
    audit?: AuditInfo;
    status: 'active' | 'deleted';
  }

  export interface CategoryTreeNode {
    category: ClauseCategory;
    children: CategoryTreeNode[];
    clause_count: number;
  }

  export interface CreateCategoryRequest {
    name: string;
    description?: string;
    parent_id?: string;
    icon?: string;
  }

  export interface AuditInfo {
    created_by: string;
    created_date: string;
    modified_by?: string;
    modified_date?: string;
  }

  4.3 Services

  File: query-builder/src/app/clause-library/services/clause-library.service.ts

  import { Injectable } from '@angular/core';
  import { HttpClient, HttpParams } from '@angular/common/http';
  import { Observable, BehaviorSubject } from 'rxjs';
  import { tap, map } from 'rxjs/operators';
  import {
    Clause,
    ClauseListResponse,
    CreateClauseRequest,
    UpdateClauseRequest,
    SearchClausesRequest
  } from '../models/clause.models';
  import {
    ClauseCategory,
    CategoryTreeNode,
    CreateCategoryRequest
  } from '../models/category.models';

  @Injectable({
    providedIn: 'root'
  })
  export class ClauseLibraryService {
    private readonly apiUrl = '/api/clause-library';

    private categoryTreeSubject = new BehaviorSubject<CategoryTreeNode[]>([]);
    public categoryTree$ = this.categoryTreeSubject.asObservable();

    private selectedCategorySubject = new BehaviorSubject<string | null>(null);
    public selectedCategory$ = this.selectedCategorySubject.asObservable();

    constructor(private http: HttpClient) {}

    // ========== Clause Operations ==========

    createClause(request: CreateClauseRequest): Observable<Clause> {
      return this.http.post<Clause>(`${this.apiUrl}/clauses`, request);
    }

    getClause(clauseId: string): Observable<Clause> {
      return this.http.get<Clause>(`${this.apiUrl}/clauses/${clauseId}`);
    }

    updateClause(clauseId: string, request: UpdateClauseRequest): Observable<Clause> {
      return this.http.put<Clause>(`${this.apiUrl}/clauses/${clauseId}`, request);
    }

    deleteClause(clauseId: string): Observable<void> {
      return this.http.delete<void>(`${this.apiUrl}/clauses/${clauseId}`);
    }

    createClauseVersion(clauseId: string, changeNotes?: string): Observable<Clause> {
      return this.http.post<Clause>(
        `${this.apiUrl}/clauses/${clauseId}/versions`,
        { change_notes: changeNotes }
      );
    }

    searchClauses(request: SearchClausesRequest): Observable<ClauseListResponse> {
      return this.http.post<ClauseListResponse>(`${this.apiUrl}/clauses/search`, request);
    }

    // ========== Category Operations ==========

    getCategoryTree(): Observable<CategoryTreeNode[]> {
      return this.http.get<CategoryTreeNode[]>(`${this.apiUrl}/categories/tree`).pipe(
        tap(tree => this.categoryTreeSubject.next(tree))
      );
    }

    getCategory(categoryId: string): Observable<ClauseCategory> {
      return this.http.get<ClauseCategory>(`${this.apiUrl}/categories/${categoryId}`);
    }

    createCategory(request: CreateCategoryRequest): Observable<ClauseCategory> {
      return this.http.post<ClauseCategory>(`${this.apiUrl}/categories`, request).pipe(
        tap(() => this.getCategoryTree().subscribe()) // Refresh tree
      );
    }

    selectCategory(categoryId: string | null): void {
      this.selectedCategorySubject.next(categoryId);
    }

    // ========== Variable Operations ==========

    getSystemVariables(): Observable<any> {
      return this.http.get(`${this.apiUrl}/variables`);
    }

    createCustomVariable(request: any): Observable<any> {
      return this.http.post(`${this.apiUrl}/variables/custom`, request);
    }

    // ========== Comparison & AI Operations ==========

    compareClause(request: any): Observable<any> {
      return this.http.post(`${this.apiUrl}/compare`, request);
    }

    suggestClause(request: any): Observable<any> {
      return this.http.post(`${this.apiUrl}/suggest`, request);
    }
  }

  4.4 TinyMCE Angular Integration

  Install Dependencies:

  cd query-builder
  npm install @tinymce/tinymce-angular tinymce

  File: query-builder/src/app/clause-library/components/clause-editor/clause-editor.component.ts

  import { Component, OnInit, Input, Output, EventEmitter, ViewChild } from '@angular/core';
  import { FormBuilder, FormGroup, Validators } from '@angular/forms';
  import { EditorComponent } from '@tinymce/tinymce-angular';
  import { ClauseLibraryService } from '../../services/clause-library.service';
  import { Clause, CreateClauseRequest, UpdateClauseRequest } from '../../models/clause.models';
  import { ClauseVariable } from '../../models/clause.models';

  @Component({
    selector: 'app-clause-editor',
    templateUrl: './clause-editor.component.html',
    styleUrls: ['./clause-editor.component.scss']
  })
  export class ClauseEditorComponent implements OnInit {
    @Input() clause?: Clause;
    @Input() mode: 'create' | 'edit' = 'create';
    @Output() saved = new EventEmitter<Clause>();
    @Output() cancelled = new EventEmitter<void>();

    @ViewChild(EditorComponent) editorComponent?: EditorComponent;

    clauseForm: FormGroup;
    systemVariables: ClauseVariable[] = [];
    isLoading = false;
    errorMessage = '';

    // TinyMCE configuration
    editorConfig = {
      base_url: '/tinymce',
      suffix: '.min',
      height: 500,
      menubar: true,
      plugins: [
        'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
        'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
        'insertdatetime', 'media', 'table', 'help', 'wordcount', 'save'
      ],
      toolbar:
        'undo redo | formatselect | bold italic underline strikethrough | \
        alignleft aligncenter alignright alignjustify | \
        bullist numlist outdent indent | removeformat | \
        insertVariable | help',
      toolbar_mode: 'sliding',
      content_style: `
        body { font-family: 'Times New Roman', Times, serif; font-size: 12pt; }
        .variable {
          background-color: #ffeb3b;
          padding: 2px 4px;
          border-radius: 2px;
          cursor: pointer;
        }
      `,
      setup: (editor: any) => {
        // Add custom button for inserting variables
        editor.ui.registry.addMenuButton('insertVariable', {
          text: 'Insert Variable',
          icon: 'plus',
          fetch: (callback: any) => {
            const items = this.systemVariables.map(v => ({
              type: 'menuitem',
              text: v.display_name || v.name,
              onAction: () => {
                editor.insertContent(
                  `<span class="variable" data-var="${v.name}"
  contenteditable="false">${v.default_value}</span>&nbsp;`
                );
              }
            }));
            callback(items);
          }
        });
      }
    };

    constructor(
      private fb: FormBuilder,
      private clauseService: ClauseLibraryService
    ) {
      this.clauseForm = this.fb.group({
        name: ['', Validators.required],
        description: [''],
        category_id: ['', Validators.required],
        content_html: ['', Validators.required],
        tags: [[]],
        contract_types: [[]],
        jurisdictions: [[]],
        risk_level: [''],
        complexity: ['']
      });
    }

    ngOnInit(): void {
      this.loadSystemVariables();

      if (this.clause && this.mode === 'edit') {
        this.clauseForm.patchValue({
          name: this.clause.name,
          description: this.clause.description,
          category_id: this.clause.category_id,
          content_html: this.clause.content.html,
          tags: this.clause.metadata.tags,
          contract_types: this.clause.metadata.contract_types,
          jurisdictions: this.clause.metadata.jurisdictions,
          risk_level: this.clause.metadata.risk_level,
          complexity: this.clause.metadata.complexity
        });
      }
    }

    private loadSystemVariables(): void {
      this.clauseService.getSystemVariables().subscribe({
        next: (data) => {
          this.systemVariables = [
            ...data.variables,
            ...data.custom_variables
          ];
        },
        error: (error) => {
          console.error('Error loading system variables:', error);
        }
      });
    }

    onSave(): void {
      if (this.clauseForm.invalid) {
        this.errorMessage = 'Please fill in all required fields.';
        return;
      }

      this.isLoading = true;
      this.errorMessage = '';

      const formValue = this.clauseForm.value;

      if (this.mode === 'create') {
        const request: CreateClauseRequest = {
          name: formValue.name,
          description: formValue.description,
          category_id: formValue.category_id,
          content_html: formValue.content_html,
          tags: formValue.tags || [],
          contract_types: formValue.contract_types || [],
          jurisdictions: formValue.jurisdictions || [],
          risk_level: formValue.risk_level,
          complexity: formValue.complexity
        };

        this.clauseService.createClause(request).subscribe({
          next: (clause) => {
            this.isLoading = false;
            this.saved.emit(clause);
          },
          error: (error) => {
            this.isLoading = false;
            this.errorMessage = error.error?.detail || 'Failed to create clause';
          }
        });
      } else {
        const request: UpdateClauseRequest = {
          name: formValue.name,
          description: formValue.description,
          category_id: formValue.category_id,
          content_html: formValue.content_html,
          tags: formValue.tags,
          contract_types: formValue.contract_types,
          jurisdictions: formValue.jurisdictions,
          risk_level: formValue.risk_level,
          complexity: formValue.complexity
        };

        this.clauseService.updateClause(this.clause!.id, request).subscribe({
          next: (clause) => {
            this.isLoading = false;
            this.saved.emit(clause);
          },
          error: (error) => {
            this.isLoading = false;
            this.errorMessage = error.error?.detail || 'Failed to update clause';
          }
        });
      }
    }

    onCancel(): void {
      this.cancelled.emit();
    }

    onCreateVersion(): void {
      if (!this.clause) return;

      const changeNotes = prompt('Enter change notes for new version:');
      if (changeNotes === null) return;

      this.isLoading = true;
      this.clauseService.createClauseVersion(this.clause.id, changeNotes).subscribe({
        next: (newVersion) => {
          this.isLoading = false;
          this.clause = newVersion;
          alert('New version created successfully!');
        },
        error: (error) => {
          this.isLoading = false;
          this.errorMessage = error.error?.detail || 'Failed to create version';
        }
      });
    }
  }

  File: query-builder/src/app/clause-library/components/clause-editor/clause-editor.component.html

  <div class="clause-editor">
    <div class="editor-header">
      <h2>{{ mode === 'create' ? 'Create New Clause' : 'Edit Clause' }}</h2>
      <div class="header-actions" *ngIf="mode === 'edit'">
        <button
          type="button"
          class="btn btn-secondary"
          (click)="onCreateVersion()"
          [disabled]="isLoading">
          Create New Version
        </button>
      </div>
    </div>

    <form [formGroup]="clauseForm" (ngSubmit)="onSave()">
      <div class="form-row">
        <div class="form-group col-md-8">
          <label for="name">Clause Name *</label>
          <input
            type="text"
            class="form-control"
            id="name"
            formControlName="name"
            [class.is-invalid]="clauseForm.get('name')?.invalid && clauseForm.get('name')?.touched">
          <div class="invalid-feedback" *ngIf="clauseForm.get('name')?.invalid && clauseForm.get('name')?.touched">
            Clause name is required.
          </div>
        </div>

        <div class="form-group col-md-4">
          <label for="category_id">Category *</label>
          <select
            class="form-control"
            id="category_id"
            formControlName="category_id"
            [class.is-invalid]="clauseForm.get('category_id')?.invalid && clauseForm.get('category_id')?.touched">
            <option value="">Select Category</option>
            <!-- TODO: Populate from category tree -->
          </select>
          <div class="invalid-feedback" *ngIf="clauseForm.get('category_id')?.invalid &&
  clauseForm.get('category_id')?.touched">
            Category is required.
          </div>
        </div>
      </div>

      <div class="form-group">
        <label for="description">Description</label>
        <textarea
          class="form-control"
          id="description"
          formControlName="description"
          rows="2"></textarea>
      </div>

      <div class="form-group">
        <label>Clause Content *</label>
        <editor
          [init]="editorConfig"
          formControlName="content_html">
        </editor>
        <div class="invalid-feedback d-block" *ngIf="clauseForm.get('content_html')?.invalid &&
  clauseForm.get('content_html')?.touched">
          Clause content is required.
        </div>
      </div>

      <div class="form-row">
        <div class="form-group col-md-4">
          <label for="risk_level">Risk Level</label>
          <select class="form-control" id="risk_level" formControlName="risk_level">
            <option value="">Not specified</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        <div class="form-group col-md-4">
          <label for="complexity">Complexity</label>
          <select class="form-control" id="complexity" formControlName="complexity">
            <option value="">Not specified</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label for="tags">Tags</label>
        <input
          type="text"
          class="form-control"
          id="tags"
          placeholder="Enter tags separated by commas">
      </div>

      <div class="alert alert-danger" *ngIf="errorMessage">
        {{ errorMessage }}
      </div>

      <div class="form-actions">
        <button
          type="submit"
          class="btn btn-primary"
          [disabled]="isLoading">
          {{ mode === 'create' ? 'Create Clause' : 'Update Clause' }}
        </button>
        <button
          type="button"
          class="btn btn-secondary"
          (click)="onCancel()"
          [disabled]="isLoading">
          Cancel
        </button>
      </div>
    </form>
  </div>

  4.5 Main Clause Library Component

  File: query-builder/src/app/clause-library/clause-library.component.ts

  import { Component, OnInit } from '@angular/core';
  import { ClauseLibraryService } from './services/clause-library.service';
  import { Clause, SearchClausesRequest } from './models/clause.models';
  import { CategoryTreeNode } from './models/category.models';

  @Component({
    selector: 'app-clause-library',
    templateUrl: './clause-library.component.html',
    styleUrls: ['./clause-library.component.scss']
  })
  export class ClauseLibraryComponent implements OnInit {
    categoryTree: CategoryTreeNode[] = [];
    selectedCategoryId: string | null = null;
    clauses: Clause[] = [];
    selectedClause: Clause | null = null;

    isLoading = false;
    showEditor = false;
    editorMode: 'create' | 'edit' = 'create';

    searchQuery = '';
    currentPage = 1;
    pageSize = 20;
    totalCount = 0;

    constructor(private clauseService: ClauseLibraryService) {}

    ngOnInit(): void {
      this.loadCategoryTree();
      this.loadClauses();

      // Subscribe to category selection
      this.clauseService.selectedCategory$.subscribe(categoryId => {
        this.selectedCategoryId = categoryId;
        this.loadClauses();
      });
    }

    private loadCategoryTree(): void {
      this.clauseService.getCategoryTree().subscribe({
        next: (tree) => {
          this.categoryTree = tree;
        },
        error: (error) => {
          console.error('Error loading category tree:', error);
        }
      });
    }

    private loadClauses(): void {
      this.isLoading = true;

      const request: SearchClausesRequest = {
        query: this.searchQuery || undefined,
        category_id: this.selectedCategoryId || undefined,
        page: this.currentPage,
        page_size: this.pageSize
      };

      this.clauseService.searchClauses(request).subscribe({
        next: (response) => {
          this.clauses = response.clauses;
          this.totalCount = response.total_count;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading clauses:', error);
          this.isLoading = false;
        }
      });
    }

    onCreateClause(): void {
      this.editorMode = 'create';
      this.selectedClause = null;
      this.showEditor = true;
    }

    onEditClause(clause: Clause): void {
      this.editorMode = 'edit';
      this.selectedClause = clause;
      this.showEditor = true;
    }

    onViewClause(clause: Clause): void {
      this.selectedClause = clause;
    }

    onClauseSaved(clause: Clause): void {
      this.showEditor = false;
      this.selectedClause = clause;
      this.loadClauses();
    }

    onEditorCancelled(): void {
      this.showEditor = false;
    }

    onSearch(): void {
      this.currentPage = 1;
      this.loadClauses();
    }

    onPageChange(page: number): void {
      this.currentPage = page;
      this.loadClauses();
    }

    onDeleteClause(clause: Clause): void {
      if (!confirm(`Are you sure you want to delete "${clause.name}"?`)) {
        return;
      }

      this.clauseService.deleteClause(clause.id).subscribe({
        next: () => {
          this.loadClauses();
          if (this.selectedClause?.id === clause.id) {
            this.selectedClause = null;
          }
        },
        error: (error) => {
          console.error('Error deleting clause:', error);
          alert('Failed to delete clause');
        }
      });
    }
  }

  Due to character limits, I'll continue with the remaining sections in my next response. Let me mark the first todo
   as complete and continue.

● Now continuing with the Word Add-in integration and remaining sections:

  ---
  5. Word Add-in Integration

  5.1 Office Add-in Manifest Update

  File: office-addin/manifest.xml

  Add new ribbon button for Clause Library:

  <!-- Add to existing ribbon -->
  <Control xsi:type="Button" id="ClauseLibraryButton">
    <Label resid="ClauseLibrary.ButtonLabel" />
    <Supertip>
      <Title resid="ClauseLibrary.ButtonLabel" />
      <Description resid="ClauseLibrary.ButtonTooltip" />
    </Supertip>
    <Icon>
      <bt:Image size="16" resid="Icon.16x16" />
      <bt:Image size="32" resid="Icon.32x32" />
      <bt:Image size="80" resid="Icon.80x80" />
    </Icon>
    <Action xsi:type="ShowTaskpane">
      <TaskpaneId>ClauseLibraryTaskpane</TaskpaneId>
      <SourceLocation resid="ClauseLibrary.Url" />
    </Action>
  </Control>

  <!-- Add resources -->
  <bt:String id="ClauseLibrary.ButtonLabel" DefaultValue="Clause Library" />
  <bt:String id="ClauseLibrary.ButtonTooltip" DefaultValue="Compare and manage contract clauses" />
  <bt:Url id="ClauseLibrary.Url" DefaultValue="https://localhost:3000/clause-library-taskpane.html" />

  5.2 Task Pane HTML

  File: office-addin/src/taskpane/clause-library-taskpane.html

  <!DOCTYPE html>
  <html>
  <head>
      <meta charset="UTF-8" />
      <meta http-equiv="X-UA-Compatible" content="IE=Edge" />
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Clause Library</title>

      <link rel="stylesheet"
  href="https://static2.sharepointonline.com/files/fabric/office-ui-fabric-core/11.0.0/css/fabric.min.css" />
      <link rel="stylesheet" href="taskpane.css" />
  </head>

  <body class="ms-Fabric">
      <div class="clause-library-taskpane">
          <!-- Header -->
          <header class="taskpane-header">
              <h2>Clause Library</h2>
          </header>

          <!-- Main Content -->
          <main class="taskpane-content">
              <!-- No Selection State -->
              <div id="no-selection" class="state-panel">
                  <div class="ms-MessageBar ms-MessageBar--info">
                      <div class="ms-MessageBar-content">
                          <div class="ms-MessageBar-text">
                              Select text in your document to compare with clause library.
                          </div>
                      </div>
                  </div>
                  <button id="create-from-selection-btn" class="ms-Button ms-Button--primary" disabled>
                      <span class="ms-Button-label">Create Clause from Selection</span>
                  </button>
              </div>

              <!-- Selection Made State -->
              <div id="text-selected" class="state-panel" style="display: none;">
                  <div class="selected-text-preview">
                      <h3>Selected Text</h3>
                      <div id="selected-text-content" class="text-preview"></div>
                  </div>

                  <div class="clause-selection">
                      <h3>Compare With Clause</h3>

                      <!-- AI Suggest Toggle -->
                      <div class="form-group">
                          <input type="checkbox" id="ai-suggest-toggle" class="ms-Toggle-input" />
                          <label for="ai-suggest-toggle" class="ms-Toggle">
                              <span class="ms-Toggle-label">Use AI to Suggest Clause</span>
                          </label>
                      </div>

                      <!-- Manual Selection -->
                      <div id="manual-selection">
                          <select id="clause-dropdown" class="ms-Dropdown">
                              <option value="">Select a clause...</option>
                          </select>
                      </div>

                      <!-- AI Suggestions -->
                      <div id="ai-suggestions" style="display: none;">
                          <div id="suggestion-loading" class="loading-spinner">
                              <div class="ms-Spinner"></div>
                              <span>Finding best matching clauses...</span>
                          </div>
                          <div id="suggestion-results"></div>
                      </div>

                      <button id="compare-btn" class="ms-Button ms-Button--primary">
                          <span class="ms-Button-label">Compare</span>
                      </button>
                  </div>

                  <div class="quick-actions">
                      <button id="create-clause-btn" class="ms-Button">
                          <span class="ms-Button-label">Create Clause from Selection</span>
                      </button>
                  </div>
              </div>

              <!-- Comparison Results State -->
              <div id="comparison-results" class="state-panel" style="display: none;">
                  <div class="results-header">
                      <h3>Comparison Results</h3>
                      <button id="back-to-selection-btn" class="ms-Button ms-Button--icon">
                          <i class="ms-Icon ms-Icon--Back"></i>
                      </button>
                  </div>

                  <div class="similarity-score">
                      <h4>Similarity Score</h4>
                      <div class="score-display">
                          <span id="similarity-score-value">--</span>%
                      </div>
                  </div>

                  <div class="risk-analysis">
                      <h4>Risk Analysis</h4>
                      <div id="risk-level" class="risk-badge"></div>
                      <div id="risk-details"></div>
                  </div>

                  <div class="differences">
                      <h4>Differences Found</h4>
                      <div id="differences-list"></div>
                  </div>

                  <div class="recommendations">
                      <h4>Recommendations</h4>
                      <div id="recommendations-list"></div>
                  </div>

                  <div class="action-buttons">
                      <button id="apply-recommendations-btn" class="ms-Button ms-Button--primary">
                          <span class="ms-Button-label">Apply Recommendations</span>
                      </button>
                      <button id="replace-with-library-btn" class="ms-Button">
                          <span class="ms-Button-label">Replace with Library Clause</span>
                      </button>
                  </div>

                  <!-- Replacement Options Modal -->
                  <div id="replacement-options-modal" class="modal" style="display: none;">
                      <div class="modal-content">
                          <h3>Replacement Options</h3>

                          <div class="form-group">
                              <label>
                                  <input type="radio" name="formatting" value="preserve" checked />
                                  Preserve original formatting
                              </label>
                          </div>
                          <div class="form-group">
                              <label>
                                  <input type="radio" name="formatting" value="library" />
                                  Use clause library formatting
                              </label>
                          </div>

                          <div class="form-group">
                              <label>
                                  <input type="checkbox" id="enable-track-changes" />
                                  Enable Track Changes
                              </label>
                              <p class="help-text">If disabled, text will be overwritten directly.</p>
                          </div>

                          <div class="modal-actions">
                              <button id="confirm-replace-btn" class="ms-Button ms-Button--primary">
                                  <span class="ms-Button-label">Replace</span>
                              </button>
                              <button id="cancel-replace-btn" class="ms-Button">
                                  <span class="ms-Button-label">Cancel</span>
                              </button>
                          </div>
                      </div>
                  </div>
              </div>
          </main>
      </div>

      <script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js"></script>
      <script src="clause-library-taskpane.js"></script>
  </body>
  </html>

  5.3 Task Pane JavaScript

  File: office-addin/src/taskpane/clause-library-taskpane.ts

  /// <reference types="@types/office-js" />

  interface ClauseSuggestion {
    clause: any;
    similarity_score: number;
  }

  interface ComparisonResult {
    id: string;
    similarity_score: number;
    comparison: any;
    risk_analysis: any;
    recommendations: any[];
  }

  let currentSelection: Word.Range | null = null;
  let currentComparisonResult: ComparisonResult | null = null;
  let aiSuggestEnabled: boolean = false;
  let availableClauses: any[] = [];

  // Load AI suggest preference from localStorage
  const AI_SUGGEST_KEY = 'clause_library_ai_suggest_enabled';

  Office.onReady((info) => {
    if (info.host === Office.HostType.Word) {
      initializeTaskPane();
    }
  });

  async function initializeTaskPane(): Promise<void> {
    // Load AI suggest preference
    const savedPreference = localStorage.getItem(AI_SUGGEST_KEY);
    aiSuggestEnabled = savedPreference === 'true';

    const aiToggle = document.getElementById('ai-suggest-toggle') as HTMLInputElement;
    if (aiToggle) {
      aiToggle.checked = aiSuggestEnabled;
      aiToggle.addEventListener('change', onAiSuggestToggle);
    }

    // Load available clauses for dropdown
    await loadClausesForDropdown();

    // Set up event listeners
    document.getElementById('compare-btn')?.addEventListener('click', onCompareClicked);
    document.getElementById('create-clause-btn')?.addEventListener('click', onCreateClauseClicked);
    document.getElementById('create-from-selection-btn')?.addEventListener('click', onCreateClauseClicked);
    document.getElementById('apply-recommendations-btn')?.addEventListener('click', onApplyRecommendations);
    document.getElementById('replace-with-library-btn')?.addEventListener('click', onReplaceWithLibrary);
    document.getElementById('back-to-selection-btn')?.addEventListener('click', onBackToSelection);
    document.getElementById('confirm-replace-btn')?.addEventListener('click', onConfirmReplace);
    document.getElementById('cancel-replace-btn')?.addEventListener('click', onCancelReplace);

    // Monitor document selection changes
    await Word.run(async (context) => {
      context.document.onSelectionChanged.add(onSelectionChanged);
      await context.sync();
    });

    // Initial check
    await checkSelection();
  }

  async function loadClausesForDropdown(): Promise<void> {
    try {
      const response = await fetch('/api/clause-library/clauses/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: 1, page_size: 1000 })
      });

      const data = await response.json();
      availableClauses = data.clauses;

      const dropdown = document.getElementById('clause-dropdown') as HTMLSelectElement;
      if (dropdown) {
        dropdown.innerHTML = '<option value="">Select a clause...</option>';

        data.clauses.forEach((clause: any) => {
          const option = document.createElement('option');
          option.value = clause.id;
          option.textContent = `${clause.name} (${clause.category_path_display})`;
          dropdown.appendChild(option);
        });
      }
    } catch (error) {
      console.error('Error loading clauses:', error);
    }
  }

  async function onSelectionChanged(): Promise<void> {
    await checkSelection();
  }

  async function checkSelection(): Promise<void> {
    await Word.run(async (context) => {
      const selection = context.document.getSelection();
      selection.load('text');
      await context.sync();

      const hasSelection = selection.text && selection.text.trim().length > 0;

      if (hasSelection) {
        currentSelection = selection;
        showState('text-selected');

        // Update preview
        const preview = document.getElementById('selected-text-content');
        if (preview) {
          preview.textContent = selection.text.substring(0, 200) + '...';
        }

        // If AI suggest is enabled, trigger suggestions
        if (aiSuggestEnabled) {
          await suggestClauses(selection.text);
        }
      } else {
        currentSelection = null;
        showState('no-selection');
      }
    });
  }

  function onAiSuggestToggle(event: Event): void {
    const checkbox = event.target as HTMLInputElement;
    aiSuggestEnabled = checkbox.checked;

    // Save preference to localStorage
    localStorage.setItem(AI_SUGGEST_KEY, aiSuggestEnabled.toString());

    // Toggle UI
    const manualSelection = document.getElementById('manual-selection');
    const aiSuggestions = document.getElementById('ai-suggestions');

    if (aiSuggestEnabled) {
      if (manualSelection) manualSelection.style.display = 'none';
      if (aiSuggestions) aiSuggestions.style.display = 'block';

      // Trigger suggestions if we have selected text
      if (currentSelection) {
        Word.run(async (context) => {
          currentSelection!.load('text');
          await context.sync();
          await suggestClauses(currentSelection!.text);
        });
      }
    } else {
      if (manualSelection) manualSelection.style.display = 'block';
      if (aiSuggestions) aiSuggestions.style.display = 'none';
    }
  }

  async function suggestClauses(text: string): Promise<void> {
    const loadingEl = document.getElementById('suggestion-loading');
    const resultsEl = document.getElementById('suggestion-results');

    if (loadingEl) loadingEl.style.display = 'block';
    if (resultsEl) resultsEl.innerHTML = '';

    try {
      const response = await fetch('/api/clause-library/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contract_text: text,
          top_k: 5
        })
      });

      const data = await response.json();

      if (loadingEl) loadingEl.style.display = 'none';

      if (data.suggestions && data.suggestions.length > 0) {
        displaySuggestions(data.suggestions);
      } else {
        if (resultsEl) {
          resultsEl.innerHTML = '<p class="no-results">No matching clauses found.</p>';
        }
      }
    } catch (error) {
      console.error('Error suggesting clauses:', error);
      if (loadingEl) loadingEl.style.display = 'none';
      if (resultsEl) {
        resultsEl.innerHTML = '<p class="error">Failed to load suggestions.</p>';
      }
    }
  }

  function displaySuggestions(suggestions: ClauseSuggestion[]): void {
    const resultsEl = document.getElementById('suggestion-results');
    if (!resultsEl) return;

    resultsEl.innerHTML = '';

    suggestions.forEach((suggestion, index) => {
      const card = document.createElement('div');
      card.className = 'suggestion-card';

      const score = Math.round(suggestion.similarity_score * 100);
      const scoreClass = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low';

      card.innerHTML = `
        <div class="suggestion-header">
          <h4>${suggestion.clause.name}</h4>
          <span class="similarity-badge ${scoreClass}">${score}% match</span>
        </div>
        <p class="category">${suggestion.clause.category_path_display}</p>
        <p class="description">${suggestion.clause.description || ''}</p>
        <button class="ms-Button select-suggestion-btn" data-clause-id="${suggestion.clause.id}">
          <span class="ms-Button-label">Select</span>
        </button>
      `;

      const selectBtn = card.querySelector('.select-suggestion-btn');
      selectBtn?.addEventListener('click', () => {
        onSuggestionSelected(suggestion.clause.id);
      });

      resultsEl.appendChild(card);
    });
  }

  async function onSuggestionSelected(clauseId: string): Promise<void> {
    // Automatically trigger comparison with selected clause
    await compareWithClause(clauseId);
  }

  async function onCompareClicked(): Promise<void> {
    const dropdown = document.getElementById('clause-dropdown') as HTMLSelectElement;
    const clauseId = dropdown?.value;

    if (!clauseId) {
      alert('Please select a clause to compare.');
      return;
    }

    await compareWithClause(clauseId);
  }

  async function compareWithClause(clauseId: string): Promise<void> {
    if (!currentSelection) {
      alert('No text selected.');
      return;
    }

    try {
      const selectedText = await Word.run(async (context) => {
        currentSelection!.load('text');
        await context.sync();
        return currentSelection!.text;
      });

      // Show loading state
      showState('comparison-results');
      showLoading('Analyzing clause...');

      const response = await fetch('/api/clause-library/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clause_id: clauseId,
          contract_text: selectedText
        })
      });

      if (!response.ok) {
        throw new Error('Comparison failed');
      }

      const result: ComparisonResult = await response.json();
      currentComparisonResult = result;

      hideLoading();
      displayComparisonResults(result);
    } catch (error) {
      console.error('Error comparing clause:', error);
      hideLoading();
      alert('Failed to compare clause. Please try again.');
      showState('text-selected');
    }
  }

  function displayComparisonResults(result: ComparisonResult): void {
    // Display similarity score
    const scoreEl = document.getElementById('similarity-score-value');
    if (scoreEl) {
      const score = Math.round(result.comparison.similarity_score * 100);
      scoreEl.textContent = score.toString();
    }

    // Display risk analysis
    const riskLevelEl = document.getElementById('risk-level');
    const riskDetailsEl = document.getElementById('risk-details');

    if (riskLevelEl) {
      riskLevelEl.textContent = result.risk_analysis.overall_risk.toUpperCase();
      riskLevelEl.className = `risk-badge risk-${result.risk_analysis.overall_risk}`;
    }

    if (riskDetailsEl) {
      riskDetailsEl.innerHTML = result.risk_analysis.risks.map((risk: any) => `
        <div class="risk-item ${risk.severity}">
          <h5>${risk.category}</h5>
          <p>${risk.description}</p>
          <p class="impact">${risk.impact}</p>
        </div>
      `).join('');
    }

    // Display differences
    const differencesEl = document.getElementById('differences-list');
    if (differencesEl) {
      differencesEl.innerHTML = result.comparison.differences.map((diff: any) => `
        <div class="difference-item ${diff.severity}">
          <span class="diff-type">${diff.type}</span>
          <p class="location">${diff.location}</p>
          <div class="diff-comparison">
            <div class="library-text">
              <strong>Library:</strong> ${diff.library_text || '(none)'}
            </div>
            <div class="contract-text">
              <strong>Contract:</strong> ${diff.contract_text || '(none)'}
            </div>
          </div>
        </div>
      `).join('');
    }

    // Display recommendations
    const recommendationsEl = document.getElementById('recommendations-list');
    if (recommendationsEl) {
      recommendationsEl.innerHTML = result.recommendations.map((rec: any, index: number) => `
        <div class="recommendation-item priority-${rec.priority}">
          <h5>${rec.description}</h5>
          <p class="rationale">${rec.rationale}</p>
          <div class="recommendation-text">
            ${rec.suggested_text ? `<p><strong>Suggested:</strong> ${rec.suggested_text}</p>` : ''}
          </div>
          <button class="ms-Button apply-single-rec-btn" data-index="${index}">
            <span class="ms-Button-label">Apply This</span>
          </button>
        </div>
      `).join('');

      // Add event listeners to individual recommendation buttons
      document.querySelectorAll('.apply-single-rec-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const index = parseInt((e.currentTarget as HTMLElement).dataset.index || '0');
          applySingleRecommendation(result.recommendations[index]);
        });
      });
    }
  }

  async function onApplyRecommendations(): Promise<void> {
    if (!currentComparisonResult || !currentSelection) return;

    try {
      await Word.run(async (context) => {
        // Apply all recommendations
        for (const rec of currentComparisonResult!.recommendations) {
          await applyRecommendationToDocument(context, rec);
        }

        await context.sync();
      });

      alert('Recommendations applied successfully!');
    } catch (error) {
      console.error('Error applying recommendations:', error);
      alert('Failed to apply recommendations.');
    }
  }

  async function applySingleRecommendation(recommendation: any): Promise<void> {
    try {
      await Word.run(async (context) => {
        await applyRecommendationToDocument(context, recommendation);
        await context.sync();
      });

      alert('Recommendation applied successfully!');
    } catch (error) {
      console.error('Error applying recommendation:', error);
      alert('Failed to apply recommendation.');
    }
  }

  async function applyRecommendationToDocument(
    context: Word.RequestContext,
    recommendation: any
  ): Promise<void> {
    if (!currentSelection) return;

    switch (recommendation.type) {
      case 'replacement':
        if (recommendation.original_text && recommendation.suggested_text) {
          const searchResults = currentSelection.search(recommendation.original_text, {
            matchCase: false,
            matchWholeWord: false
          });
          searchResults.load('items');
          await context.sync();

          if (searchResults.items.length > 0) {
            searchResults.items[0].insertText(
              recommendation.suggested_text,
              Word.InsertLocation.replace
            );
          }
        }
        break;

      case 'addition':
        if (recommendation.suggested_text) {
          currentSelection.insertText(
            recommendation.suggested_text + ' ',
            Word.InsertLocation.end
          );
        }
        break;

      case 'deletion':
        if (recommendation.original_text) {
          const searchResults = currentSelection.search(recommendation.original_text, {
            matchCase: false,
            matchWholeWord: false
          });
          searchResults.load('items');
          await context.sync();

          if (searchResults.items.length > 0) {
            searchResults.items[0].delete();
          }
        }
        break;
    }
  }

  function onReplaceWithLibrary(): void {
    // Show replacement options modal
    const modal = document.getElementById('replacement-options-modal');
    if (modal) {
      modal.style.display = 'block';
    }
  }

  function onCancelReplace(): void {
    const modal = document.getElementById('replacement-options-modal');
    if (modal) {
      modal.style.display = 'none';
    }
  }

  async function onConfirmReplace(): Promise<void> {
    if (!currentComparisonResult || !currentSelection) return;

    const preserveFormatting = (document.querySelector('input[name="formatting"]:checked') as
  HTMLInputElement)?.value === 'preserve';
    const enableTrackChanges = (document.getElementById('enable-track-changes') as HTMLInputElement)?.checked;

    try {
      await Word.run(async (context) => {
        // Enable track changes if requested
        if (enableTrackChanges) {
          context.document.changeTrackingMode = Word.ChangeTrackingMode.trackAll;
        }

        // Get clause library text
        const clauseResponse = await
  fetch(`/api/clause-library/clauses/${currentComparisonResult!.clause_library_id}`);
        const clause = await clauseResponse.json();

        if (preserveFormatting) {
          // Replace text only, preserve formatting
          currentSelection!.insertText(
            clause.content.plain_text,
            Word.InsertLocation.replace
          );
        } else {
          // Replace with HTML content (library formatting)
          currentSelection!.insertHtml(
            clause.content.html,
            Word.InsertLocation.replace
          );
        }

        await context.sync();
      });

      // Close modal
      onCancelReplace();

      alert('Text replaced successfully!');

      // Go back to selection state
      showState('text-selected');
    } catch (error) {
      console.error('Error replacing text:', error);
      alert('Failed to replace text.');
    }
  }

  async function onCreateClauseClicked(): Promise<void> {
    if (!currentSelection) {
      alert('No text selected.');
      return;
    }

    try {
      const selectedText = await Word.run(async (context) => {
        currentSelection!.load(['text', 'html']);
        await context.sync();
        return {
          text: currentSelection!.text,
          html: currentSelection!.html
        };
      });

      // Open clause editor with pre-filled content
      // This would navigate to the clause editor component or open a dialog
      window.open(
        `/clause-library/create?content=${encodeURIComponent(selectedText.html)}`,
        '_blank'
      );
    } catch (error) {
      console.error('Error creating clause from selection:', error);
      alert('Failed to create clause.');
    }
  }

  function onBackToSelection(): void {
    showState('text-selected');
    currentComparisonResult = null;
  }

  function showState(state: 'no-selection' | 'text-selected' | 'comparison-results'): void {
    document.getElementById('no-selection')!.style.display = state === 'no-selection' ? 'block' : 'none';
    document.getElementById('text-selected')!.style.display = state === 'text-selected' ? 'block' : 'none';
    document.getElementById('comparison-results')!.style.display = state === 'comparison-results' ? 'block' :
  'none';
  }

  function showLoading(message: string): void {
    // TODO: Implement loading overlay
  }

  function hideLoading(): void {
    // TODO: Hide loading overlay
  }

● ---
  6. AI Service Integration

  6.1 Update AI Service for Clause Embeddings

  File: web_app/src/services/ai_service.py

  Add method for generating embeddings specifically for clauses:

  async def generate_clause_embedding(self, clause_text: str) -> List[float]:
      """
      Generate embedding optimized for clause comparison.
      Pre-processes text to focus on legal terminology and structure.
      """
      # Pre-process text for better legal clause matching
      processed_text = self._preprocess_clause_text(clause_text)

      return await self.generate_embedding(processed_text)

  def _preprocess_clause_text(self, text: str) -> str:
      """
      Pre-process clause text to improve embedding quality.
      - Normalize legal terminology
      - Remove boilerplate that doesn't affect meaning
      - Preserve key legal phrases
      """
      # Remove excessive whitespace
      text = ' '.join(text.split())

      # Normalize common legal variations
      replacements = {
          'shall not': 'must not',
          'shall': 'will',
          'herein': 'in this agreement',
          'hereinafter': 'after this',
          'aforementioned': 'mentioned above'
      }

      for old, new in replacements.items():
          text = text.replace(old, new)

      return text

  ---
  7. Testing Strategy

  7.1 Backend Testing

  File: web_app/tests/test_clause_library_service.py

  """
  Tests for ClauseLibraryService.
  """

  import pytest
  from datetime import datetime
  from src.services.clause_library_service import ClauseLibraryService
  from src.models.clause_library_models import (
      CreateClauseRequest, UpdateClauseRequest, CreateCategoryRequest
  )

  @pytest.fixture
  async def clause_service(cosmos_service, ai_service):
      """Create clause library service instance."""
      service = ClauseLibraryService(cosmos_service, ai_service)
      await service.initialize()
      return service

  @pytest.fixture
  def sample_clause_request():
      """Sample clause creation request."""
      return CreateClauseRequest(
          name="Test Indemnification Clause",
          description="Test clause for unit testing",
          category_id="indemnification_mutual_broad",
          content_html="<p>This is a <strong>test</strong> clause with <span class='variable'
  data-var='CONTRACTOR_PARTY'>Contractor</span>.</p>",
          tags=["test", "indemnification"],
          contract_types=["MSA"],
          jurisdictions=["multi-state"],
          risk_level="medium",
          complexity="medium"
      )

  @pytest.mark.asyncio
  async def test_create_clause(clause_service, sample_clause_request):
      """Test creating a new clause."""
      clause = await clause_service.create_clause(
          sample_clause_request,
          "test@example.com"
      )

      assert clause.id is not None
      assert clause.name == sample_clause_request.name
      assert clause.category_id == sample_clause_request.category_id
      assert clause.version.version_number == 1
      assert clause.version.is_current is True
      assert len(clause.variables) > 0
      assert clause.embedding is not None

  @pytest.mark.asyncio
  async def test_update_clause(clause_service, sample_clause_request):
      """Test updating an existing clause."""
      # Create clause
      clause = await clause_service.create_clause(
          sample_clause_request,
          "test@example.com"
      )

      # Update clause
      update_request = UpdateClauseRequest(
          name="Updated Test Clause",
          description="Updated description"
      )

      updated_clause = await clause_service.update_clause(
          clause.id,
          update_request,
          "test@example.com"
      )

      assert updated_clause.name == "Updated Test Clause"
      assert updated_clause.description == "Updated description"
      assert updated_clause.audit.modified_by == "test@example.com"

  @pytest.mark.asyncio
  async def test_create_clause_version(clause_service, sample_clause_request):
      """Test creating a new version of a clause."""
      # Create clause
      clause = await clause_service.create_clause(
          sample_clause_request,
          "test@example.com"
      )

      # Create new version
      new_version = await clause_service.create_clause_version(
          clause.id,
          "Updated for compliance",
          "test@example.com"
      )

      assert new_version.id != clause.id
      assert new_version.version.version_number == 2
      assert new_version.version.is_current is True
      assert new_version.version.parent_version_id == clause.id
      assert new_version.version.change_notes == "Updated for compliance"

      # Verify old version is no longer current
      old_clause = await clause_service.get_clause(clause.id)
      assert old_clause.version.is_current is False

  @pytest.mark.asyncio
  async def test_search_clauses(clause_service, sample_clause_request):
      """Test searching clauses."""
      # Create test clauses
      await clause_service.create_clause(sample_clause_request, "test@example.com")

      request2 = sample_clause_request.model_copy()
      request2.name = "Different Clause"
      request2.tags = ["different"]
      await clause_service.create_clause(request2, "test@example.com")

      # Search by category
      from src.models.clause_library_models import SearchClausesRequest
      search_request = SearchClausesRequest(
          category_id=sample_clause_request.category_id
      )

      results = await clause_service.search_clauses(search_request)

      assert results.total_count >= 2
      assert all(c.category_id == sample_clause_request.category_id for c in results.clauses)

  @pytest.mark.asyncio
  async def test_compare_clause(clause_service, sample_clause_request):
      """Test clause comparison with AI."""
      # Create clause
      clause = await clause_service.create_clause(
          sample_clause_request,
          "test@example.com"
      )

      # Compare with similar text
      from src.models.clause_library_models import CompareClauseRequest
      compare_request = CompareClauseRequest(
          clause_id=clause.id,
          contract_text="This is a similar test clause with Contractor Party."
      )

      comparison = await clause_service.compare_clause(
          compare_request,
          "test@example.com"
      )

      assert comparison.id is not None
      assert comparison.clause_library_id == clause.id
      assert comparison.comparison.similarity_score >= 0.0
      assert comparison.comparison.similarity_score <= 1.0
      assert comparison.risk_analysis.overall_risk in ["low", "medium", "high"]
      assert isinstance(comparison.recommendations, list)

  @pytest.mark.asyncio
  async def test_suggest_clause(clause_service, sample_clause_request):
      """Test AI clause suggestion."""
      # Create test clauses
      await clause_service.create_clause(sample_clause_request, "test@example.com")

      # Suggest clauses for similar text
      from src.models.clause_library_models import SuggestClauseRequest
      suggest_request = SuggestClauseRequest(
          contract_text="Indemnification clause with contractor liability",
          top_k=3
      )

      suggestions = await clause_service.suggest_clause(suggest_request)

      assert len(suggestions) > 0
      assert len(suggestions) <= 3

      for clause, score in suggestions:
          assert 0.0 <= score <= 1.0
          assert clause.id is not None

  @pytest.mark.asyncio
  async def test_create_category(clause_service):
      """Test creating a new category."""
      request = CreateCategoryRequest(
          name="Test Category",
          description="Test category description",
          parent_id="indemnification",
          icon="test-icon"
      )

      category = await clause_service.create_category(request, "test@example.com")

      assert category.id is not None
      assert category.name == "Test Category"
      assert category.parent_id == "indemnification"
      assert category.level == 2
      assert "indemnification" in category.path

  @pytest.mark.asyncio
  async def test_get_category_tree(clause_service):
      """Test retrieving category tree."""
      tree = await clause_service.get_category_tree()

      assert len(tree) > 0
      assert all(node.category.level == 1 for node in tree)

      # Verify tree structure
      for node in tree:
          if node.children:
              assert all(child.category.parent_id == node.category.id for child in node.children)

  7.2 Frontend Testing

  File: query-builder/src/app/clause-library/services/clause-library.service.spec.ts

  import { TestBed } from '@angular/core/testing';
  import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
  import { ClauseLibraryService } from './clause-library.service';
  import { CreateClauseRequest, Clause } from '../models/clause.models';

  describe('ClauseLibraryService', () => {
    let service: ClauseLibraryService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
      TestBed.configureTestingModule({
        imports: [HttpClientTestingModule],
        providers: [ClauseLibraryService]
      });

      service = TestBed.inject(ClauseLibraryService);
      httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
      httpMock.verify();
    });

    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should create a clause', (done) => {
      const request: CreateClauseRequest = {
        name: 'Test Clause',
        category_id: 'test_category',
        content_html: '<p>Test content</p>'
      };

      const mockResponse: Clause = {
        id: 'test-id',
        type: 'clause',
        name: 'Test Clause',
        category_id: 'test_category',
        category_path: ['test'],
        category_path_display: 'Test',
        content: {
          html: '<p>Test content</p>',
          plain_text: 'Test content'
        },
        variables: [],
        metadata: {
          tags: [],
          contract_types: [],
          jurisdictions: []
        },
        version: {
          version_number: 1,
          version_label: 'v1.0',
          is_current: true,
          created_by: 'test@example.com',
          created_date: '2025-01-01T00:00:00Z'
        },
        usage_stats: {
          times_used: 0
        },
        audit: {
          created_by: 'test@example.com',
          created_date: '2025-01-01T00:00:00Z'
        },
        status: 'active'
      };

      service.createClause(request).subscribe(clause => {
        expect(clause.id).toBe('test-id');
        expect(clause.name).toBe('Test Clause');
        done();
      });

      const req = httpMock.expectOne('/api/clause-library/clauses');
      expect(req.request.method).toBe('POST');
      req.flush(mockResponse);
    });

    it('should get category tree', (done) => {
      const mockTree = [
        {
          category: {
            id: 'cat1',
            type: 'category' as const,
            level: 1 as const,
            name: 'Category 1',
            path: ['cat1'],
            display_path: 'Category 1',
            order: 1,
            is_predefined: true,
            clause_count: 5,
            status: 'active' as const
          },
          children: [],
          clause_count: 5
        }
      ];

      service.getCategoryTree().subscribe(tree => {
        expect(tree.length).toBe(1);
        expect(tree[0].category.name).toBe('Category 1');
        done();
      });

      const req = httpMock.expectOne('/api/clause-library/categories/tree');
      expect(req.request.method).toBe('GET');
      req.flush(mockTree);
    });

    it('should search clauses', (done) => {
      const mockResponse = {
        clauses: [],
        total_count: 0,
        page: 1,
        page_size: 20
      };

      service.searchClauses({ query: 'test' }).subscribe(response => {
        expect(response.total_count).toBe(0);
        done();
      });

      const req = httpMock.expectOne('/api/clause-library/clauses/search');
      expect(req.request.method).toBe('POST');
      req.flush(mockResponse);
    });
  });

  7.3 Integration Testing

  File: web_app/tests/test_clause_library_integration.py

  """
  Integration tests for Clause Library end-to-end workflows.
  """

  import pytest
  from fastapi.testclient import TestClient
  from web_app import app

  client = TestClient(app)

  @pytest.mark.integration
  def test_complete_clause_workflow():
      """Test complete workflow: create, update, version, compare."""

      # 1. Create a clause
      create_response = client.post("/api/clause-library/clauses", json={
          "name": "Integration Test Clause",
          "category_id": "indemnification_mutual_broad",
          "content_html": "<p>Test indemnification clause content.</p>",
          "tags": ["test"],
          "contract_types": ["MSA"]
      })

      assert create_response.status_code == 201
      clause = create_response.json()
      clause_id = clause["id"]

      # 2. Get the clause
      get_response = client.get(f"/api/clause-library/clauses/{clause_id}")
      assert get_response.status_code == 200

      # 3. Update the clause
      update_response = client.put(f"/api/clause-library/clauses/{clause_id}", json={
          "name": "Updated Integration Test Clause"
      })
      assert update_response.status_code == 200
      updated_clause = update_response.json()
      assert updated_clause["name"] == "Updated Integration Test Clause"

      # 4. Create a new version
      version_response = client.post(
          f"/api/clause-library/clauses/{clause_id}/versions",
          json={"change_notes": "Updated for testing"}
      )
      assert version_response.status_code == 200
      new_version = version_response.json()
      assert new_version["version"]["version_number"] == 2

      # 5. Compare with contract text
      compare_response = client.post("/api/clause-library/compare", json={
          "clause_id": new_version["id"],
          "contract_text": "Similar indemnification clause with different wording."
      })
      assert compare_response.status_code == 200
      comparison = compare_response.json()
      assert "comparison" in comparison
      assert "risk_analysis" in comparison
      assert "recommendations" in comparison

      # 6. Search for the clause
      search_response = client.post("/api/clause-library/clauses/search", json={
          "query": "Integration Test",
          "page": 1,
          "page_size": 20
      })
      assert search_response.status_code == 200
      search_results = search_response.json()
      assert search_results["total_count"] >= 1

  @pytest.mark.integration
  def test_ai_suggestion_workflow():
      """Test AI-powered clause suggestion workflow."""

      # Create test clauses
      for i in range(3):
          client.post("/api/clause-library/clauses", json={
              "name": f"Suggestion Test Clause {i}",
              "category_id": "indemnification_mutual_broad",
              "content_html": f"<p>Indemnification clause variation {i}</p>",
              "tags": ["test", "suggestion"]
          })

      # Request suggestions
      suggest_response = client.post("/api/clause-library/suggest", json={
          "contract_text": "Indemnification and liability protection clause",
          "top_k": 5
      })

      assert suggest_response.status_code == 200
      suggestions = suggest_response.json()
      assert "suggestions" in suggestions
      assert len(suggestions["suggestions"]) > 0

      # Verify suggestions have similarity scores
      for suggestion in suggestions["suggestions"]:
          assert "clause" in suggestion
          assert "similarity_score" in suggestion
          assert 0.0 <= suggestion["similarity_score"] <= 1.0

  ---
  8. Implementation Phases

  Phase 1: Foundation & Backend (Weeks 1-2)

  Week 1: Database & Models
  - Create CosmosDB containers (clause_library, clause_categories)
  - Run setup scripts (setup_clause_library_containers.py)
  - Implement data models (clause_library_models.py)
  - Initialize predefined categories and system variables
  - Test database connectivity and queries

  Week 2: Backend Services & APIs
  - Implement ClauseLibraryService core CRUD operations
  - Implement category management methods
  - Implement variable management methods
  - Create API router (clause_library_router.py)
  - Integrate with main web_app.py
  - Write unit tests for service layer
  - Test all API endpoints with Postman/curl

  Deliverables:
  - Functional backend API for clause management
  - Database containers with sample data
  - Unit test coverage ≥80%
  - API documentation (endpoints, request/response schemas)

  ---
  Phase 2: AI Integration & Comparison (Weeks 3-4)

  Week 3: AI Comparison Engine
  - Implement AI comparison logic in ClauseLibraryService
  - Build comparison prompt template
  - Implement response parsing for differences, risks, recommendations
  - Add embedding generation for clauses
  - Test comparison accuracy with sample clauses

  Week 4: AI Suggestion System
  - Implement vector search for clause suggestions
  - Optimize embedding strategy for legal text
  - Implement suggestion ranking algorithm
  - Add caching for frequently compared clauses
  - Write integration tests for AI features
  - Performance testing (response time <3s for comparison)

  Deliverables:
  - Working AI comparison with risk analysis and recommendations
  - AI-powered clause suggestion feature
  - Performance benchmarks and optimization report
  - Integration test coverage ≥70%

  ---
  Phase 3: Frontend Development (Weeks 5-6)

  Week 5: Angular Components
  - Create clause-library module structure
  - Implement ClauseLibraryService (TypeScript)
  - Build ClauseEditorComponent with TinyMCE
  - Build ClauseListComponent with search/filter
  - Build CategoryTreeComponent for navigation
  - Implement routing and navigation

  Week 6: UI/UX Polish
  - Build ClauseViewerComponent for preview
  - Build VariableManagerComponent
  - Add form validation and error handling
  - Implement pagination and infinite scroll
  - Add loading states and progress indicators
  - Responsive design testing (desktop/tablet)
  - Accessibility testing (WCAG 2.1 AA)

  Deliverables:
  - Fully functional Angular clause library UI
  - Rich text editor with variable insertion
  - Category management interface
  - Responsive and accessible design
  - Frontend unit tests ≥70%

  ---
  Phase 4: Word Add-in Integration (Weeks 7-8)

  Week 7: Basic Add-in Features
  - Update Office Add-in manifest
  - Create clause-library-taskpane.html
  - Implement clause-library-taskpane.ts
  - Build text selection detection
  - Implement manual clause dropdown selection
  - Build comparison results display
  - Test in Word Desktop and Word Online

  Week 8: Advanced Add-in Features
  - Implement AI clause suggestion in add-in
  - Build "Create Clause from Selection" feature
  - Implement recommendation application logic
  - Build replacement options modal (formatting, track changes)
  - Add localStorage for AI suggest preference
  - Implement error handling and retry logic
  - Cross-browser testing (Chrome, Edge, Firefox)

  Deliverables:
  - Functional Word add-in for clause comparison
  - AI-powered clause suggestion in Word
  - Text replacement with formatting options
  - Create clause from selection feature
  - Add-in testing report (compatibility matrix)

  ---
  Phase 5: Testing & Refinement (Week 9)

  Testing Focus:
  - End-to-end integration testing (full workflows)
  - Performance testing (load times, API response times)
  - Security testing (input validation, SQL injection, XSS)
  - Usability testing with sample users
  - Cross-browser compatibility testing
  - Accessibility audit (WCAG 2.1 AA compliance)
  - Bug fixes and performance optimization

  Documentation:
  - User guide for clause library management
  - Developer documentation (API, architecture, deployment)
  - Video tutorials (creating clauses, using Word add-in)
  - FAQ and troubleshooting guide

  Deliverables:
  - Complete test report with all issues resolved
  - User and developer documentation
  - Training materials
  - Sign-off for production deployment

  ---
  Phase 6: Deployment & Launch (Week 10)

  Deployment Steps:
  - Deploy backend to Azure App Service
  - Configure production CosmosDB containers
  - Deploy frontend to production environment
  - Publish Word add-in to Microsoft AppSource (if applicable)
  - Configure monitoring and alerting (Application Insights)
  - Set up backup and disaster recovery
  - Production smoke testing

  Launch Activities:
  - Soft launch with beta users
  - Collect feedback and iterate
  - Full launch announcement
  - Monitor system performance and usage metrics
  - On-call support for first week

  Deliverables:
  - Production-ready system in Azure
  - Monitoring dashboards configured
  - Launch announcement and training sessions
  - Post-launch support plan

  ---
  9. Migration & Deployment

  9.1 Database Migration Script

  File: web_app/migrate_clause_library.py

  """
  Migration script for setting up Clause Library in existing environment.
  """

  import asyncio
  import logging
  from setup_clause_library_containers import setup_containers

  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)

  async def migrate():
      """Run migration for clause library."""
      logger.info("Starting Clause Library migration...")

      try:
          await setup_containers()
          logger.info("✅ Clause Library migration completed successfully!")
          return True
      except Exception as e:
          logger.error(f"❌ Migration failed: {e}", exc_info=True)
          return False

  if __name__ == "__main__":
      success = asyncio.run(migrate())
      exit(0 if success else 1)

  9.2 Deployment Checklist

  Pre-Deployment:
  - Review all code changes for security vulnerabilities
  - Ensure all environment variables are configured
  - Verify Azure resources (CosmosDB, App Service, OpenAI) are provisioned
  - Run full test suite and verify all tests pass
  - Review and update API documentation
  - Prepare rollback plan

  Deployment:
  - Run database migration script (migrate_clause_library.py)
  - Deploy backend API to Azure App Service
  - Deploy frontend to production CDN/hosting
  - Update Word add-in manifest and publish
  - Verify all services are running and healthy
  - Run smoke tests on production environment

  Post-Deployment:
  - Monitor application logs for errors
  - Check Application Insights for performance metrics
  - Verify user can access clause library features
  - Collect initial usage feedback
  - Document any issues and create follow-up tasks

  9.3 Rollback Plan

  If critical issues are discovered post-deployment:

  1. Backend Rollback:
    - Revert to previous App Service deployment slot
    - Or redeploy previous working version
  2. Database Rollback:
    - Clause library containers are additive (no existing data affected)
    - Can disable feature flag to hide clause library UI
    - Delete new containers if necessary: clause_library, clause_categories
  3. Frontend Rollback:
    - Revert to previous frontend deployment
    - Remove clause library routes from Angular app
  4. Word Add-in Rollback:
    - Remove clause library button from manifest
    - Republish previous add-in version

  ---
  10. Post-Implementation Enhancements (Future Phases)

  Phase 2 Features (Future)

  - Contract Building from Clauses: Assemble complete contracts from library clauses
  - Bulk Import/Export: Import clauses from Word docs, export to templates
  - Advanced Search: Full-text search with Elasticsearch integration
  - Clause Analytics: Usage analytics, effectiveness tracking
  - Compliance Integration: Link clauses to compliance rules
  - Multi-language Support: Internationalization for global teams
  - Collaboration Features: Comments, reviews, approval workflows
  - Clause Templates: Pre-built clause templates for common scenarios
  - Version Comparison: Diff view between clause versions
  - Audit Trail: Detailed history of all clause changes

  ---
  Summary

  This implementation plan provides a comprehensive roadmap for building the Clause Library functionality with:

  ✅ Advanced Data Models with version history and hierarchical categories✅ Robust Backend API with full CRUD
  operations and AI integration✅ Modern Angular Frontend with TinyMCE rich text editing✅ Word Add-in Integration
  for seamless document workflow✅ AI-Powered Features for comparison, risk analysis, and suggestions✅
  Comprehensive Testing Strategy across all layers✅ Phased Implementation for manageable development and
  deployment✅ Minimal Impact on existing functionality through modular design

  Estimated Timeline: 10 weeks for full implementationTeam Size: 2-3 developers (1 backend, 1 frontend, 1 DevOps/QA)

● Implementation Plan Complete!

  I've created a comprehensive implementation plan for your Clause Library functionality. Here's what's included:

  📋 Key Components

  1. Data Models & Schemas - Complete document structures for:
    - Clauses with version history
    - 3-level hierarchical categories
    - System and custom variables
    - Comparison results with AI analysis
  2. Backend Implementation - Full Python/FastAPI backend with:
    - ClauseLibraryService for all business logic
    - REST API endpoints for CRUD operations
    - AI integration for comparison and suggestions
    - CosmosDB setup scripts with predefined categories
  3. Frontend Implementation - Angular components using:
    - TinyMCE Angular integration for rich text editing
    - Category tree navigation
    - Search/filter functionality
    - Clause editor with variable insertion
  4. Word Add-in Integration - Office.js implementation with:
    - Text selection and comparison
    - AI-powered clause suggestions (with localStorage preference)
    - Replacement options (formatting, track changes)
    - Create clause from selection
  5. Testing Strategy - Comprehensive test coverage:
    - Backend unit tests (≥80% coverage target)
    - Frontend component tests (≥70% coverage)
    - Integration tests for end-to-end workflows
    - Word add-in compatibility testing
  6. 10-Week Implementation Plan - Phased approach:
    - Phase 1: Database & Backend (Weeks 1-2)
    - Phase 2: AI Integration (Weeks 3-4)
    - Phase 3: Frontend Development (Weeks 5-6)
    - Phase 4: Word Add-in (Weeks 7-8)
    - Phase 5: Testing & Refinement (Week 9)
    - Phase 6: Deployment (Week 10)

  🚀 Getting Started

  To begin implementation:

  1. Review the complete plan above - All code, schemas, and architectural decisions
  2. Start with Phase 1 - Database setup is the foundation
  3. Run the setup script: python web_app/setup_clause_library_containers.py
  4. Follow the weekly checklists in each phase

  📊 Key Technical Decisions Made

  - ✅ TinyMCE for Word-compatible rich text editing
  - ✅ Separate containers for clauses and categories
  - ✅ HTML storage with variable spans for formatting
  - ✅ AI-powered comparison using Azure OpenAI
  - ✅ localStorage for AI suggest preference
  - ✅ Version history with manual version creation
  - ✅ Minimal impact - All new functionality in separate modules

  ❓ Next Steps

  Would you like me to:
  1. Create any specific component implementation first?
  2. Generate sample data for testing?
  3. Create a detailed API specification document?
  4. Help with the initial database setup?
  5. Create additional documentation or diagrams?
