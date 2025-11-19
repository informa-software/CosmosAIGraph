"""
Setup Job Queue Container

This script creates the job_queue container in CosmosDB
with the appropriate partition key, indexing policy, and TTL configuration.

This container stores batch processing jobs for contract comparison
and query operations with automatic cleanup after 7 days.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_job_queue_container():
    """Create job_queue container with TTL enabled"""

    logger.info("=" * 70)
    logger.info("Starting Job Queue container setup...")
    logger.info("=" * 70)

    # Initialize Cosmos service
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()
    database = cosmos_service.set_db(ConfigService.graph_source_db())

    container_name = "job_queue"

    # Load index policy
    index_policy_path = Path(__file__).parent / "config" / "cosmosdb_nosql_job_queue_index_policy.json"

    logger.info(f"Loading index policy from: {index_policy_path}")

    with open(index_policy_path, 'r') as f:
        index_policy = json.load(f)

    # Container properties
    # Partition by user_id for efficient user-scoped queries
    partition_key_path = "/user_id"

    # TTL: 7 days (604800 seconds) for automatic cleanup of completed/failed jobs
    # Set to -1 to disable TTL, or None to not enable TTL feature
    default_ttl = 604800  # 7 days

    logger.info(f"Creating container: {container_name}")
    logger.info(f"Partition key: {partition_key_path}")
    logger.info(f"TTL: {default_ttl} seconds (7 days)")
    logger.info(f"Index policy loaded: {len(str(index_policy))} bytes")

    try:
        # Create container if it doesn't exist (idempotent operation)
        container = await database.create_container_if_not_exists(
            id=container_name,
            partition_key={"paths": [partition_key_path], "kind": "Hash"},
            indexing_policy=index_policy,
            default_ttl=default_ttl
        )

        logger.info(f"✓ Container '{container_name}' ready")

        # Verify container properties
        properties = await container.read()

        logger.info("")
        logger.info("Container verification:")
        logger.info(f"  - Container ID: {properties['id']}")
        logger.info(f"  - Partition Key: {properties['partitionKey']}")
        logger.info(f"  - Default TTL: {properties.get('defaultTtl', 'Not set')} seconds")
        logger.info(f"  - Indexing Mode: {properties['indexingPolicy']['indexingMode']}")
        logger.info(f"  - Excluded Paths: {len(properties['indexingPolicy']['excludedPaths'])}")
        logger.info(f"  - Composite Indexes: {len(properties['indexingPolicy'].get('compositeIndexes', []))}")

        logger.info("")
        logger.info("Composite indexes configured:")
        for i, composite_index in enumerate(properties['indexingPolicy'].get('compositeIndexes', []), 1):
            paths = [f"{idx['path']} ({idx['order']})" for idx in composite_index]
            logger.info(f"  {i}. {' → '.join(paths)}")

        logger.info("")
        logger.info("========================================")
        logger.info("Job Queue Container Setup Complete!")
        logger.info("========================================")
        logger.info("")
        logger.info("Container ready for use:")
        logger.info(f"  Database: {ConfigService.graph_source_db()}")
        logger.info(f"  Container: {container_name}")
        logger.info(f"  Partition Key: {partition_key_path}")
        logger.info(f"  TTL: {default_ttl} seconds (automatic cleanup after 7 days)")
        logger.info("")
        logger.info("This container stores:")
        logger.info("  - Batch comparison jobs")
        logger.info("  - Batch query jobs")
        logger.info("  - Job status and progress tracking")
        logger.info("  - Links to results in analysis_results container")
        logger.info("")
        logger.info("TTL Configuration:")
        logger.info("  - Completed/failed jobs are automatically deleted after 7 days")
        logger.info("  - Each document has 'ttl' field for custom retention")
        logger.info("  - Set document.ttl = -1 to never expire")
        logger.info("  - Set document.ttl = N to expire in N seconds")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Deploy JobService for job management")
        logger.info("2. Deploy background worker for job processing")
        logger.info("3. Integrate with Compare Contracts page")
        logger.info("4. Integrate with Query Contracts page")
        logger.info("5. Set up SSE endpoints for progress tracking")
        logger.info("")
        logger.info("⚠️  Wait 1-2 minutes for indexes to build before querying")
        logger.info("")

    except Exception as e:
        logger.error(f"Failed to setup container: {str(e)}")
        raise

    finally:
        await cosmos_service.close()


async def main():
    """Main execution function."""
    try:
        await setup_job_queue_container()
        logger.info("Setup completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Setup failed with error: {e}")
        logger.exception(e)
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)
