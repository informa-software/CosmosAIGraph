"""
Test that LLM-generated query text appears in execution trace
"""

import sys
from pathlib import Path

# Add src to path
web_app_dir = Path(__file__).parent
sys.path.insert(0, str(web_app_dir))

from src.services.query_execution_tracker import QueryExecutionTracker, ExecutionStatus


def test_llm_query_in_trace():
    """Test that LLM query text is included in ASCII trace."""

    # Create tracker with LLM plan
    llm_plan = {
        "strategy": "ENTITY_FIRST",
        "query_type": "SQL",
        "query_text": "SELECT * FROM c WHERE c.id = 'acme_corp'",
        "confidence": 0.95,
        "reasoning": "Single entity lookup is optimal",
        "validation_status": "valid"
    }

    tracker = QueryExecutionTracker(
        query="Show me contracts with Acme Corp",
        planned_strategy="db",
        llm_plan=llm_plan
    )

    # Add a step
    step = tracker.start_step(
        name="Query entity collection",
        strategy="db",
        collection="contractor_parties"
    )

    tracker.complete_step(
        step=step,
        status=ExecutionStatus.SUCCESS,
        ru_cost=2.5,
        docs_found=1,
        metadata={"key": "acme_corp"}
    )

    tracker.finish()

    # Generate ASCII trace
    trace = tracker.visualize_ascii()

    print("="*80)
    print("EXECUTION TRACE WITH LLM QUERY")
    print("="*80)
    print(trace)
    print("="*80)

    # Verify LLM query text is present
    assert "LLM Generated Query:" in trace, "LLM query section missing"
    assert "SELECT * FROM c WHERE c.id = 'acme_corp'" in trace, "LLM query text missing"
    assert "LLM STRATEGY: ENTITY_FIRST" in trace, "LLM strategy missing"
    assert "Confidence: 0.95" in trace, "Confidence missing"
    assert "Query Type: SQL" in trace, "Query type missing"

    print("\n[OK] All assertions passed - LLM query text appears in trace")


def test_multiline_sparql_in_trace():
    """Test that multi-line SPARQL query is properly formatted in trace."""

    sparql_query = """PREFIX caig: <http://cosmosdb.com/caig#>
SELECT ?contract ?contractor ?state WHERE {
  ?contract a caig:Contract .
  ?contract caig:is_performed_by ?contractor .
  ?contract caig:is_governed_by ?state .
  ?contractor caig:display_name "Acme Corp" .
  ?state caig:normalized_name "california" .
}"""

    llm_plan = {
        "strategy": "GRAPH_TRAVERSAL",
        "query_type": "SPARQL",
        "query_text": sparql_query,
        "confidence": 0.92,
        "reasoning": "Multi-hop relationship query requires graph traversal",
        "validation_status": "valid"
    }

    tracker = QueryExecutionTracker(
        query="Find contracts between Acme Corp and clients in California",
        planned_strategy="db",
        llm_plan=llm_plan
    )

    step = tracker.start_step(
        name="Query contracts",
        strategy="db",
        collection="contracts"
    )

    tracker.complete_step(
        step=step,
        status=ExecutionStatus.SUCCESS,
        ru_cost=5.2,
        docs_found=3
    )

    tracker.finish()

    # Generate ASCII trace
    trace = tracker.visualize_ascii()

    print("\n" + "="*80)
    print("EXECUTION TRACE WITH MULTI-LINE SPARQL")
    print("="*80)
    print(trace)
    print("="*80)

    # Verify multi-line SPARQL is present
    assert "LLM Generated Query:" in trace, "LLM query section missing"
    assert "PREFIX caig:" in trace, "SPARQL PREFIX missing"
    assert "SELECT ?contract ?contractor ?state WHERE" in trace, "SPARQL SELECT missing"
    assert "LLM STRATEGY: GRAPH_TRAVERSAL [MISMATCH]" in trace, "Strategy mismatch indicator missing"

    print("\n[OK] All assertions passed - Multi-line SPARQL appears in trace")


def test_invalid_llm_plan_in_trace():
    """Test that validation errors are shown in trace."""

    llm_plan = {
        "strategy": "INVALID_STRATEGY",
        "validation_status": "invalid",
        "validation_error": "Unknown strategy: INVALID_STRATEGY"
    }

    tracker = QueryExecutionTracker(
        query="Test invalid query",
        planned_strategy="db",
        llm_plan=llm_plan
    )

    step = tracker.start_step(
        name="Fallback to direct query",
        strategy="db",
        collection="contracts"
    )

    tracker.complete_step(
        step=step,
        status=ExecutionStatus.SUCCESS,
        ru_cost=3.0,
        docs_found=5
    )

    tracker.finish()

    # Generate ASCII trace
    trace = tracker.visualize_ascii()

    print("\n" + "="*80)
    print("EXECUTION TRACE WITH INVALID LLM PLAN")
    print("="*80)
    print(trace)
    print("="*80)

    # Verify validation error is shown
    assert "LLM STRATEGY: [invalid]" in trace, "Invalid status missing"
    assert "Validation Error:" in trace, "Validation error message missing"

    print("\n[OK] All assertions passed - Validation errors appear in trace")


if __name__ == "__main__":
    test_llm_query_in_trace()
    test_multiline_sparql_in_trace()
    test_invalid_llm_plan_in_trace()
    print("\n" + "="*80)
    print("ALL TESTS PASSED - LLM query text is properly displayed in execution traces")
    print("="*80)
