"""
Simplified test script for negation support - no external dependencies.
Tests the core logic without requiring module imports.
"""

import re


def test_negation_regex_patterns():
    """Test that negation regex patterns work correctly"""
    print("\n" + "="*80)
    print("TEST 1: Negation Regex Patterns")
    print("="*80)

    # Negation patterns from ContractStrategyBuilder
    negation_patterns = [
        (r'(?:not|n\'t)\s+(?:governed\s+by|with|from|in)\s+(\w+(?:\s+\w+)*)', 'governing_law_states'),
        (r'(?:excluding|except\s+for|other\s+than|without)\s+(\w+(?:\s+\w+)*)', None),
        (r'(?:not|exclude)\s+(\w+(?:\s+\w+)*?)(?:\s+contracts?|\s*$)', None),
    ]

    test_cases = [
        ("Show all contracts not governed by Alabama", "alabama", "governing_law_states"),
        ("List contracts excluding Florida", "florida", None),
        ("Find contracts except for California", "california", None),
        ("Get contracts other than Texas", "texas", None),
        ("Show contracts without Washington", "washington", None),
        ("Show contracts not governed by New York", "new york", "governing_law_states"),
    ]

    passed = 0
    failed = 0

    for query, expected_value, expected_type in test_cases:
        print(f"\nQuery: {query}")
        found = False

        for pattern, entity_type_hint in negation_patterns:
            matches = re.finditer(pattern, query.lower(), re.IGNORECASE)
            for match in matches:
                negated_value = match.group(1).strip()
                print(f"  Detected negation: {negated_value}")

                if negated_value == expected_value:
                    found = True
                    print(f"  [PASS] Correctly detected '{expected_value}'")
                    passed += 1
                    break
            if found:
                break

        if not found:
            print(f"  [FAIL] Did not detect expected value '{expected_value}'")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_filter_building():
    """Test SQL filter building with negations"""
    print("\n" + "="*80)
    print("TEST 2: SQL Filter Building")
    print("="*80)

    test_cases = [
        {
            "name": "Simple negation",
            "filter": {"governing_law_state": {"$ne": "alabama"}},
            "expected": "c.governing_law_state != 'alabama'"
        },
        {
            "name": "Positive filter",
            "filter": {"contract_type": "msa"},
            "expected": "c.contract_type = 'msa'"
        },
        {
            "name": "Mixed filters",
            "filter": {
                "contract_type": "msa",
                "governing_law_state": {"$ne": "alabama"}
            },
            "expected_contains": [
                "c.contract_type = 'msa'",
                "c.governing_law_state != 'alabama'"
            ]
        }
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Filter: {test['filter']}")

        # Build WHERE clause (same logic as cosmos_nosql_service.py)
        where_clauses = []
        for field, value in test['filter'].items():
            if isinstance(value, dict) and "$ne" in value:
                negated_value = value["$ne"]
                where_clauses.append(f"c.{field} != '{negated_value}'")
            else:
                where_clauses.append(f"c.{field} = '{value}'")

        where_clause = " AND ".join(where_clauses)
        print(f"Generated WHERE: {where_clause}")

        # Check result
        if "expected" in test:
            if where_clause == test["expected"]:
                print("[PASS]")
                passed += 1
            else:
                print(f"[FAIL] Expected '{test['expected']}'")
                failed += 1
        elif "expected_contains" in test:
            all_present = all(exp in where_clause for exp in test["expected_contains"])
            if all_present:
                print("[PASS]")
                passed += 1
            else:
                print(f"[FAIL] Not all expected fragments present")
                failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_complete_sql_query():
    """Test complete SQL query generation"""
    print("\n" + "="*80)
    print("TEST 3: Complete SQL Query Generation")
    print("="*80)

    test_cases = [
        {
            "description": "Not governed by Alabama",
            "filter": {"governing_law_state": {"$ne": "alabama"}},
            "expected_sql": "SELECT TOP 100 * FROM c WHERE c.governing_law_state != 'alabama'"
        },
        {
            "description": "MSA contracts not governed by Alabama",
            "filter": {
                "contract_type": "msa",
                "governing_law_state": {"$ne": "alabama"}
            },
            "should_contain": [
                "c.contract_type = 'msa'",
                "c.governing_law_state != 'alabama'",
                "AND"
            ]
        }
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\nTest: {test['description']}")

        # Build WHERE clause
        where_clauses = []
        for field, value in test['filter'].items():
            if isinstance(value, dict) and "$ne" in value:
                negated_value = value["$ne"]
                where_clauses.append(f"c.{field} != '{negated_value}'")
            else:
                where_clauses.append(f"c.{field} = '{value}'")

        where_clause = " AND ".join(where_clauses)
        sql = f"SELECT TOP 100 * FROM c WHERE {where_clause}"

        print(f"Generated SQL:\n  {sql}")

        # Check result
        if "expected_sql" in test:
            if sql == test["expected_sql"]:
                print("[PASS]")
                passed += 1
            else:
                print(f"[FAIL]")
                print(f"Expected:\n  {test['expected_sql']}")
                failed += 1
        elif "should_contain" in test:
            all_present = all(fragment in sql for fragment in test["should_contain"])
            if all_present:
                print("[PASS] All required fragments present")
                passed += 1
            else:
                missing = [f for f in test["should_contain"] if f not in sql]
                print(f"[FAIL] Missing fragments: {missing}")
                failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("\n" + "="*80)
    print("NEGATION SUPPORT TEST SUITE (STANDALONE)")
    print("="*80)

    all_passed = True
    all_passed &= test_negation_regex_patterns()
    all_passed &= test_filter_building()
    all_passed &= test_complete_sql_query()

    print("\n" + "="*80)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED")
    else:
        print("[FAILURE] SOME TESTS FAILED")
    print("="*80 + "\n")
