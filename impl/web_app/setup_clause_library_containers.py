"""
Setup script for Clause Library CosmosDB containers.
"""

import asyncio
import json
from pathlib import Path
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_containers():
    """Create and configure Clause Library containers."""

    # Load configuration
    cosmos_uri = os.environ.get("CAIG_COSMOSDB_NOSQL_URI")
    cosmos_key = os.environ.get("CAIG_COSMOSDB_NOSQL_KEY")
    database_name = os.environ.get("CAIG_COSMOSDB_NOSQL_DBNAME", "caig")

    if not cosmos_uri or not cosmos_key:
        logger.error("Missing required environment variables: CAIG_COSMOSDB_NOSQL_URI and/or CAIG_COSMOSDB_NOSQL_KEY")
        sys.exit(1)

    logger.info(f"Connecting to CosmosDB database: {database_name}")

    async with CosmosClient(cosmos_uri, cosmos_key) as client:
        database = client.get_database_client(database_name)

        # Create clause_library container
        logger.info("Creating clause_library container...")
        try:
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
            logger.info("✓ clause_library container created")
        except Exception as e:
            logger.error(f"Error creating clause_library container: {e}")
            raise

        # Create clause_categories container
        logger.info("Creating clause_categories container...")
        try:
            categories_policy = json.loads(
                Path("config/cosmosdb_nosql_clause_categories_index_policy.json").read_text()
            )

            await database.create_container_if_not_exists(
                id="clause_categories",
                partition_key=PartitionKey(path="/level"),
                indexing_policy=categories_policy
            )
            logger.info("✓ clause_categories container created")
        except Exception as e:
            logger.error(f"Error creating clause_categories container: {e}")
            raise

        # Initialize system variables
        logger.info("Initializing system variables...")
        try:
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
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "contractor_party",
                        "default_value": "[Contractor Party]"
                    },
                    {
                        "name": "CONTRACTING_PARTY",
                        "display_name": "Contracting Party",
                        "description": "The party requesting the work/services",
                        "data_type": "string",
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "contracting_party",
                        "default_value": "[Contracting Party]"
                    },
                    {
                        "name": "CONTRACT_TYPE",
                        "display_name": "Contract Type",
                        "description": "Type of contract (MSA, SOW, NDA, etc.)",
                        "data_type": "string",
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "contract_type",
                        "default_value": "[Contract Type]"
                    },
                    {
                        "name": "EFFECTIVE_DATE",
                        "display_name": "Effective Date",
                        "description": "Contract effective date",
                        "data_type": "date",
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "effective_date",
                        "default_value": "[Effective Date]"
                    },
                    {
                        "name": "EXPIRATION_DATE",
                        "display_name": "Expiration Date",
                        "description": "Contract expiration date",
                        "data_type": "date",
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "expiration_date",
                        "default_value": "[Expiration Date]"
                    },
                    {
                        "name": "CONTRACT_VALUE",
                        "display_name": "Contract Value",
                        "description": "Total contract value",
                        "data_type": "currency",
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "total_amount",
                        "default_value": "[Contract Value]"
                    },
                    {
                        "name": "GOVERNING_LAW_STATE",
                        "display_name": "Governing Law State",
                        "description": "State whose laws govern the contract",
                        "data_type": "string",
                        "type": "system",
                        "source": "contract_metadata",
                        "metadata_field": "governing_law",
                        "default_value": "[Governing Law State]"
                    }
                ],
                "custom_variables": [],
                "audit": {
                    "created_by": "system",
                    "created_date": "2025-10-28T00:00:00Z",
                    "modified_by": "system",
                    "modified_date": "2025-10-28T00:00:00Z"
                }
            }

            await container.upsert_item(system_variables)
            logger.info("✓ System variables initialized")
        except Exception as e:
            logger.error(f"Error initializing system variables: {e}")
            raise

        # Initialize predefined categories
        logger.info("Initializing predefined categories...")
        try:
            await initialize_predefined_categories(database)
        except Exception as e:
            logger.error(f"Error initializing categories: {e}")
            raise

        logger.info("\n✅ All containers setup completed successfully!")


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
        },

        # Level 2 Categories (under Confidentiality)
        {
            "id": "confidentiality_mutual",
            "type": "category",
            "level": 2,
            "name": "Mutual NDA",
            "description": "Mutual non-disclosure agreements",
            "parent_id": "confidentiality",
            "path": ["confidentiality", "mutual"],
            "display_path": "Confidentiality > Mutual NDA",
            "order": 1,
            "icon": "shield-check",
            "is_predefined": True,
            "clause_count": 0,
            "status": "active"
        },
        {
            "id": "confidentiality_one_way",
            "type": "category",
            "level": 2,
            "name": "One-Way NDA",
            "description": "One-way non-disclosure agreements",
            "parent_id": "confidentiality",
            "path": ["confidentiality", "one_way"],
            "display_path": "Confidentiality > One-Way NDA",
            "order": 2,
            "icon": "arrow-right-circle",
            "is_predefined": True,
            "clause_count": 0,
            "status": "active"
        }
    ]

    for category in predefined_categories:
        await container.upsert_item(category)
        logger.info(f"  ✓ Created category: {category['display_path']}")


if __name__ == "__main__":
    try:
        asyncio.run(setup_containers())
        sys.exit(0)
    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        sys.exit(1)
