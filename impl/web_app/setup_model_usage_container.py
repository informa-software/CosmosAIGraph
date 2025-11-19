"""
Setup script for model_usage container

Creates and configures the CosmosDB container for tracking LLM usage.
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
        partition_key_path: Partition key path (e.g., "/user_email")
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


async def setup_model_usage_container():
    """
    Create and configure the model_usage container.

    Container structure:
    - Partition key: /user_email
    - TTL: None (optional: 7776000 seconds = 90 days for data retention policy)
    - Composite indexes for efficient analytics queries
    """
    logger.info("=" * 70)
    logger.info("Setting up model_usage container")
    logger.info("=" * 70)

    # Initialize CosmosDB service
    logger.info("Initializing CosmosDB service...")
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()
    database = cosmos_service.set_db(ConfigService.graph_source_db())

    container_name = "model_usage"
    partition_key_path = "/user_email"

    # Load index policy from configuration file
    try:
        index_policy = load_index_policy("cosmosdb_nosql_model_usage_index_policy.json")
        logger.info("Loaded index policy successfully")
    except Exception as e:
        logger.error(f"Failed to load index policy: {e}")
        return False

    # Create container
    try:
        created = await create_container_if_not_exists(
            database=database,
            container_name=container_name,
            partition_key_path=partition_key_path,
            index_policy=index_policy,
            default_ttl=None  # Optional: Set to 7776000 for 90-day retention
        )

        # Display configuration
        logger.info("")
        logger.info("Container configuration:")
        logger.info(f"  Name: {container_name}")
        logger.info(f"  Partition Key: {partition_key_path}")
        logger.info(f"  Composite Indexes: {len(index_policy.get('compositeIndexes', []))}")
        logger.info("")
        logger.info("Composite indexes configured:")
        for i, composite_index in enumerate(index_policy.get('compositeIndexes', []), 1):
            paths = [f"{idx['path']} ({idx['order']})" for idx in composite_index]
            logger.info(f"  {i}. {' → '.join(paths)}")

        logger.info("")
        logger.info("✓ model_usage container setup complete!")
        logger.info("")

        if created:
            logger.info("\n⚠️  Important: Wait 1-2 minutes for indexes to build before querying")

    except Exception as e:
        logger.error(f"Failed to setup model_usage container: {e}")
        return False

    # Clean up async resources
    try:
        if cosmos_service._client:
            await cosmos_service._client.close()
            logger.debug("CosmosDB client closed successfully")
    except Exception as e:
        logger.warning(f"Error closing CosmosDB client: {e}")

    return True


async def main():
    """Main execution function."""
    success = await setup_model_usage_container()

    if success:
        logger.info("")
        logger.info("=" * 70)
        logger.info("Setup completed successfully!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. LLM tracking is already integrated into all services")
        logger.info("2. Run some operations to generate tracking data:")
        logger.info("   - SPARQL queries")
        logger.info("   - Contract comparisons")
        logger.info("   - Compliance evaluations")
        logger.info("3. Verify data in CosmosDB portal (model_usage container)")
        logger.info("4. Access analytics via endpoints:")
        logger.info("   - GET /api/analytics/operation-breakdown?user_email=system&days=7")
        logger.info("   - GET /api/analytics/token-efficiency?user_email=system&days=7")
        logger.info("   - GET /api/analytics/error-analysis?user_email=system&days=7")
        logger.info("")
    else:
        logger.error("Setup failed. Please check the error messages above.")

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Setup failed with error: {e}")
        logger.exception(e)
        sys.exit(1)
