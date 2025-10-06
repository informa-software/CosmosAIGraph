"""
Unit Test for LLM Query Executor

Tests LLMQueryExecutor class with mocked services to verify execution logic
without requiring live Azure resources.
"""

import sys
import logging
import asyncio
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Dict, List

# Add src to path
web_app_dir = Path(__file__).parent
sys.path.insert(0, str(web_app_dir))

from src.services.llm_query_executor import LLMQueryExecutor, ExecutionResult
from src.services.llm_query_planner import LLMQueryPlan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_sql_execution_success():
    """Test successful SQL query execution."""
    print("\n[TEST 1] SQL Execution - Success Case")
    print("-" * 80)

    # Create mock CosmosDB service
    mock_cosmos = Mock()
    mock_cosmos.set_container = Mock()
    mock_cosmos.query_items = AsyncMock(return_value=[
        {"id": "1", "contract_name": "Contract A", "contract_value": 100000},
        {"id": "2", "contract_name": "Contract B", "contract_value": 200000}
    ])
    mock_cosmos.last_request_charge = Mock(return_value=5.2)  # It's a method, not an attribute

    # Create LLM plan
    llm_plan = LLMQueryPlan(
        strategy="ENTITY_FIRST",
        fallback_strategy="VECTOR_SEARCH",
        query_type="SQL",
        query_text="SELECT * FROM c WHERE c.governing_law_state = 'Delaware'",
        execution_plan={"collection": "contracts"},
        confidence=0.95,
        reasoning="Simple entity lookup",
        raw_response={}
    )

    # Execute
    executor = LLMQueryExecutor(cosmos_service=mock_cosmos)
    result = await executor.execute_plan(llm_plan)

    # Verify
    assert result.success, "SQL execution should succeed"
    assert len(result.documents) == 2, "Should return 2 documents"
    assert result.ru_cost == 5.2, "Should capture RU cost"
    assert result.executed_query == llm_plan.query_text, "Should record executed query"
    assert not result.fallback_used, "Should not use fallback"

    print(f"[OK] Documents: {len(result.documents)}, RU cost: {result.ru_cost}")
    return True


async def test_sql_validation_failure():
    """Test SQL validation failure triggers fallback."""
    print("\n[TEST 2] SQL Validation Failure")
    print("-" * 80)

    # Create mock service (won't be called)
    mock_cosmos = Mock()
    mock_cosmos.set_container = Mock()
    mock_cosmos.query_items = AsyncMock()

    # Create invalid LLM plan (low confidence)
    llm_plan = LLMQueryPlan(
        strategy="ENTITY_FIRST",
        fallback_strategy="VECTOR_SEARCH",
        query_type="SQL",
        query_text="SELECT * FROM c",
        execution_plan={"collection": "contracts"},
        confidence=0.3,  # Below threshold
        reasoning="Low confidence query",
        raw_response={}
    )

    # Execute
    executor = LLMQueryExecutor(cosmos_service=mock_cosmos)
    result = await executor.execute_plan(llm_plan)

    # Verify
    assert not result.success, "Should fail validation"
    assert result.fallback_used, "Should indicate fallback needed"
    assert "Low confidence" in result.error_message, "Should explain validation failure"
    assert len(result.documents) == 0, "Should return no documents"

    # Verify query was not executed
    mock_cosmos.query_items.assert_not_called()

    print(f"[OK] Validation correctly failed: {result.error_message}")
    return True


async def test_sparql_execution_success():
    """Test successful SPARQL query execution."""
    print("\n[TEST 3] SPARQL Execution - Success Case")
    print("-" * 80)

    # Create mock ontology service
    mock_ontology = Mock()
    mock_ontology.sparql_query = Mock(return_value={
        'results': {
            'bindings': [
                {'contractor': {'value': 'Acme Corp'}, 'contract_count': {'value': '5'}},
                {'contractor': {'value': 'TechCo'}, 'contract_count': {'value': '3'}}
            ]
        }
    })

    # Create LLM plan
    llm_plan = LLMQueryPlan(
        strategy="GRAPH_TRAVERSAL",
        fallback_strategy="VECTOR_SEARCH",
        query_type="SPARQL",
        query_text="""
        PREFIX caig: <http://cosmosdb.com/caig#>
        SELECT ?contractor (COUNT(?contract) as ?contract_count)
        WHERE {
            ?contract a caig:Contract .
            ?contract caig:hasContractor ?contractor .
        }
        GROUP BY ?contractor
        """,
        execution_plan={"estimated_ru_cost": 15.0},
        confidence=0.85,
        reasoning="Graph traversal for aggregation",
        raw_response={}
    )

    # Execute
    executor = LLMQueryExecutor(ontology_service=mock_ontology)
    result = await executor.execute_plan(llm_plan)

    # Verify
    assert result.success, "SPARQL execution should succeed"
    assert len(result.documents) == 2, "Should return 2 result bindings"
    assert result.documents[0]['contractor'] == 'Acme Corp', "Should parse SPARQL bindings"
    assert result.documents[0]['contract_count'] == '5', "Should extract values from bindings"
    assert result.ru_cost == 15.0, "Should use estimated RU cost"

    print(f"[OK] SPARQL results: {len(result.documents)} bindings")
    return True


async def test_unknown_query_type():
    """Test unknown query type handling."""
    print("\n[TEST 4] Unknown Query Type")
    print("-" * 80)

    # Create LLM plan with unknown type
    llm_plan = LLMQueryPlan(
        strategy="UNKNOWN_STRATEGY",
        fallback_strategy="VECTOR_SEARCH",
        query_type="CYPHER",  # Not supported
        query_text="MATCH (n) RETURN n",
        execution_plan={},
        confidence=0.95,
        reasoning="Graph query",
        raw_response={}
    )

    # Execute
    executor = LLMQueryExecutor()
    result = await executor.execute_plan(llm_plan)

    # Verify
    assert not result.success, "Should fail for unknown query type"
    assert result.fallback_used, "Should indicate fallback needed"
    assert "Unknown query type" in result.error_message or "Unknown strategy" in result.error_message

    print(f"[OK] Unknown type correctly rejected: {result.error_message}")
    return True


async def test_execution_error_handling():
    """Test execution error handling."""
    print("\n[TEST 5] Execution Error Handling")
    print("-" * 80)

    # Create mock service that raises exception
    mock_cosmos = Mock()
    mock_cosmos.set_container = Mock()
    mock_cosmos.query_items = AsyncMock(side_effect=Exception("CosmosDB connection failed"))
    mock_cosmos.last_request_charge = Mock(return_value=0.0)

    # Create valid LLM plan
    llm_plan = LLMQueryPlan(
        strategy="ENTITY_FIRST",
        fallback_strategy="VECTOR_SEARCH",
        query_type="SQL",
        query_text="SELECT * FROM c",
        execution_plan={"collection": "contracts"},
        confidence=0.9,
        reasoning="Simple query",
        raw_response={}
    )

    # Execute
    executor = LLMQueryExecutor(cosmos_service=mock_cosmos)
    result = await executor.execute_plan(llm_plan)

    # Verify
    assert not result.success, "Should fail on execution error"
    assert result.fallback_used, "Should indicate fallback needed"
    assert "connection failed" in result.error_message.lower(), "Should capture error message"

    print(f"[OK] Error correctly handled: {result.error_message}")
    return True


async def main():
    """Run all unit tests."""
    print("\n" + "="*80)
    print("LLM QUERY EXECUTOR UNIT TESTS")
    print("="*80)

    tests = [
        ("SQL Execution Success", test_sql_execution_success),
        ("SQL Validation Failure", test_sql_validation_failure),
        ("SPARQL Execution Success", test_sparql_execution_success),
        ("Unknown Query Type", test_unknown_query_type),
        ("Execution Error Handling", test_execution_error_handling)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success, None))
        except AssertionError as e:
            logger.error(f"[FAIL] {test_name}: {str(e)}")
            results.append((test_name, False, str(e)))
        except Exception as e:
            logger.error(f"[ERROR] {test_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False, str(e)))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for test_name, success, error in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")
        if error:
            print(f"     Error: {error}")

    print(f"\nTotal: {total}, Passed: {passed}, Failed: {total - passed}")

    if passed == total:
        print("\n[OK] All unit tests passed!")
        return True
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
