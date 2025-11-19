"""
Setup script for user preferences and model usage containers in CosmosDB.

This script automatically creates the following containers:
1. user_preferences - Stores user model preferences and settings
2. model_usage - Stores model usage tracking for analytics

Usage:
    python setup_user_preferences_container.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.config_service import ConfigService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_index_policy(policy_file: str) -> dict:
    """Load index policy from JSON file."""
    config_dir = Path(__file__).parent / "config"
    policy_path = config_dir / policy_file

    if not policy_path.exists():
        raise FileNotFoundError(f"Index policy file not found: {policy_path}")

    with open(policy_path, 'r') as f:
        return json.load(f)


async def create_container_if_not_exists(
    database,
    container_name: str,
    partition_key_path: str,
    index_policy: dict,
    default_ttl: int = None
) -> bool:
    """
    Create a container if it doesn't already exist.

    Args:
        database: Database client
        container_name: Name of the container to create
        partition_key_path: Partition key path (e.g., "/user_email")
        index_policy: Indexing policy dictionary
        default_ttl: Default time-to-live in seconds (None = no TTL)

    Returns:
        True if container was created, False if it already existed
    """
    try:
        # Check if container already exists
        existing_containers = []
        async for container in database.list_containers():
            existing_containers.append(container)

        container_exists = container_name in [c['id'] for c in existing_containers]

        if container_exists:
            logger.info(f"Container '{container_name}' already exists - skipping creation")
            return False

        # Create container
        logger.info(f"Creating container: {container_name}")

        container_settings = {
            "id": container_name,
            "partition_key": {
                "paths": [partition_key_path],
                "kind": "Hash"
            },
            "indexing_policy": index_policy
        }

        if default_ttl is not None:
            container_settings["default_ttl"] = default_ttl

        await database.create_container_if_not_exists(**container_settings)

        logger.info(f"✓ Container '{container_name}' created successfully")
        return True

    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to create container '{container_name}': {e.message}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating container '{container_name}': {str(e)}")
        raise


async def setup_containers():
    """Setup user preferences and model usage containers."""

    logger.info("="*80)
    logger.info("USER PREFERENCES & MODEL USAGE CONTAINERS SETUP")
    logger.info("="*80)

    # Get configuration
    cosmos_uri = ConfigService.cosmosdb_nosql_uri()
    cosmos_key = ConfigService.cosmosdb_nosql_key()
    db_name = ConfigService.graph_source_db()

    if not cosmos_uri or not cosmos_key:
        logger.error("CosmosDB connection details not found in environment variables")
        logger.error("Please set CAIG_COSMOSDB_NOSQL_URI and CAIG_COSMOSDB_NOSQL_KEY")
        return

    logger.info(f"Database: {db_name}")
    logger.info("")

    # Initialize Cosmos client
    client = None
    try:
        client = CosmosClient(cosmos_uri, credential=cosmos_key)
        database = client.get_database_client(db_name)

        # Track results
        containers_created = []
        containers_skipped = []

        # Container 1: user_preferences
        logger.info("Setting up user_preferences container...")
        user_prefs_policy = load_index_policy("cosmosdb_nosql_user_preferences_index_policy.json")

        if await create_container_if_not_exists(
            database=database,
            container_name="user_preferences",
            partition_key_path="/user_email",
            index_policy=user_prefs_policy
        ):
            containers_created.append("user_preferences")
        else:
            containers_skipped.append("user_preferences")

        logger.info("")

        # Container 2: model_usage
        logger.info("Setting up model_usage container...")
        model_usage_policy = load_index_policy("cosmosdb_nosql_model_usage_index_policy.json")

        if await create_container_if_not_exists(
            database=database,
            container_name="model_usage",
            partition_key_path="/user_email",
            index_policy=model_usage_policy
        ):
            containers_created.append("model_usage")
        else:
            containers_skipped.append("model_usage")

        logger.info("")
        logger.info("="*80)
        logger.info("SETUP SUMMARY")
        logger.info("="*80)
        logger.info(f"Containers created: {len(containers_created)}")
        for name in containers_created:
            logger.info(f"  ✓ {name}")

        logger.info(f"Containers skipped (already exist): {len(containers_skipped)}")
        for name in containers_skipped:
            logger.info(f"  - {name}")

        logger.info("")
        logger.info("Setup completed successfully!")
        logger.info("")

    except FileNotFoundError as e:
        logger.error(f"Configuration file error: {str(e)}")
        sys.exit(1)
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"CosmosDB error: {e.message}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if client:
            await client.close()


if __name__ == "__main__":
    asyncio.run(setup_containers())
