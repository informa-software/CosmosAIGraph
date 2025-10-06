"""
Test LLM Execution Mode

Verifies that LLM-generated queries execute correctly when CAIG_LLM_EXECUTION_MODE=execution.
Tests both successful execution and fallback scenarios.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Set up path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure environment for LLM execution mode
os.environ["CAIG_USE_LLM_STRATEGY"] = "true"
os.environ["CAIG_LLM_EXECUTION_MODE"] = "execution"
os.environ["CAIG_GRAPH_MODE"] = "contracts"

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ontology_service import OntologyService
from src.services.contract_strategy_builder import ContractStrategyBuilder
from src.services.rag_data_service import RAGDataService, RAGDataResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_query(rag_service: RAGDataService, query: str, description: str, test_num: int):
    """Test a single query and report results."""
    print(f"\n{'='*80}")
    print(f"Test {test_num}: {description}")
    print(f"Query: {query}")
    print(f"{'='*80}")

    try:
        # Execute query
        rdr = RAGDataResult(query)
        await rag_service.get_database_rag_data(query, rdr, max_doc_count=5)

        # Report results
        print(f"\n[RESULTS]")
        print(f"  Documents found: {len(rdr.docs)}")
        print(f"  Execution time: {rdr.get_elapsed_time():.0f}ms")

        # Check if LLM execution was used
        if rdr.tracker:
            print(f"\n[EXECUTION PATH]")
            print(f"  Strategy: {rdr.tracker.strategy}")
            print(f"  Query type: {rdr.tracker.query_type}")

            if rdr.tracker.llm_query_text:
                print(f"  LLM execution: YES")
                print(f"  LLM query preview: {rdr.tracker.llm_query_text[:100]}...")
                if rdr.tracker.fallback_count > 0:
                    print(f"  Fallback used: YES ({rdr.tracker.fallback_count} times)")
                else:
                    print(f"  Fallback used: NO")
            else:
                print(f"  LLM execution: NO (rule-based)")

            # Show ASCII visualization
            print(f"\n[EXECUTION TRACE]")
            print(rdr.tracker.visualize_ascii())

        # Show sample documents
        if rdr.docs:
            print(f"\n[SAMPLE DOCUMENT]")
            doc = rdr.docs[0]
            if "contract_name" in doc:
                print(f"  Contract: {doc.get('contract_name', 'N/A')}")
                print(f"  Type: {doc.get('contract_type', 'N/A')}")
                print(f"  Value: ${doc.get('contract_value', 0):,.0f}")
            elif "clause_type" in doc:
                print(f"  Clause Type: {doc.get('clause_type', 'N/A')}")
                print(f"  Contract: {doc.get('contract_name', 'N/A')}")
            else:
                print(f"  ID: {doc.get('id', 'N/A')}")

        print(f"\n[OK] Test {test_num} completed successfully")
        return True

    except Exception as e:
        print(f"\n[ERROR] Test {test_num} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run LLM execution mode tests."""
    print(f"\n{'='*80}")
    print(f"LLM EXECUTION MODE TEST")
    print(f"{'='*80}")
    print(f"Environment:")
    print(f"  CAIG_USE_LLM_STRATEGY: {os.environ.get('CAIG_USE_LLM_STRATEGY')}")
    print(f"  CAIG_LLM_EXECUTION_MODE: {os.environ.get('CAIG_LLM_EXECUTION_MODE')}")
    print(f"  CAIG_GRAPH_MODE: {os.environ.get('CAIG_GRAPH_MODE')}")

    # Initialize services
    print(f"\nInitializing services...")
    config = ConfigService()
    cosmos_service = CosmosNoSQLService()
    ontology_service = OntologyService()
    strategy_builder = ContractStrategyBuilder()

    rag_service = RAGDataService(
        nosql_svc=cosmos_service,
        ontology_svc=ontology_service,
        strategy_builder=strategy_builder
    )

    print(f"[OK] Services initialized")

    # Test queries
    test_cases = [
        {
            "query": "What contracts are governed by Delaware?",
            "description": "Simple entity query - should use ENTITY_FIRST strategy"
        },
        {
            "query": "Show me MSA contracts with Microsoft",
            "description": "Multi-entity query - contract type + contractor party"
        },
        {
            "query": "Which contracts are governed by Alabama and contain an indemnification clause?",
            "description": "Complex query using contract_clauses collection"
        },
        {
            "query": "What are the highest value contracts?",
            "description": "Aggregation query - may use CONTRACT_DIRECT"
        },
        {
            "query": "Find contracts related to cloud services",
            "description": "Semantic query - should use VECTOR_SEARCH"
        }
    ]

    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        success = await test_query(
            rag_service,
            test_case["query"],
            test_case["description"],
            i
        )
        results.append(success)

    # Summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")

    if all(results):
        print(f"\n[OK] All tests passed - LLM execution mode working correctly")
    else:
        print(f"\n[WARNING] Some tests failed - check output above")

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
