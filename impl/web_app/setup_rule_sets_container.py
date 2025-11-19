"""
Setup script for Rule Sets container in Cosmos DB.

Creates the rule_sets container with appropriate indexing policy
and populates it with default rule sets (NDA, MSA, General).

Usage:
    python setup_rule_sets_container.py

Author: Aleksey Savateyev, Microsoft, 2025
"""

import asyncio
import json
import logging
from datetime import datetime

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.rule_set_service import RuleSetService
from src.models.rule_set_models import RuleSetCreate

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Container configuration
CONTAINER_NAME = "rule_sets"
PARTITION_KEY_PATH = "/id"

# Index policy for rule_sets container
INDEX_POLICY = {
    "indexingMode": "consistent",
    "automatic": True,
    "includedPaths": [
        {
            "path": "/*"
        }
    ],
    "excludedPaths": [
        {
            "path": "/\"_etag\"/?"
        }
    ],
    "compositeIndexes": [
        [
            {
                "path": "/is_active",
                "order": "ascending"
            },
            {
                "path": "/name",
                "order": "ascending"
            }
        ]
    ]
}


# Default rule sets to create
DEFAULT_RULE_SETS = [
    {
        "name": "General Rules",
        "description": "General compliance rules applicable to all contract types",
        "suggested_contract_types": ["MSA", "NDA", "SOW", "Service Agreement", "Subscription"],
        "is_active": True
    },
    {
        "name": "NDA Rules",
        "description": "Compliance rules specific to Non-Disclosure Agreements",
        "suggested_contract_types": ["NDA"],
        "is_active": True
    },
    {
        "name": "MSA Rules",
        "description": "Compliance rules specific to Master Service Agreements",
        "suggested_contract_types": ["MSA"],
        "is_active": True
    }
]


async def create_container():
    """Create the rule_sets container if it doesn't exist."""
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()

    try:
        # Get the database proxy
        db_proxy = cosmos_service.set_db(ConfigService.graph_source_db())

        # Check if container already exists
        try:
            existing_containers = await cosmos_service.list_containers()
            if CONTAINER_NAME in existing_containers:
                logger.info(f"Container '{CONTAINER_NAME}' already exists")
                return True
        except Exception as e:
            logger.warning(f"Could not list containers: {str(e)}")

        # Container doesn't exist, create it
        logger.info(f"Creating container '{CONTAINER_NAME}'...")

        # Create container with index policy
        container = await db_proxy.create_container(
            id=CONTAINER_NAME,
            partition_key={
                "paths": [PARTITION_KEY_PATH],
                "kind": "Hash"
            },
            indexing_policy=INDEX_POLICY
        )

        logger.info(f"✅ Container '{CONTAINER_NAME}' created successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error creating container: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        await cosmos_service.close()


async def create_default_rule_sets():
    """Create default rule sets."""
    rule_set_service = RuleSetService()
    await rule_set_service.initialize()

    try:
        logger.info("Creating default rule sets...")

        for rule_set_data in DEFAULT_RULE_SETS:
            try:
                # Check if rule set already exists with this name
                existing = await rule_set_service.list_rule_sets(include_inactive=True)
                if any(rs.name == rule_set_data["name"] for rs in existing.rule_sets):
                    logger.info(f"  - Rule set '{rule_set_data['name']}' already exists, skipping")
                    continue

                # Create the rule set
                rule_set_create = RuleSetCreate(
                    name=rule_set_data["name"],
                    description=rule_set_data["description"],
                    suggested_contract_types=rule_set_data["suggested_contract_types"],
                    is_active=rule_set_data["is_active"],
                    rule_ids=[]  # No rules initially
                )

                created = await rule_set_service.create_rule_set(rule_set_create, created_by="setup_script")
                logger.info(f"  ✅ Created rule set: '{created.name}' (ID: {created.id})")

            except Exception as e:
                logger.error(f"  ❌ Error creating rule set '{rule_set_data['name']}': {str(e)}")

        logger.info("Default rule sets creation complete!")

    finally:
        await rule_set_service.close()


async def main():
    """Main setup function."""
    logger.info("="*80)
    logger.info("Rule Sets Container Setup")
    logger.info("="*80)

    # Step 1: Create container
    logger.info("\n📦 Step 1: Creating rule_sets container...")
    container_created = await create_container()

    if not container_created:
        logger.error("Failed to create container. Exiting.")
        return

    # Step 2: Create default rule sets
    logger.info("\n📋 Step 2: Creating default rule sets...")
    await create_default_rule_sets()

    logger.info("\n" + "="*80)
    logger.info("✅ Setup complete!")
    logger.info("="*80)
    logger.info("\nNext steps:")
    logger.info("1. View rule sets: GET http://localhost:8000/api/rule_sets")
    logger.info("2. Create custom rule sets via the API or UI")
    logger.info("3. Assign rules to rule sets when creating/editing rules")
    logger.info("4. Use rule sets when evaluating contracts")


if __name__ == "__main__":
    asyncio.run(main())
