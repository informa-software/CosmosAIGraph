"""
Test LLM Query Planner - Phase 1 Validation

Tests the complete LLM query planning pipeline with 10 diverse queries:
1. Single entity queries
2. Negation queries
3. OR list queries
4. Aggregation queries
5. Graph traversal queries
6. Complex multi-entity queries

Validates:
- LLM generates valid query plans
- SQL/SPARQL validation works
- Query syntax is correct
- Strategy selection is reasonable
- Confidence scores are appropriate
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List

# Add src to path
web_app_dir = Path(__file__).parent
sys.path.insert(0, str(web_app_dir))

from src.services.llm_query_planner import LLMQueryPlanner, LLMQueryPlan
from src.services.sql_validator import SQLValidator
from src.services.sparql_validator import SPARQLValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMQueryPlannerTester:
    """Test harness for LLM Query Planner validation."""

    def __init__(self):
        self.llm_planner = LLMQueryPlanner()
        self.sql_validator = SQLValidator()
        self.sparql_validator = SPARQLValidator()
        self.results: List[Dict] = []

    def test_query(self, query_id: int, natural_language: str, expected_strategy: str,
                   expected_query_type: str, notes: str = "") -> Dict:
        """Test a single query and validate results."""
        logger.info(f"\n{'='*80}")
        logger.info(f"Test Query #{query_id}: {natural_language}")
        logger.info(f"Expected: strategy={expected_strategy}, query_type={expected_query_type}")
        logger.info(f"Notes: {notes}")
        logger.info(f"{'='*80}")

        result = {
            'query_id': query_id,
            'natural_language': natural_language,
            'expected_strategy': expected_strategy,
            'expected_query_type': expected_query_type,
            'notes': notes,
            'success': False,
            'errors': []
        }

        try:
            # Step 1: Generate LLM query plan
            logger.info("\n[STEP 1] Generating LLM query plan...")
            llm_plan = self.llm_planner.plan_query(natural_language, timeout=15.0)

            result['llm_strategy'] = llm_plan.strategy
            result['llm_query_type'] = llm_plan.query_type
            result['llm_confidence'] = llm_plan.confidence
            result['llm_reasoning'] = llm_plan.reasoning
            result['llm_query_text'] = llm_plan.query_text

            logger.info(f"LLM Strategy: {llm_plan.strategy}")
            logger.info(f"Query Type: {llm_plan.query_type}")
            logger.info(f"Confidence: {llm_plan.confidence:.2f}")
            logger.info(f"Reasoning: {llm_plan.reasoning}")

            # Step 2: Validate query syntax
            logger.info("\n[STEP 2] Validating query syntax...")
            if llm_plan.query_type == "SQL":
                is_valid, validation_msg = self.sql_validator.validate(llm_plan.query_text)
            elif llm_plan.query_type == "SPARQL":
                is_valid, validation_msg = self.sparql_validator.validate(llm_plan.query_text)
            else:
                is_valid = False
                validation_msg = f"Unknown query type: {llm_plan.query_type}"

            result['validation_passed'] = is_valid
            result['validation_message'] = validation_msg

            if is_valid:
                logger.info(f"✅ Validation PASSED: {validation_msg}")
            else:
                logger.error(f"❌ Validation FAILED: {validation_msg}")
                result['errors'].append(f"Validation failed: {validation_msg}")

            # Step 3: Display generated query
            logger.info(f"\n[STEP 3] Generated {llm_plan.query_type} Query:")
            logger.info("-" * 80)
            logger.info(llm_plan.query_text)
            logger.info("-" * 80)

            # Step 4: Check strategy match
            logger.info("\n[STEP 4] Strategy validation...")
            strategy_match = (llm_plan.strategy == expected_strategy)
            result['strategy_match'] = strategy_match

            if strategy_match:
                logger.info(f"✅ Strategy MATCH: {llm_plan.strategy}")
            else:
                logger.warning(f"⚠️  Strategy MISMATCH: Expected {expected_strategy}, got {llm_plan.strategy}")
                result['errors'].append(f"Strategy mismatch: expected {expected_strategy}, got {llm_plan.strategy}")

            # Step 5: Check query type match
            logger.info("\n[STEP 5] Query type validation...")
            query_type_match = (llm_plan.query_type == expected_query_type)
            result['query_type_match'] = query_type_match

            if query_type_match:
                logger.info(f"✅ Query type MATCH: {llm_plan.query_type}")
            else:
                logger.warning(f"⚠️  Query type MISMATCH: Expected {expected_query_type}, got {llm_plan.query_type}")
                result['errors'].append(f"Query type mismatch: expected {expected_query_type}, got {llm_plan.query_type}")

            # Step 6: Check confidence threshold
            logger.info("\n[STEP 6] Confidence validation...")
            confidence_ok = (llm_plan.confidence >= 0.5)
            result['confidence_ok'] = confidence_ok

            if confidence_ok:
                logger.info(f"✅ Confidence OK: {llm_plan.confidence:.2f} >= 0.5")
            else:
                logger.warning(f"⚠️  Confidence LOW: {llm_plan.confidence:.2f} < 0.5")
                result['errors'].append(f"Low confidence: {llm_plan.confidence:.2f}")

            # Overall success
            result['success'] = (is_valid and strategy_match and query_type_match and confidence_ok)

            if result['success']:
                logger.info(f"\n✅ TEST PASSED - Query #{query_id}")
            else:
                logger.warning(f"\n⚠️  TEST COMPLETED WITH WARNINGS - Query #{query_id}")
                logger.warning(f"Errors: {result['errors']}")

        except Exception as e:
            logger.error(f"\n❌ TEST FAILED - Query #{query_id}: {str(e)}")
            result['errors'].append(f"Exception: {str(e)}")
            result['exception'] = str(e)

        self.results.append(result)
        return result

    def run_all_tests(self):
        """Run all 10 test queries."""
        logger.info("\n" + "="*80)
        logger.info("STARTING LLM QUERY PLANNER PHASE 1 VALIDATION")
        logger.info("="*80)

        # Test 1: Simple single entity query (contractor party)
        self.test_query(
            query_id=1,
            natural_language="Show me contracts with Acme Corp",
            expected_strategy="ENTITY_FIRST",
            expected_query_type="SQL",
            notes="Simple contractor party lookup - should use entity collection first"
        )

        # Test 2: Single entity query (governing law)
        self.test_query(
            query_id=2,
            natural_language="Find contracts governed by California law",
            expected_strategy="ENTITY_FIRST",
            expected_query_type="SQL",
            notes="Governing law entity lookup"
        )

        # Test 3: Negation query
        self.test_query(
            query_id=3,
            natural_language="Show contracts NOT governed by New York",
            expected_strategy="CONTRACT_DIRECT",
            expected_query_type="SQL",
            notes="Negation requires direct contract query, cannot use entity collection"
        )

        # Test 4: OR list query
        self.test_query(
            query_id=4,
            natural_language="Find contracts with Microsoft OR Google OR Amazon",
            expected_strategy="ENTITY_FIRST",
            expected_query_type="SQL",
            notes="Multiple entities with OR - can use entity collection with IN clause"
        )

        # Test 5: Aggregation query
        self.test_query(
            query_id=5,
            natural_language="What is the total value of contracts in California?",
            expected_strategy="ENTITY_AGGREGATION",
            expected_query_type="SQL",
            notes="Aggregation query - should use pre-computed stats from entity collection"
        )

        # Test 6: Contract field query (non-entity)
        self.test_query(
            query_id=6,
            natural_language="Show me Master Service Agreements",
            expected_strategy="CONTRACT_DIRECT",
            expected_query_type="SQL",
            notes="Contract type query - direct contract lookup"
        )

        # Test 7: Graph traversal query
        self.test_query(
            query_id=7,
            natural_language="Show me all contractors who have contracts in California and what types of contracts they have",
            expected_strategy="GRAPH_TRAVERSAL",
            expected_query_type="SPARQL",
            notes="Multi-hop relationship query requiring graph traversal"
        )

        # Test 8: Multi-entity complex query
        self.test_query(
            query_id=8,
            natural_language="Find contracts between Acme Corp and any client in California",
            expected_strategy="ENTITY_FIRST",
            expected_query_type="SQL",
            notes="Multiple entity filters - contractor + governing law"
        )

        # Test 9: Semantic/content search
        self.test_query(
            query_id=9,
            natural_language="Find contracts about liability and indemnification",
            expected_strategy="VECTOR_SEARCH",
            expected_query_type="SQL",
            notes="Content-based semantic search - requires vector embeddings"
        )

        # Test 10: Complex aggregation with grouping
        self.test_query(
            query_id=10,
            natural_language="Show me the number of contracts per state",
            expected_strategy="ENTITY_AGGREGATION",
            expected_query_type="SQL",
            notes="Grouped aggregation - use entity collection stats"
        )

    def print_summary(self):
        """Print test summary report."""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY REPORT")
        logger.info("="*80)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total_tests - passed

        logger.info(f"\nTotal Tests: {total_tests}")
        logger.info(f"Passed: {passed} ({passed/total_tests*100:.1f}%)")
        logger.info(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")

        # Strategy distribution
        logger.info("\n" + "-"*80)
        logger.info("STRATEGY DISTRIBUTION")
        logger.info("-"*80)

        strategy_counts = {}
        for r in self.results:
            strategy = r.get('llm_strategy', 'UNKNOWN')
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        for strategy, count in sorted(strategy_counts.items()):
            logger.info(f"{strategy}: {count} queries")

        # Query type distribution
        logger.info("\n" + "-"*80)
        logger.info("QUERY TYPE DISTRIBUTION")
        logger.info("-"*80)

        query_type_counts = {}
        for r in self.results:
            query_type = r.get('llm_query_type', 'UNKNOWN')
            query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1

        for query_type, count in sorted(query_type_counts.items()):
            logger.info(f"{query_type}: {count} queries")

        # Validation results
        logger.info("\n" + "-"*80)
        logger.info("VALIDATION RESULTS")
        logger.info("-"*80)

        validation_passed = sum(1 for r in self.results if r.get('validation_passed', False))
        logger.info(f"Queries with valid syntax: {validation_passed}/{total_tests} ({validation_passed/total_tests*100:.1f}%)")

        strategy_matches = sum(1 for r in self.results if r.get('strategy_match', False))
        logger.info(f"Strategy matches: {strategy_matches}/{total_tests} ({strategy_matches/total_tests*100:.1f}%)")

        query_type_matches = sum(1 for r in self.results if r.get('query_type_match', False))
        logger.info(f"Query type matches: {query_type_matches}/{total_tests} ({query_type_matches/total_tests*100:.1f}%)")

        # Average confidence
        avg_confidence = sum(r.get('llm_confidence', 0) for r in self.results) / total_tests
        logger.info(f"Average confidence: {avg_confidence:.2f}")

        # Failed tests details
        if failed > 0:
            logger.info("\n" + "-"*80)
            logger.info("FAILED TESTS DETAILS")
            logger.info("-"*80)

            for r in self.results:
                if not r['success']:
                    logger.info(f"\nQuery #{r['query_id']}: {r['natural_language']}")
                    logger.info(f"Errors: {r['errors']}")
                    if 'exception' in r:
                        logger.info(f"Exception: {r['exception']}")

        # Save results to JSON
        output_file = web_app_dir / "test_results_phase1.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\nDetailed results saved to: {output_file}")


def main():
    """Main test execution."""
    # Check environment variable
    use_llm = os.environ.get('CAIG_USE_LLM_STRATEGY', 'false').lower()
    if use_llm != 'true':
        logger.warning("WARNING: CAIG_USE_LLM_STRATEGY is not set to 'true'")
        logger.warning("Set environment variable: CAIG_USE_LLM_STRATEGY=true")
        logger.warning("Continuing anyway for testing purposes...")

    # Run tests
    tester = LLMQueryPlannerTester()
    tester.run_all_tests()
    tester.print_summary()


if __name__ == "__main__":
    main()
