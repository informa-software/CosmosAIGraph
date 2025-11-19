"""
Setup Word Add-in Evaluations Container

This script creates the word_addin_evaluations container in CosmosDB
with the appropriate partition key and indexing policy.
"""

import asyncio
import json
import logging
from pathlib import Path

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_word_addin_container():
    """Create word_addin_evaluations container"""

    logger.info("Starting Word Add-in container setup...")

    # Initialize Cosmos service
    cosmos_service = CosmosNoSQLService()
    await cosmos_service.initialize()
    database = cosmos_service.set_db(ConfigService.graph_source_db())

    container_name = "word_addin_evaluations"

    # Load index policy
    index_policy_path = Path(__file__).parent / "config" / "cosmosdb_nosql_word_addin_evaluations_index_policy.json"

    logger.info(f"Loading index policy from: {index_policy_path}")

    with open(index_policy_path, 'r') as f:
        index_policy = json.load(f)

    # Container properties
    partition_key_path = "/evaluation_id"

    logger.info(f"Creating container: {container_name}")
    logger.info(f"Partition key: {partition_key_path}")
    logger.info(f"Index policy loaded: {len(str(index_policy))} bytes")

    try:
        # Create container if it doesn't exist (idempotent operation)
        container = await database.create_container_if_not_exists(
            id=container_name,
            partition_key={"paths": [partition_key_path], "kind": "Hash"},
            indexing_policy=index_policy
        )

        logger.info(f"✓ Container '{container_name}' ready")

        # Verify container properties
        properties = await container.read()

        logger.info("Container verification:")
        logger.info(f"  - Container ID: {properties['id']}")
        logger.info(f"  - Partition Key: {properties['partitionKey']}")
        logger.info(f"  - Indexing Mode: {properties['indexingPolicy']['indexingMode']}")
        logger.info(f"  - Excluded Paths: {len(properties['indexingPolicy']['excludedPaths'])}")
        logger.info(f"  - Composite Indexes: {len(properties['indexingPolicy'].get('compositeIndexes', []))}")

        logger.info("")
        logger.info("========================================")
        logger.info("Word Add-in Container Setup Complete!")
        logger.info("========================================")
        logger.info("")
        logger.info("Container ready for use:")
        logger.info(f"  Database: {ConfigService.graph_source_db()}")
        logger.info(f"  Container: {container_name}")
        logger.info(f"  Partition Key: {partition_key_path}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Deploy backend API with WordAddinEvaluationService")
        logger.info("2. Test evaluation endpoint")
        logger.info("3. Verify data storage")
        logger.info("")

    except Exception as e:
        logger.error(f"Failed to setup container: {str(e)}")
        raise

    finally:
        await cosmos_service.close()


if __name__ == "__main__":
    asyncio.run(setup_word_addin_container())
