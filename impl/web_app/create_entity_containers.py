"""
Script to create the required CosmosDB containers for contract entity management.
Usage: python create_entity_containers.py
"""

import asyncio
import logging
from dotenv import load_dotenv
from azure.cosmos.partition_key import PartitionKey
from azure.cosmos.aio import CosmosClient
from src.services.config_service import ConfigService


async def create_entity_containers():
    """Create the required containers for contract entity management."""
    
    # Get CosmosDB connection details
    cosmos_uri = ConfigService.cosmosdb_nosql_uri()
    cosmos_key = ConfigService.cosmosdb_nosql_key()
    database_name = ConfigService.graph_source_db()
    
    logging.info(f"Connecting to database: {database_name}")
    
    # Create CosmosDB client
    async with CosmosClient(cosmos_uri, cosmos_key) as client:
        database = client.get_database_client(database_name)
        
        # Define containers to create with their partition keys
        containers = [
            {
                "id": "contractor_parties",
                "partition_key": PartitionKey(path="/pk"),
                "description": "Stores contractor party entities"
            },
            {
                "id": "contracting_parties", 
                "partition_key": PartitionKey(path="/pk"),
                "description": "Stores contracting party entities"
            },
            {
                "id": "governing_laws",
                "partition_key": PartitionKey(path="/pk"),
                "description": "Stores governing law entities"
            },
            {
                "id": "contract_types",
                "partition_key": PartitionKey(path="/pk"),
                "description": "Stores contract type entities"
            },
            {
                "id": "config",
                "partition_key": PartitionKey(path="/pk"),
                "description": "Stores configuration and reference documents"
            }
        ]
        
        # Create each container
        for container_config in containers:
            try:
                # Try to create the container
                container = await database.create_container(
                    id=container_config["id"],
                    partition_key=container_config["partition_key"]
                )
                logging.info(f"✅ Created container: {container_config['id']} - {container_config['description']}")
            except Exception as e:
                if "Conflict" in str(e):
                    logging.info(f"ℹ️  Container already exists: {container_config['id']}")
                else:
                    logging.error(f"❌ Error creating container {container_config['id']}: {str(e)}")
    
    logging.info("Container creation completed!")
    
    # Also create contract-specific containers if they don't exist
    logging.info("\nChecking contract data containers...")
    
    contract_containers = [
        {
            "id": "contracts",
            "partition_key": PartitionKey(path="/pk"),
            "description": "Stores parent contract documents"
        },
        {
            "id": "contract_clauses",
            "partition_key": PartitionKey(path="/pk"),
            "description": "Stores contract clause documents with embeddings"
        },
        {
            "id": "contract_chunks",
            "partition_key": PartitionKey(path="/pk"),
            "description": "Stores contract chunk documents with embeddings"
        }
    ]
    
    async with CosmosClient(cosmos_uri, cosmos_key) as client:
        database = client.get_database_client(database_name)
        
        for container_config in contract_containers:
            try:
                container = await database.create_container(
                    id=container_config["id"],
                    partition_key=container_config["partition_key"]
                )
                logging.info(f"✅ Created container: {container_config['id']} - {container_config['description']}")
            except Exception as e:
                if "Conflict" in str(e):
                    logging.info(f"ℹ️  Container already exists: {container_config['id']}")
                else:
                    logging.error(f"❌ Error creating container {container_config['id']}: {str(e)}")


if __name__ == "__main__":
    # Initialize environment and logging
    load_dotenv(override=True)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    
    # Run the container creation
    asyncio.run(create_entity_containers())