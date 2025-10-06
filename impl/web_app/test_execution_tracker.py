"""
Test script to demonstrate query execution tracking and visualization.

This script tests the execution tracker with various query scenarios:
1. Successful optimized path (ENTITY_FIRST)
2. Aggregation query (ENTITY_AGGREGATION)
3. Multi-filter query (CONTRACT_DIRECT)
4. Fallback scenario (entity not found)

Usage:
    python test_execution_tracker.py
"""

import asyncio
import logging
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, '.')

from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.rag_data_service import RAGDataService
from src.services.config_service import ConfigService
from src.services.logging_level_service import LoggingLevelService

# Initialize
load_dotenv(override=True)
logging.basicConfig(
    format="%(asctime)s - %(message)s",
    level=logging.DEBUG
)


async def test_entity_first_query():
    """Test optimized entity-first query"""
    print("\n" + "=" * 80)
    print("TEST 1: Entity-First Query (Optimized Path)")
    print("=" * 80)

    ai_svc = AiService()
    nosql_svc = CosmosNoSQLService()
    rag_svc = RAGDataService(ai_svc, nosql_svc)

    # Query that should trigger ENTITY_FIRST strategy
    query = "Show all contracts governed by Florida"

    print(f"\nQuery: {query}")
    print("\nExecuting...\n")

    rdr = await rag_svc.get_rag_data(query, max_doc_count=10, enable_tracking=True)

    tracker = rdr.get_execution_tracker()
    if tracker:
        print(tracker.visualize_ascii())
    else:
        print("❌ No execution tracker available")

    print(f"\nDocuments returned: {len(rdr.get_rag_docs())}")


async def test_aggregation_query():
    """Test aggregation query using pre-computed stats"""
    print("\n" + "=" * 80)
    print("TEST 2: Aggregation Query (Pre-computed Stats)")
    print("=" * 80)

    ai_svc = AiService()
    nosql_svc = CosmosNoSQLService()
    rag_svc = RAGDataService(ai_svc, nosql_svc)

    # Query that should trigger ENTITY_AGGREGATION strategy
    query = "How many contracts are governed by Delaware?"

    print(f"\nQuery: {query}")
    print("\nExecuting...\n")

    rdr = await rag_svc.get_rag_data(query, max_doc_count=10, enable_tracking=True)

    tracker = rdr.get_execution_tracker()
    if tracker:
        print(tracker.visualize_ascii())
    else:
        print("❌ No execution tracker available")

    print(f"\nDocuments returned: {len(rdr.get_rag_docs())}")


async def test_multi_filter_query():
    """Test multi-filter direct contract query"""
    print("\n" + "=" * 80)
    print("TEST 3: Multi-Filter Query (Contract Direct)")
    print("=" * 80)

    ai_svc = AiService()
    nosql_svc = CosmosNoSQLService()
    rag_svc = RAGDataService(ai_svc, nosql_svc)

    # Query with multiple filters
    query = "Show MSA contracts with Microsoft governed by Washington"

    print(f"\nQuery: {query}")
    print("\nExecuting...\n")

    rdr = await rag_svc.get_rag_data(query, max_doc_count=10, enable_tracking=True)

    tracker = rdr.get_execution_tracker()
    if tracker:
        print(tracker.visualize_ascii())
    else:
        print("❌ No execution tracker available")

    print(f"\nDocuments returned: {len(rdr.get_rag_docs())}")


async def test_fallback_scenario():
    """Test fallback from entity-first to vector search"""
    print("\n" + "=" * 80)
    print("TEST 4: Fallback Scenario (Entity Not Found → Vector Search)")
    print("=" * 80)

    ai_svc = AiService()
    nosql_svc = CosmosNoSQLService()
    rag_svc = RAGDataService(ai_svc, nosql_svc)

    # Query with non-existent entity
    query = "Contracts with XYZ Corporation that don't exist"

    print(f"\nQuery: {query}")
    print("\nExecuting...\n")

    rdr = await rag_svc.get_rag_data(query, max_doc_count=10, enable_tracking=True)

    tracker = rdr.get_execution_tracker()
    if tracker:
        print(tracker.visualize_ascii())
    else:
        print("❌ No execution tracker available")

    print(f"\nDocuments returned: {len(rdr.get_rag_docs())}")
    print(f"Final strategy used: {rdr.get_strategy()}")


async def main():
    """Run all tests"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " QUERY EXECUTION TRACKER - DEMONSTRATION".center(78) + "║")
    print("╚" + "═" * 78 + "╝")

    # Check if in contracts mode
    graph_mode = ConfigService.envvar("CAIG_GRAPH_MODE", "libraries")
    if graph_mode != "contracts":
        print(f"\n⚠️  WARNING: CAIG_GRAPH_MODE is '{graph_mode}', not 'contracts'")
        print("These tests are designed for contracts mode.")
        print("Set CAIG_GRAPH_MODE=contracts in your environment to run these tests.\n")
        return

    try:
        # Run tests sequentially
        await test_entity_first_query()
        await test_aggregation_query()
        await test_multi_filter_query()
        await test_fallback_scenario()

        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        logging.exception(e)


if __name__ == "__main__":
    asyncio.run(main())
