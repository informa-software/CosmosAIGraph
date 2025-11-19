"""
Setup Compliance Containers

Creates the three CosmosDB containers needed for the compliance system:
- compliance_rules: Stores compliance rules
- compliance_results: Stores evaluation results
- evaluation_jobs: Stores async job tracking (with 7-day TTL)

Usage:
    python setup_compliance_containers.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from azure.cosmos import exceptions

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.util.fs import FS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_index_policy(filename: str) -> dict:
    """Load index policy from config file."""
    filepath = f"config/{filename}"
    try:
        content = FS.read(filepath)
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to load index policy from {filepath}: {e}")
        raise


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
        database: CosmosDB database proxy
        container_name: Name of the container to create
        partition_key_path: Partition key path (e.g., "/id")
        index_policy: Indexing policy dict
        default_ttl: Default time-to-live in seconds (None = off, -1 = no expiry)

    Returns:
        True if created, False if already exists
    """

    # Check if container already exists by listing all containers
    try:
        existing_containers = []
        async for container in database.list_containers():
            existing_containers.append(container)

        container_names = [c['id'] for c in existing_containers]

        if container_name in container_names:
            logger.info(f"Container '{container_name}' already exists")
            return False

    except Exception as e:
        logger.warning(f"Could not list containers: {e}. Attempting to create anyway...")

    # Container doesn't exist, create it
    logger.info(f"Creating container '{container_name}'...")

    try:
        # Create the container using create_container_if_not_exists
        # This is idempotent - won't fail if container already exists
        container = await database.create_container_if_not_exists(
            id=container_name,
            partition_key={"paths": [partition_key_path], "kind": "Hash"},
            indexing_policy=index_policy,
            default_ttl=default_ttl
        )

        logger.info(f"✅ Created container '{container_name}' successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create container '{container_name}': {e}")
        raise


async def setup_compliance_containers():
    """Main setup function to create all compliance containers."""
    logger.info("=" * 70)
    logger.info("Starting Compliance Containers Setup")
    logger.info("=" * 70)

    # Initialize CosmosDB service
    logger.info("Initializing CosmosDB service...")
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()
    database = cosmos_service.set_db(ConfigService.graph_source_db())

    containers_created = 0
    containers_skipped = 0

    # 1. Create compliance_rules container
    logger.info("\n[1/3] Setting up compliance_rules container...")
    try:
        index_policy = load_index_policy("cosmosdb_nosql_compliance_rules_index_policy.json")
        created = await create_container_if_not_exists(
            database=database,
            container_name="compliance_rules",
            partition_key_path="/id",
            index_policy=index_policy,
            default_ttl=None  # No TTL
        )
        if created:
            containers_created += 1
        else:
            containers_skipped += 1
    except Exception as e:
        logger.error(f"Failed to setup compliance_rules: {e}")
        return False

    # 2. Create compliance_results container
    logger.info("\n[2/3] Setting up compliance_results container...")
    try:
        index_policy = load_index_policy("cosmosdb_nosql_compliance_results_index_policy.json")
        created = await create_container_if_not_exists(
            database=database,
            container_name="compliance_results",
            partition_key_path="/contract_id",
            index_policy=index_policy,
            default_ttl=None  # No TTL
        )
        if created:
            containers_created += 1
        else:
            containers_skipped += 1
    except Exception as e:
        logger.error(f"Failed to setup compliance_results: {e}")
        return False

    # 3. Create evaluation_jobs container (with 7-day TTL)
    logger.info("\n[3/3] Setting up evaluation_jobs container...")
    try:
        index_policy = load_index_policy("cosmosdb_nosql_evaluation_jobs_index_policy.json")
        created = await create_container_if_not_exists(
            database=database,
            container_name="evaluation_jobs",
            partition_key_path="/id",
            index_policy=index_policy,
            default_ttl=604800  # 7 days in seconds
        )
        if created:
            containers_created += 1
        else:
            containers_skipped += 1
    except Exception as e:
        logger.error(f"Failed to setup evaluation_jobs: {e}")
        return False

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("Compliance Containers Setup Summary")
    logger.info("=" * 70)
    logger.info(f"✅ Containers created: {containers_created}")
    logger.info(f"ℹ️  Containers skipped (already exist): {containers_skipped}")
    logger.info("=" * 70)

    if containers_created > 0:
        logger.info("\n⚠️  Important: Wait 1-2 minutes for indexes to build before querying")

    logger.info("\n✅ Setup completed successfully!")

    # Clean up async resources
    try:
        if cosmos_service._client:
            await cosmos_service._client.close()
            logger.debug("CosmosDB client closed successfully")
    except Exception as e:
        logger.warning(f"Error closing CosmosDB client: {e}")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(setup_compliance_containers())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Setup failed with error: {e}")
        logger.exception(e)
        sys.exit(1)
