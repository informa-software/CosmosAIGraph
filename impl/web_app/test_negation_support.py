"""
Test script for negation support in contract queries.

Tests:
1. Negation detection in ContractStrategyBuilder
2. Query optimizer builds correct filters with negations
3. SQL generation handles != operator
"""

import asyncio
import logging
from src.services.contract_strategy_builder import ContractStrategyBuilder
from src.services.query_optimizer import QueryOptimizer
from src.services.config_service import ConfigService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


def test_negation_detection():
    """Test that negations are detected in queries"""
    print("\n" + "="*80)
    print("TEST 1: Negation Detection")
    print("="*80)

    test_cases = [
        "Show all contracts not governed by Alabama",
        "List contracts excluding Florida",
        "Find contracts except for California",
        "Get contracts other than Texas",
        "Show contracts without Washington"
    ]

    # Mock AI service (not needed for negation detection)
    class MockAiService:
        pass

    sb = ContractStrategyBuilder(MockAiService())

    for query in test_cases:
        print(f"\nQuery: {query}")
        strategy = {
            "natural_language": query,
            "strategy": "",
            "entities": {},
            "negations": {},
            "algorithm": "",
            "confidence": 0.0,
            "name": ""
        }

        sb.detect_negation_patterns(strategy)

        print(f"Negations detected: {strategy['negations']}")

        # Verify negation was detected
        has_negations = any(strategy['negations'].values())
        print(f"✅ PASS" if has_negations else "❌ FAIL: No negations detected")


def test_query_optimizer_filter_building():
    """Test that QueryOptimizer builds correct filters with negations"""
    print("\n" + "="*80)
    print("TEST 2: Query Optimizer Filter Building")
    print("="*80)

    # Create strategy object with negation
    strategy_obj = {
        "natural_language": "Show all contracts not governed by Alabama",
        "strategy": "db",
        "entities": {},
        "negations": {
            "contractor_parties": [],
            "contracting_parties": [],
            "governing_law_states": [{
                "normalized_name": "alabama",
                "display_name": "Alabama",
                "confidence": 0.9,
                "match_type": "negation_pattern"
            }],
            "contract_types": []
        },
        "algorithm": "",
        "confidence": 0.8,
        "name": "contract_query"
    }

    optimizer = QueryOptimizer(strategy_obj)
    filter_dict = optimizer._build_composite_filter()

    print(f"\nBuilt filter: {filter_dict}")

    # Verify negation is marked with $ne
    expected_filter = {"governing_law_state": {"$ne": "alabama"}}
    if filter_dict == expected_filter:
        print("✅ PASS: Filter correctly built with $ne operator")
    else:
        print(f"❌ FAIL: Expected {expected_filter}, got {filter_dict}")


def test_sql_generation():
    """Test that SQL query generation handles negations"""
    print("\n" + "="*80)
    print("TEST 3: SQL Generation with Negations")
    print("="*80)

    # Simulate filter dict with negation
    filter_dict = {"governing_law_state": {"$ne": "alabama"}}

    # Simulate SQL WHERE clause building (same logic as in cosmos_nosql_service.py)
    where_clauses = []
    for field, value in filter_dict.items():
        if isinstance(value, dict) and "$ne" in value:
            negated_value = value["$ne"]
            where_clauses.append(f"c.{field} != '{negated_value}'")
        else:
            where_clauses.append(f"c.{field} = '{value}'")

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
    sql = f"SELECT TOP 100 * FROM c WHERE {where_clause}"

    print(f"\nGenerated SQL:\n{sql}")

    expected_sql = "SELECT TOP 100 * FROM c WHERE c.governing_law_state != 'alabama'"
    if sql == expected_sql:
        print("✅ PASS: SQL correctly uses != operator")
    else:
        print(f"❌ FAIL: Expected:\n{expected_sql}\nGot:\n{sql}")


def test_multi_filter_with_negation():
    """Test multi-filter query with both positive and negative filters"""
    print("\n" + "="*80)
    print("TEST 4: Multi-Filter with Positive and Negative Filters")
    print("="*80)

    # Strategy with both positive entity and negation
    strategy_obj = {
        "natural_language": "Show MSA contracts not governed by Alabama",
        "strategy": "db",
        "entities": {
            "contractor_parties": [],
            "contracting_parties": [],
            "governing_law_states": [],
            "contract_types": [{
                "normalized_name": "msa",
                "display_name": "MSA",
                "confidence": 0.95,
                "match_type": "exact"
            }]
        },
        "negations": {
            "contractor_parties": [],
            "contracting_parties": [],
            "governing_law_states": [{
                "normalized_name": "alabama",
                "display_name": "Alabama",
                "confidence": 0.9,
                "match_type": "negation_pattern"
            }],
            "contract_types": []
        },
        "algorithm": "",
        "confidence": 0.8,
        "name": "contract_query"
    }

    optimizer = QueryOptimizer(strategy_obj)
    filter_dict = optimizer._build_composite_filter()

    print(f"\nBuilt filter: {filter_dict}")

    # Build SQL
    where_clauses = []
    for field, value in filter_dict.items():
        if isinstance(value, dict) and "$ne" in value:
            negated_value = value["$ne"]
            where_clauses.append(f"c.{field} != '{negated_value}'")
        else:
            where_clauses.append(f"c.{field} = '{value}'")

    where_clause = " AND ".join(where_clauses)
    sql = f"SELECT TOP 100 * FROM c WHERE {where_clause}"

    print(f"\nGenerated SQL:\n{sql}")

    # Verify both filters are present
    has_positive = "c.contract_type = 'msa'" in sql
    has_negative = "c.governing_law_state != 'alabama'" in sql

    if has_positive and has_negative:
        print("✅ PASS: SQL correctly combines positive and negative filters")
    else:
        print(f"❌ FAIL: Missing filters - positive: {has_positive}, negative: {has_negative}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("NEGATION SUPPORT TEST SUITE")
    print("="*80)

    try:
        test_negation_detection()
        test_query_optimizer_filter_building()
        test_sql_generation()
        test_multi_filter_with_negation()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH ERROR: {str(e)}")
        logging.exception(e)
