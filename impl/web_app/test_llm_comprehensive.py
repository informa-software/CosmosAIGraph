"""
Comprehensive LLM Query Planner Test Suite - Phase 2 Validation

Tests 50+ diverse queries covering:
- Simple entity queries
- Complex multi-entity queries
- Negations (single and multiple)
- OR/AND combinations
- Aggregations (simple and grouped)
- Graph traversal queries
- Vector search queries
- Hybrid queries (entity + content)
- Edge cases and corner cases

Generates detailed analysis report for Phase 2 decision-making.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

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


# Test Query Definitions
# Format: (id, query, expected_strategy, expected_type, category, notes)
TEST_QUERIES = [
    # Category 1: Simple Entity Queries (10 queries)
    (1, "Show me contracts with Acme Corp", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single contractor party lookup"),
    (2, "Find contracts governed by California law", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single governing law lookup"),
    (3, "Show me contracts with Microsoft", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single contractor party lookup"),
    (4, "Find contracts in Texas", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single governing law lookup"),
    (5, "Show me contracts from Google", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single contractor party lookup - alternate phrasing"),
    (6, "List contracts under New York law", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single governing law - alternate phrasing"),
    (7, "Find all IBM contracts", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single contractor party"),
    (8, "Show Florida contracts", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single governing law - short form"),
    (9, "Contracts with Oracle", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single contractor party - minimal phrasing"),
    (10, "Washington state contracts", "ENTITY_FIRST", "SQL", "simple_entity",
     "Single governing law - minimal phrasing"),

    # Category 2: Negation Queries (10 queries)
    (11, "Show contracts NOT governed by New York", "CONTRACT_DIRECT", "SQL", "negation",
     "Single negation - governing law"),
    (12, "Find contracts without California law", "CONTRACT_DIRECT", "SQL", "negation",
     "Single negation - alternate phrasing"),
    (13, "Contracts not from Microsoft", "CONTRACT_DIRECT", "SQL", "negation",
     "Single negation - contractor party"),
    (14, "Show me contracts excluding Texas", "CONTRACT_DIRECT", "SQL", "negation",
     "Single negation - governing law exclusion"),
    (15, "Find contracts NOT with Google", "CONTRACT_DIRECT", "SQL", "negation",
     "Single negation - contractor party"),
    (16, "Contracts not governed by Florida or California", "CONTRACT_DIRECT", "SQL", "negation",
     "Multiple negations with OR"),
    (17, "Show contracts excluding Microsoft and Google", "CONTRACT_DIRECT", "SQL", "negation",
     "Multiple negations with AND"),
    (18, "Find contracts NOT in New York, Texas, or California", "CONTRACT_DIRECT", "SQL", "negation",
     "Multiple state negations"),
    (19, "Contracts without Acme Corp or IBM", "CONTRACT_DIRECT", "SQL", "negation",
     "Multiple contractor negations"),
    (20, "Show contracts not governed by any of these: NY, CA, TX", "CONTRACT_DIRECT", "SQL", "negation",
     "List negation - alternate phrasing"),

    # Category 3: OR List Queries (10 queries)
    (21, "Find contracts with Microsoft OR Google OR Amazon", "CONTRACT_DIRECT", "SQL", "or_list",
     "Multiple contractors with OR - could be ENTITY_FIRST if same field"),
    (22, "Show contracts in California OR New York OR Texas", "ENTITY_FIRST", "SQL", "or_list",
     "Multiple states with OR - can use entity IN clause"),
    (23, "Contracts from IBM or Oracle", "ENTITY_FIRST", "SQL", "or_list",
     "Two contractors with OR"),
    (24, "Find contracts governed by Florida or Washington", "ENTITY_FIRST", "SQL", "or_list",
     "Two states with OR"),
    (25, "Show me Microsoft, Google, or Amazon contracts", "CONTRACT_DIRECT", "SQL", "or_list",
     "List format - multiple contractors"),
    (26, "Contracts in CA, NY, TX, or FL", "ENTITY_FIRST", "SQL", "or_list",
     "Abbreviated state list with OR"),
    (27, "Find contracts with any of these parties: Acme, Microsoft, IBM", "CONTRACT_DIRECT", "SQL", "or_list",
     "Explicit any-of phrasing"),
    (28, "Show contracts governed by either California or Texas", "ENTITY_FIRST", "SQL", "or_list",
     "Either/or phrasing"),
    (29, "Contracts from Microsoft or governed by California", "CONTRACT_DIRECT", "SQL", "or_list",
     "Mixed fields with OR - different entity types"),
    (30, "Find Acme or Google contracts in New York or Texas", "CONTRACT_DIRECT", "SQL", "or_list",
     "Multiple OR conditions across fields"),

    # Category 4: Aggregation Queries (10 queries)
    (31, "What is the total value of contracts in California?", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Single state total value - use pre-computed stats"),
    (32, "Show me the number of contracts per state", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Grouped count by state"),
    (33, "How many contracts does Microsoft have?", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Single contractor count"),
    (34, "What is the average contract value in Texas?", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Single state average - may need computation"),
    (35, "Count all contracts in New York", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Single state count"),
    (36, "Show total contract value by contractor", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Grouped sum by contractor"),
    (37, "How many contracts are there per governing law?", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Grouped count by state - alternate phrasing"),
    (38, "What is the total value of all Microsoft contracts?", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Single contractor total value"),
    (39, "Show me contract counts grouped by state", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Grouped count - explicit grouping"),
    (40, "Sum of contract values in California", "ENTITY_AGGREGATION", "SQL", "aggregation",
     "Single state sum - direct phrasing"),

    # Category 5: Graph Traversal Queries (10 queries)
    (41, "Show me all contractors who have contracts in California", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Multi-hop: state -> contracts -> contractors"),
    (42, "What types of contracts does Acme Corp have?", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Multi-hop: contractor -> contracts -> types"),
    (43, "Find all contractors working in Texas and their contract types", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Multi-hop: state -> contracts -> contractors + types"),
    (44, "Show relationships between Microsoft and California contracts", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Relationship query with multiple entities"),
    (45, "Find contracts between Acme Corp and any client in California", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "'Between' keyword triggers graph traversal"),
    (46, "What contractors have both MSA and SOW contracts?", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Multi-hop with multiple contract types"),
    (47, "Show me all contract types used in New York", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Multi-hop: state -> contracts -> types"),
    (48, "Find contractors connected to Google contracts", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "'Connected to' phrasing - relationship query"),
    (49, "Show the network of contracts involving Microsoft", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "'Network' keyword - relationship traversal"),
    (50, "What are the relationships between Acme Corp and Texas?", "GRAPH_TRAVERSAL", "SPARQL", "graph",
     "Explicit relationships query"),

    # Category 6: Vector Search Queries (10 queries)
    (51, "Find contracts about liability and indemnification", "VECTOR_SEARCH", "SQL", "vector",
     "Semantic topic search"),
    (52, "Show me contracts related to intellectual property", "VECTOR_SEARCH", "SQL", "vector",
     "Semantic concept search"),
    (53, "Find contracts with confidentiality clauses", "VECTOR_SEARCH", "SQL", "vector",
     "Content-based search"),
    (54, "Show contracts about data privacy", "VECTOR_SEARCH", "SQL", "vector",
     "Topic-based search"),
    (55, "Find contracts discussing termination conditions", "VECTOR_SEARCH", "SQL", "vector",
     "Semantic clause search"),
    (56, "Show me contracts related to payment terms", "VECTOR_SEARCH", "SQL", "vector",
     "Content search - payment clauses"),
    (57, "Find contracts with warranty provisions", "VECTOR_SEARCH", "SQL", "vector",
     "Semantic warranty search"),
    (58, "Show contracts about dispute resolution", "VECTOR_SEARCH", "SQL", "vector",
     "Topic search - legal clauses"),
    (59, "Find contracts with non-compete clauses", "VECTOR_SEARCH", "SQL", "vector",
     "Specific clause type search"),
    (60, "Show me contracts discussing force majeure", "VECTOR_SEARCH", "SQL", "vector",
     "Legal term semantic search"),

    # Category 7: Hybrid Queries - Entity + Clause Type (15 queries)
    (61, "Which contracts are governed by Alabama and contain an indemnification clause", "ENTITY_FIRST_OR_CONTRACT_DIRECT", "SQL", "hybrid",
     "Entity filter + clause type - uses contract_clauses collection (LLM chooses: ENTITY_FIRST→filter clauses OR CONTRACT_DIRECT with subquery)"),
    (62, "Find California contracts about liability", "VECTOR_SEARCH", "SQL", "hybrid",
     "Governing law + semantic content"),
    (63, "Show Microsoft contracts with confidentiality clauses", "VECTOR_SEARCH", "SQL", "hybrid",
     "Contractor + content search"),
    (64, "Find Texas contracts discussing payment terms", "VECTOR_SEARCH", "SQL", "hybrid",
     "Governing law + semantic clause"),
    (65, "Show Acme Corp contracts about intellectual property", "VECTOR_SEARCH", "SQL", "hybrid",
     "Contractor + semantic topic"),
    (66, "Find New York contracts with termination clauses", "VECTOR_SEARCH", "SQL", "hybrid",
     "Governing law + content"),
    (67, "Show Google contracts related to data privacy", "VECTOR_SEARCH", "SQL", "hybrid",
     "Contractor + semantic topic"),
    (68, "Find Florida contracts about warranty provisions", "VECTOR_SEARCH", "SQL", "hybrid",
     "Governing law + content search"),
    (69, "Show IBM contracts with non-compete clauses", "VECTOR_SEARCH", "SQL", "hybrid",
     "Contractor + specific clause"),
    (70, "Find contracts in California or Texas about liability", "VECTOR_SEARCH", "SQL", "hybrid",
     "OR list states + content search"),
    (71, "Show Microsoft or Google contracts with indemnification", "VECTOR_SEARCH", "SQL", "hybrid",
     "OR list contractors + content"),
    (72, "Find Alabama contracts NOT about liability", "CONTRACT_DIRECT", "SQL", "hybrid",
     "Entity + negated content - complex"),
    (73, "Show contracts with Acme Corp about payment but NOT in California", "VECTOR_SEARCH", "SQL", "hybrid",
     "Contractor + content + negated entity"),
    (74, "Find contracts in NY, CA, or TX about intellectual property", "VECTOR_SEARCH", "SQL", "hybrid",
     "OR list + semantic search"),
    (75, "Show high-value California contracts about liability", "VECTOR_SEARCH", "SQL", "hybrid",
     "Entity + numeric filter + content"),

    # Category 8: Edge Cases (10 queries)
    (76, "Show me Master Service Agreements", "ENTITY_FIRST", "SQL", "edge_case",
     "Contract type - could be entity or direct"),
    (77, "Find all NDA contracts", "ENTITY_FIRST", "SQL", "edge_case",
     "Contract type abbreviation"),
    (78, "Show contracts", "CONTRACT_DIRECT", "SQL", "edge_case",
     "Minimal query - no filters"),
    (79, "Find everything about Acme Corp", "GRAPH_TRAVERSAL", "SPARQL", "edge_case",
     "'Everything' keyword - comprehensive query"),
    (80, "Show me the most recent contracts", "CONTRACT_DIRECT", "SQL", "edge_case",
     "Temporal ordering - no entity filter"),
    (81, "Find high-value contracts", "CONTRACT_DIRECT", "SQL", "edge_case",
     "Numeric filter only - no entity"),
    (82, "Show contracts expiring soon", "CONTRACT_DIRECT", "SQL", "edge_case",
     "Temporal filter - date-based"),
    (83, "Find contracts with Acme Corp as client", "ENTITY_FIRST", "SQL", "edge_case",
     "Role specification - contracting party"),
    (84, "Show active contracts in California", "CONTRACT_DIRECT", "SQL", "edge_case",
     "Status filter + entity"),
    (85, "Find all contracts between $100k and $500k", "CONTRACT_DIRECT", "SQL", "edge_case",
     "Numeric range - no entity filter"),
]


class ComprehensiveTestSuite:
    """Comprehensive test suite for LLM query planner validation."""

    def __init__(self):
        self.llm_planner = LLMQueryPlanner()
        self.sql_validator = SQLValidator()
        self.sparql_validator = SPARQLValidator()
        self.results: List[Dict] = []
        self.category_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

    def test_query(self, query_id: int, natural_language: str, expected_strategy: str,
                   expected_query_type: str, category: str, notes: str = "") -> Dict:
        """Test a single query and validate results."""
        logger.info(f"\n{'='*80}")
        logger.info(f"Test Query #{query_id}: {natural_language}")
        logger.info(f"Category: {category} | Expected: {expected_strategy}/{expected_query_type}")
        logger.info(f"{'='*80}")

        result = {
            'query_id': query_id,
            'natural_language': natural_language,
            'expected_strategy': expected_strategy,
            'expected_query_type': expected_query_type,
            'category': category,
            'notes': notes,
            'success': False,
            'errors': []
        }

        try:
            # Generate LLM query plan
            llm_plan = self.llm_planner.plan_query(natural_language, timeout=15.0)

            result['llm_strategy'] = llm_plan.strategy
            result['llm_query_type'] = llm_plan.query_type
            result['llm_confidence'] = llm_plan.confidence
            result['llm_reasoning'] = llm_plan.reasoning
            result['llm_query_text'] = llm_plan.query_text

            logger.info(f"LLM: {llm_plan.strategy}/{llm_plan.query_type} (confidence: {llm_plan.confidence:.2f})")

            # Validate query syntax
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
                logger.info(f"[OK] Validation PASSED")
            else:
                logger.error(f"[FAIL] Validation FAILED: {validation_msg}")
                result['errors'].append(f"Validation failed: {validation_msg}")

            # Check strategy match (handle multiple acceptable strategies with OR)
            if "_OR_" in expected_strategy:
                acceptable_strategies = expected_strategy.split("_OR_")
                strategy_match = llm_plan.strategy in acceptable_strategies
            else:
                strategy_match = (llm_plan.strategy == expected_strategy)

            result['strategy_match'] = strategy_match

            if not strategy_match:
                logger.warning(f"[WARN] Strategy mismatch: expected {expected_strategy}, got {llm_plan.strategy}")
                result['errors'].append(f"Strategy mismatch")

            # Check query type match
            query_type_match = (llm_plan.query_type == expected_query_type)
            result['query_type_match'] = query_type_match

            if not query_type_match:
                logger.warning(f"[WARN] Query type mismatch: expected {expected_query_type}, got {llm_plan.query_type}")
                result['errors'].append(f"Query type mismatch")

            # Check confidence threshold
            confidence_ok = (llm_plan.confidence >= 0.5)
            result['confidence_ok'] = confidence_ok

            if not confidence_ok:
                logger.warning(f"[WARN] Low confidence: {llm_plan.confidence:.2f}")
                result['errors'].append(f"Low confidence: {llm_plan.confidence:.2f}")

            # Overall success
            result['success'] = (is_valid and strategy_match and query_type_match and confidence_ok)

            if result['success']:
                logger.info(f"[OK] TEST PASSED")
                self.category_stats[category]['passed'] += 1
            else:
                logger.warning(f"[WARN] TEST COMPLETED WITH WARNINGS")
                self.category_stats[category]['failed'] += 1

            self.category_stats[category]['total'] += 1

        except Exception as e:
            logger.error(f"[FAIL] TEST FAILED: {str(e)}")
            result['errors'].append(f"Exception: {str(e)}")
            result['exception'] = str(e)
            self.category_stats[category]['failed'] += 1
            self.category_stats[category]['total'] += 1

        self.results.append(result)
        return result

    def run_all_tests(self):
        """Run all test queries."""
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE LLM QUERY PLANNER TEST SUITE - PHASE 2 VALIDATION")
        logger.info(f"Total Queries: {len(TEST_QUERIES)}")
        logger.info("="*80)

        for query_data in TEST_QUERIES:
            query_id, natural_language, expected_strategy, expected_type, category, notes = query_data
            self.test_query(query_id, natural_language, expected_strategy, expected_type, category, notes)

    def generate_analysis_report(self) -> str:
        """Generate comprehensive analysis report."""
        lines = []

        lines.append("="*80)
        lines.append("COMPREHENSIVE TEST ANALYSIS REPORT - PHASE 2 VALIDATION")
        lines.append("="*80)
        lines.append("")

        # Overall Statistics
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        failed = total_tests - passed

        lines.append("OVERALL STATISTICS")
        lines.append("-"*80)
        lines.append(f"Total Tests: {total_tests}")
        lines.append(f"Passed: {passed} ({passed/total_tests*100:.1f}%)")
        lines.append(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
        lines.append("")

        # Category Breakdown
        lines.append("CATEGORY BREAKDOWN")
        lines.append("-"*80)
        for category, stats in sorted(self.category_stats.items()):
            total = stats['total']
            passed_cat = stats['passed']
            pass_rate = (passed_cat / total * 100) if total > 0 else 0
            lines.append(f"{category:20} | Total: {total:3} | Passed: {passed_cat:3} | Rate: {pass_rate:5.1f}%")
        lines.append("")

        # Strategy Distribution
        lines.append("STRATEGY DISTRIBUTION")
        lines.append("-"*80)
        strategy_counts = defaultdict(int)
        for r in self.results:
            strategy = r.get('llm_strategy', 'UNKNOWN')
            strategy_counts[strategy] += 1

        for strategy, count in sorted(strategy_counts.items()):
            pct = (count / total_tests * 100)
            lines.append(f"{strategy:25} | Count: {count:3} | {pct:5.1f}%")
        lines.append("")

        # Query Type Distribution
        lines.append("QUERY TYPE DISTRIBUTION")
        lines.append("-"*80)
        query_type_counts = defaultdict(int)
        for r in self.results:
            query_type = r.get('llm_query_type', 'UNKNOWN')
            query_type_counts[query_type] += 1

        for query_type, count in sorted(query_type_counts.items()):
            pct = (count / total_tests * 100)
            lines.append(f"{query_type:25} | Count: {count:3} | {pct:5.1f}%")
        lines.append("")

        # Validation Results
        lines.append("VALIDATION RESULTS")
        lines.append("-"*80)
        validation_passed = sum(1 for r in self.results if r.get('validation_passed', False))
        strategy_matches = sum(1 for r in self.results if r.get('strategy_match', False))
        query_type_matches = sum(1 for r in self.results if r.get('query_type_match', False))
        avg_confidence = sum(r.get('llm_confidence', 0) for r in self.results) / total_tests

        lines.append(f"Queries with valid syntax:  {validation_passed}/{total_tests} ({validation_passed/total_tests*100:.1f}%)")
        lines.append(f"Strategy matches:           {strategy_matches}/{total_tests} ({strategy_matches/total_tests*100:.1f}%)")
        lines.append(f"Query type matches:         {query_type_matches}/{total_tests} ({query_type_matches/total_tests*100:.1f}%)")
        lines.append(f"Average confidence:         {avg_confidence:.2f}")
        lines.append("")

        # Confidence Analysis
        lines.append("CONFIDENCE ANALYSIS")
        lines.append("-"*80)
        confidence_ranges = {
            "0.90-1.00 (Excellent)": (0.90, 1.00),
            "0.80-0.89 (Good)": (0.80, 0.89),
            "0.70-0.79 (Fair)": (0.70, 0.79),
            "0.50-0.69 (Low)": (0.50, 0.69),
            "0.00-0.49 (Poor)": (0.00, 0.49)
        }

        for range_label, (min_conf, max_conf) in confidence_ranges.items():
            count = sum(1 for r in self.results
                       if min_conf <= r.get('llm_confidence', 0) <= max_conf)
            pct = (count / total_tests * 100)
            lines.append(f"{range_label:25} | Count: {count:3} | {pct:5.1f}%")
        lines.append("")

        # Strategy Mismatch Analysis
        mismatches = [r for r in self.results if not r.get('strategy_match', False)]
        if mismatches:
            lines.append("STRATEGY MISMATCH ANALYSIS")
            lines.append("-"*80)
            lines.append(f"Total Mismatches: {len(mismatches)} ({len(mismatches)/total_tests*100:.1f}%)")
            lines.append("")

            # Group by expected -> actual
            mismatch_patterns = defaultdict(list)
            for r in mismatches:
                pattern = f"{r['expected_strategy']} -> {r['llm_strategy']}"
                mismatch_patterns[pattern].append(r)

            for pattern, queries in sorted(mismatch_patterns.items()):
                lines.append(f"  {pattern}: {len(queries)} queries")
                for r in queries[:3]:  # Show first 3 examples
                    lines.append(f"    - Q{r['query_id']}: {r['natural_language'][:60]}...")
                if len(queries) > 3:
                    lines.append(f"    ... and {len(queries)-3} more")
            lines.append("")

        # Phase 2 Decision Criteria
        lines.append("PHASE 2 DECISION CRITERIA")
        lines.append("-"*80)

        criteria_met = []
        criteria_failed = []

        # Criterion 1: Strategy match rate >= 70%
        strategy_match_rate = (strategy_matches / total_tests * 100)
        if strategy_match_rate >= 70:
            criteria_met.append(f"[OK] Strategy match rate: {strategy_match_rate:.1f}% >= 70%")
        else:
            criteria_failed.append(f"[FAIL] Strategy match rate: {strategy_match_rate:.1f}% < 70%")

        # Criterion 2: Query validation rate = 100%
        validation_rate = (validation_passed / total_tests * 100)
        if validation_rate == 100:
            criteria_met.append(f"[OK] Query validation rate: {validation_rate:.1f}% = 100%")
        else:
            criteria_failed.append(f"[FAIL] Query validation rate: {validation_rate:.1f}% < 100%")

        # Criterion 3: Average confidence >= 0.8
        if avg_confidence >= 0.8:
            criteria_met.append(f"[OK] Average confidence: {avg_confidence:.2f} >= 0.80")
        else:
            criteria_failed.append(f"[FAIL] Average confidence: {avg_confidence:.2f} < 0.80")

        # Criterion 4: Confidence for matches >= 0.8
        matches_with_confidence = [r for r in self.results if r.get('strategy_match', False)]
        if matches_with_confidence:
            avg_match_confidence = sum(r.get('llm_confidence', 0) for r in matches_with_confidence) / len(matches_with_confidence)
            if avg_match_confidence >= 0.8:
                criteria_met.append(f"[OK] Confidence for matches: {avg_match_confidence:.2f} >= 0.80")
            else:
                criteria_failed.append(f"[FAIL] Confidence for matches: {avg_match_confidence:.2f} < 0.80")

        for criterion in criteria_met:
            lines.append(criterion)
        for criterion in criteria_failed:
            lines.append(criterion)
        lines.append("")

        # Recommendation
        lines.append("RECOMMENDATION")
        lines.append("-"*80)
        if len(criteria_failed) == 0:
            lines.append("[OK] ALL CRITERIA MET - Ready to proceed to Phase 3 (LLM Execution)")
            lines.append("")
            lines.append("Next Steps:")
            lines.append("1. Review strategy mismatches to ensure LLM reasoning is sound")
            lines.append("2. Implement Phase 3: Switch from logging to LLM execution")
            lines.append("3. Add fallback logic (if LLM fails, use rule-based)")
            lines.append("4. Deploy with gradual rollout (A/B testing)")
        elif len(criteria_failed) == 1 and "Strategy match rate" in criteria_failed[0]:
            lines.append("[WARN] PARTIAL PASS - Strategy match rate below 70%, but other criteria met")
            lines.append("")
            lines.append("Action Required:")
            lines.append("1. Manual review of strategy mismatches")
            lines.append("2. Validate that LLM strategies are reasonable (may be better than rule-based)")
            lines.append("3. If LLM reasoning is sound, proceed to Phase 3 with close monitoring")
            lines.append("4. Consider refining schema/ontology if mismatches are problematic")
        else:
            lines.append("[FAIL] CRITERIA NOT MET - More validation needed before Phase 3")
            lines.append("")
            lines.append("Action Required:")
            for criterion in criteria_failed:
                lines.append(f"  - Address: {criterion}")
            lines.append("")
            lines.append("Recommended Actions:")
            if validation_rate < 100:
                lines.append("  1. Fix query validation issues (syntax errors, injection risks)")
            if avg_confidence < 0.8:
                lines.append("  2. Improve schema descriptions or add examples for low-confidence queries")
            lines.append("  3. Collect more real-world data in production comparison mode")
            lines.append("  4. Re-run comprehensive tests after improvements")

        lines.append("")
        return "\n".join(lines)

    def save_results(self):
        """Save results to JSON file."""
        output_file = web_app_dir / "test_results_comprehensive.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\nDetailed results saved to: {output_file}")

    def print_report(self):
        """Print analysis report."""
        report = self.generate_analysis_report()
        print("\n" + report)

        # Save report to file
        report_file = web_app_dir / "test_report_comprehensive.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Analysis report saved to: {report_file}")


def main():
    """Main test execution."""
    # Check environment variable
    use_llm = os.environ.get('CAIG_USE_LLM_STRATEGY', 'false').lower()
    if use_llm != 'true':
        logger.warning("WARNING: CAIG_USE_LLM_STRATEGY is not set to 'true'")
        logger.warning("Continuing anyway for testing purposes...")

    # Run comprehensive tests
    suite = ComprehensiveTestSuite()
    suite.run_all_tests()
    suite.save_results()
    suite.print_report()


if __name__ == "__main__":
    main()
