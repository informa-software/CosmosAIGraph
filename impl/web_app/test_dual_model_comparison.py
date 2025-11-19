"""
Test script for Dual-Model Comparison (GPT-4.1 vs GPT-4.1-mini).

This script compares the performance and quality of two LLM models
side-by-side on the same clause comparison tasks.
"""

import asyncio
import sys
import os
import time
import json
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
from src.services.clause_library_service import ClauseLibraryService
from src.services.config_service import ConfigService
from src.models.clause_library_models import CompareClauseRequest
from sample_clause_data import get_sample_clauses, get_test_cases
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class DualModelTester:
    """Test harness for comparing two LLM models side-by-side."""

    def __init__(self):
        self.cosmos = CosmosNoSQLService()
        self.ai = AiService()
        self.clause_service = ClauseLibraryService(self.cosmos, self.ai)
        self.test_results = {
            "test_date": datetime.utcnow().isoformat(),
            "primary_model": None,
            "secondary_model": None,
            "comparisons": [],
            "summary": {}
        }

    async def cleanup(self):
        """Clean up resources and close connections."""
        print("\nCleaning up resources...")

        # Close CosmosDB client
        if hasattr(self.cosmos, '_client') and self.cosmos._client:
            try:
                await self.cosmos._client.close()
                print("  CosmosDB client closed")
            except Exception as e:
                print(f"  Warning: CosmosDB client close error: {e}")

        # Close any aiohttp sessions in AI service
        if hasattr(self.ai, 'session') and self.ai.session:
            try:
                await self.ai.session.close()
                print("  AI service session closed")
            except Exception as e:
                print(f"  Warning: AI service session close error: {e}")

        print("Cleanup complete")

    async def initialize(self):
        """Initialize services."""
        print("Initializing services...")

        # Initialize CosmosDB client
        await self.cosmos.initialize()
        print("  CosmosDB client initialized")

        # Set database
        self.cosmos.set_db(ConfigService.graph_source_db())
        print("  CosmosDB database connected")

        # Initialize clause library service
        await self.clause_service.initialize()
        print("  Clause library service initialized")

        # Check if secondary model is configured
        if not self.ai.aoai_client_secondary:
            print("\n  WARNING: Secondary model not configured!")
            print("  Please configure CAIG_AZURE_OPENAI_URL_SECONDARY, ")
            print("  CAIG_AZURE_OPENAI_KEY_SECONDARY, and ")
            print("  CAIG_AZURE_OPENAI_COMPLETIONS_DEP_SECONDARY in .env")
            return False

        # Store model names
        self.test_results["primary_model"] = self.ai.completions_deployment
        self.test_results["secondary_model"] = self.ai.completions_deployment_secondary

        print(f"  Primary model: {self.test_results['primary_model']}")
        print(f"  Secondary model: {self.test_results['secondary_model']}")
        print("\nServices initialized successfully")
        return True

    async def create_test_clause(self) -> str:
        """Create a test clause for comparison."""
        print("\n" + "="*80)
        print("CREATING TEST CLAUSE")
        print("="*80)

        from src.models.clause_library_models import CreateClauseRequest

        # Use the indemnification clause from sample data
        sample_clauses = get_sample_clauses()
        clause_data = sample_clauses[0]  # Indemnification clause

        print(f"\nCreating clause: {clause_data['name']}")

        request = CreateClauseRequest(**clause_data)
        clause = await self.clause_service.create_clause(
            request=request,
            user_email="test@example.com"
        )

        print(f"  Created clause ID: {clause.id}")
        print(f"  Category: {clause.category_path_display}")

        return clause.id

    async def run_comparison_with_model(
        self,
        clause_id: str,
        contract_text: str,
        model_selection: str
    ) -> Dict[str, Any]:
        """Run a comparison with a specific model."""
        request = CompareClauseRequest(
            clause_id=clause_id,
            contract_text=contract_text,
            contract_id=f"test_contract_{model_selection}"
        )

        start_time = time.time()
        comparison = await self.clause_service.compare_clause(
            request=request,
            user_email="test@example.com",
            use_cache=False,  # Don't use cache to ensure fresh comparison
            model_selection=model_selection
        )
        elapsed_time = time.time() - start_time

        return {
            "model": comparison.ai_analysis.model,
            "elapsed_time": elapsed_time,
            "tokens": comparison.ai_analysis.completion_tokens,
            "similarity_score": comparison.comparison.similarity_score,
            "risk_level": comparison.risk_analysis.overall_risk,
            "risk_count": len(comparison.risk_analysis.risks),
            "recommendation_count": len(comparison.recommendations),
            "comparison_result": comparison
        }

    def _write_comparison_details(
        self,
        test_case_num: int,
        test_case: Dict[str, Any],
        primary_result: Dict[str, Any],
        secondary_result: Dict[str, Any]
    ):
        """Write detailed comparison results to files."""
        # Create output directory
        output_dir = "dual_model_comparison_details"
        os.makedirs(output_dir, exist_ok=True)

        # Create a subdirectory for this test case
        test_dir = os.path.join(output_dir, f"test_{test_case_num:02d}_{test_case['description'].replace(' ', '_')[:30]}")
        os.makedirs(test_dir, exist_ok=True)

        # Write primary model details
        primary_file = os.path.join(test_dir, "primary_model_response.txt")
        with open(primary_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"PRIMARY MODEL ANALYSIS: {primary_result['model']}\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Case: {test_case['description']}\n")
            f.write(f"Expected Similarity: {test_case['expected_similarity']}\n")
            f.write(f"Processing Time: {primary_result['elapsed_time']:.3f}s\n")
            f.write(f"Tokens Used: {primary_result['tokens']}\n\n")

            f.write("-"*80 + "\n")
            f.write("CONTRACT TEXT ANALYZED\n")
            f.write("-"*80 + "\n")
            f.write(test_case['contract_text'] + "\n\n")

            comparison = primary_result['comparison_result']

            f.write("-"*80 + "\n")
            f.write("SIMILARITY ANALYSIS\n")
            f.write("-"*80 + "\n")
            f.write(f"Score: {comparison.comparison.similarity_score:.3f}\n\n")

            f.write("-"*80 + "\n")
            f.write("DIFFERENCES IDENTIFIED\n")
            f.write("-"*80 + "\n")
            if comparison.comparison.differences:
                for i, diff in enumerate(comparison.comparison.differences, 1):
                    f.write(f"\n{i}. {diff.type.upper()} - {diff.severity}\n")
                    f.write(f"   Location: {diff.location}\n")
                    if diff.library_text:
                        f.write(f"   Library: {diff.library_text}\n")
                    if diff.contract_text:
                        f.write(f"   Contract: {diff.contract_text}\n")
            else:
                f.write("No significant differences identified.\n")
            f.write("\n")

            f.write("-"*80 + "\n")
            f.write("RISK ANALYSIS\n")
            f.write("-"*80 + "\n")
            f.write(f"Overall Risk: {comparison.risk_analysis.overall_risk}\n")
            f.write(f"Risk Score: {comparison.risk_analysis.risk_score:.2f}\n\n")

            if comparison.risk_analysis.risks:
                f.write("Identified Risks:\n")
                for i, risk in enumerate(comparison.risk_analysis.risks, 1):
                    f.write(f"\n{i}. {risk.category.upper()} - {risk.severity}\n")
                    f.write(f"   Description: {risk.description}\n")
                    f.write(f"   Impact: {risk.impact}\n")
                    if risk.location:
                        f.write(f"   Location: {risk.location}\n")
            else:
                f.write("No risks identified.\n")
            f.write("\n")

            f.write("-"*80 + "\n")
            f.write("RECOMMENDATIONS\n")
            f.write("-"*80 + "\n")
            if comparison.recommendations:
                for i, rec in enumerate(comparison.recommendations, 1):
                    f.write(f"\n{i}. {rec.type.upper()} - Priority: {rec.priority}\n")
                    f.write(f"   {rec.description}\n")
                    if rec.suggested_text:
                        f.write(f"   Suggested Text:\n   {rec.suggested_text}\n")
                    if rec.rationale:
                        f.write(f"   Rationale: {rec.rationale}\n")
            else:
                f.write("No recommendations.\n")

        # Write secondary model details
        secondary_file = os.path.join(test_dir, "secondary_model_response.txt")
        with open(secondary_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"SECONDARY MODEL ANALYSIS: {secondary_result['model']}\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Case: {test_case['description']}\n")
            f.write(f"Expected Similarity: {test_case['expected_similarity']}\n")
            f.write(f"Processing Time: {secondary_result['elapsed_time']:.3f}s\n")
            f.write(f"Tokens Used: {secondary_result['tokens']}\n\n")

            f.write("-"*80 + "\n")
            f.write("CONTRACT TEXT ANALYZED\n")
            f.write("-"*80 + "\n")
            f.write(test_case['contract_text'] + "\n\n")

            comparison = secondary_result['comparison_result']

            f.write("-"*80 + "\n")
            f.write("SIMILARITY ANALYSIS\n")
            f.write("-"*80 + "\n")
            f.write(f"Score: {comparison.comparison.similarity_score:.3f}\n\n")

            f.write("-"*80 + "\n")
            f.write("DIFFERENCES IDENTIFIED\n")
            f.write("-"*80 + "\n")
            if comparison.comparison.differences:
                for i, diff in enumerate(comparison.comparison.differences, 1):
                    f.write(f"\n{i}. {diff.type.upper()} - {diff.severity}\n")
                    f.write(f"   Location: {diff.location}\n")
                    if diff.library_text:
                        f.write(f"   Library: {diff.library_text}\n")
                    if diff.contract_text:
                        f.write(f"   Contract: {diff.contract_text}\n")
            else:
                f.write("No significant differences identified.\n")
            f.write("\n")

            f.write("-"*80 + "\n")
            f.write("RISK ANALYSIS\n")
            f.write("-"*80 + "\n")
            f.write(f"Overall Risk: {comparison.risk_analysis.overall_risk}\n")
            f.write(f"Risk Score: {comparison.risk_analysis.risk_score:.2f}\n\n")

            if comparison.risk_analysis.risks:
                f.write("Identified Risks:\n")
                for i, risk in enumerate(comparison.risk_analysis.risks, 1):
                    f.write(f"\n{i}. {risk.category.upper()} - {risk.severity}\n")
                    f.write(f"   Description: {risk.description}\n")
                    f.write(f"   Impact: {risk.impact}\n")
                    if risk.location:
                        f.write(f"   Location: {risk.location}\n")
            else:
                f.write("No risks identified.\n")
            f.write("\n")

            f.write("-"*80 + "\n")
            f.write("RECOMMENDATIONS\n")
            f.write("-"*80 + "\n")
            if comparison.recommendations:
                for i, rec in enumerate(comparison.recommendations, 1):
                    f.write(f"\n{i}. {rec.type.upper()} - Priority: {rec.priority}\n")
                    f.write(f"   {rec.description}\n")
                    if rec.suggested_text:
                        f.write(f"   Suggested Text:\n   {rec.suggested_text}\n")
                    if rec.rationale:
                        f.write(f"   Rationale: {rec.rationale}\n")
            else:
                f.write("No recommendations.\n")

        # Write side-by-side comparison summary
        comparison_file = os.path.join(test_dir, "side_by_side_comparison.txt")
        with open(comparison_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("SIDE-BY-SIDE MODEL COMPARISON\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Case: {test_case['description']}\n")
            f.write(f"Expected: {test_case['expected_similarity']}\n\n")

            f.write("-"*80 + "\n")
            f.write("PERFORMANCE METRICS\n")
            f.write("-"*80 + "\n")
            f.write(f"{'Metric':<30} {'Primary':<25} {'Secondary':<25}\n")
            f.write("-"*80 + "\n")
            f.write(f"{'Model':<30} {primary_result['model']:<25} {secondary_result['model']:<25}\n")
            f.write(f"{'Time':<30} {primary_result['elapsed_time']:.3f}s{'':<20} {secondary_result['elapsed_time']:.3f}s\n")
            f.write(f"{'Tokens':<30} {primary_result['tokens']:<25} {secondary_result['tokens']:<25}\n")
            f.write(f"{'Similarity Score':<30} {primary_result['similarity_score']:.3f}{'':<21} {secondary_result['similarity_score']:.3f}\n")
            f.write(f"{'Risk Level':<30} {primary_result['risk_level']:<25} {secondary_result['risk_level']:<25}\n")
            f.write(f"{'Risk Count':<30} {primary_result['risk_count']:<25} {secondary_result['risk_count']:<25}\n")
            f.write(f"{'Recommendations':<30} {primary_result['recommendation_count']:<25} {secondary_result['recommendation_count']:<25}\n\n")

            time_diff = primary_result['elapsed_time'] - secondary_result['elapsed_time']
            time_pct = (time_diff / primary_result['elapsed_time']) * 100
            token_diff = primary_result['tokens'] - secondary_result['tokens']
            token_pct = (token_diff / primary_result['tokens']) * 100 if primary_result['tokens'] > 0 else 0
            similarity_diff = abs(primary_result['similarity_score'] - secondary_result['similarity_score'])

            f.write("-"*80 + "\n")
            f.write("DIFFERENCES\n")
            f.write("-"*80 + "\n")
            f.write(f"Time: {time_diff:+.3f}s ({time_pct:+.1f}%)\n")
            f.write(f"Tokens: {token_diff:+d} ({token_pct:+.1f}%)\n")
            f.write(f"Similarity: {similarity_diff:.3f}\n")
            f.write(f"\nFaster: {secondary_result['model'] if time_diff > 0 else primary_result['model']}\n")
            f.write(f"More Efficient: {secondary_result['model'] if token_diff > 0 else primary_result['model']}\n")

        print(f"  Detailed results written to: {test_dir}/")

    async def compare_models_on_test_case(
        self,
        test_case_num: int,
        clause_id: str,
        test_case: Dict[str, Any]
    ):
        """Run both models on the same test case and compare results."""
        print(f"\n[Test {test_case_num}] {test_case['description']}")
        print(f"  Expected similarity: {test_case['expected_similarity']}")
        print(f"  Contract text preview: {test_case['contract_text'][:80]}...")

        # Run with primary model
        print("\n  Running with PRIMARY model...")
        primary_result = await self.run_comparison_with_model(
            clause_id=clause_id,
            contract_text=test_case['contract_text'],
            model_selection="primary"
        )
        print(f"    Model: {primary_result['model']}")
        print(f"    Time: {primary_result['elapsed_time']:.3f}s")
        print(f"    Tokens: {primary_result['tokens']}")
        print(f"    Similarity: {primary_result['similarity_score']:.3f}")
        print(f"    Risk Level: {primary_result['risk_level']}")

        # Run with secondary model
        print("\n  Running with SECONDARY model...")
        secondary_result = await self.run_comparison_with_model(
            clause_id=clause_id,
            contract_text=test_case['contract_text'],
            model_selection="secondary"
        )
        print(f"    Model: {secondary_result['model']}")
        print(f"    Time: {secondary_result['elapsed_time']:.3f}s")
        print(f"    Tokens: {secondary_result['tokens']}")
        print(f"    Similarity: {secondary_result['similarity_score']:.3f}")
        print(f"    Risk Level: {secondary_result['risk_level']}")

        # Write detailed results to files
        self._write_comparison_details(
            test_case_num=test_case_num,
            test_case=test_case,
            primary_result=primary_result,
            secondary_result=secondary_result
        )

        # Calculate differences
        time_diff = primary_result['elapsed_time'] - secondary_result['elapsed_time']
        time_pct = (time_diff / primary_result['elapsed_time']) * 100
        token_diff = primary_result['tokens'] - secondary_result['tokens']
        token_pct = (token_diff / primary_result['tokens']) * 100 if primary_result['tokens'] > 0 else 0
        similarity_diff = abs(primary_result['similarity_score'] - secondary_result['similarity_score'])

        print("\n  COMPARISON:")
        print(f"    Time difference: {time_diff:+.3f}s ({time_pct:+.1f}%)")
        print(f"    Token difference: {token_diff:+d} ({token_pct:+.1f}%)")
        print(f"    Similarity difference: {similarity_diff:.3f}")

        # Store results
        comparison_result = {
            "test_case": test_case["description"],
            "expected_similarity": test_case["expected_similarity"],
            "primary": {
                "model": primary_result["model"],
                "elapsed_time": primary_result["elapsed_time"],
                "tokens": primary_result["tokens"],
                "similarity_score": primary_result["similarity_score"],
                "risk_level": primary_result["risk_level"],
                "risk_count": primary_result["risk_count"],
                "recommendation_count": primary_result["recommendation_count"]
            },
            "secondary": {
                "model": secondary_result["model"],
                "elapsed_time": secondary_result["elapsed_time"],
                "tokens": secondary_result["tokens"],
                "similarity_score": secondary_result["similarity_score"],
                "risk_level": secondary_result["risk_level"],
                "risk_count": secondary_result["risk_count"],
                "recommendation_count": secondary_result["recommendation_count"]
            },
            "differences": {
                "time_diff": time_diff,
                "time_pct": time_pct,
                "token_diff": token_diff,
                "token_pct": token_pct,
                "similarity_diff": similarity_diff
            }
        }

        self.test_results["comparisons"].append(comparison_result)

    async def run_model_comparison_tests(self, clause_id: str):
        """Run comparison tests with both models."""
        print("\n" + "="*80)
        print("DUAL-MODEL COMPARISON TESTS")
        print("="*80)

        test_cases = get_test_cases()

        for i, test_case in enumerate(test_cases, 1):
            try:
                await self.compare_models_on_test_case(i, clause_id, test_case)
            except Exception as e:
                error_msg = f"Comparison test {i} failed: {e}"
                print(f"  ERROR: {error_msg}")
                import traceback
                traceback.print_exc()

    def generate_report(self):
        """Generate comprehensive comparison report."""
        print("\n" + "="*80)
        print("DUAL-MODEL COMPARISON SUMMARY")
        print("="*80)

        if not self.test_results["comparisons"]:
            print("\nNo comparison results to report.")
            return

        comparisons = self.test_results["comparisons"]
        num_tests = len(comparisons)

        # Calculate aggregate statistics
        primary_stats = {
            "avg_time": sum(c["primary"]["elapsed_time"] for c in comparisons) / num_tests,
            "total_tokens": sum(c["primary"]["tokens"] for c in comparisons),
            "avg_tokens": sum(c["primary"]["tokens"] for c in comparisons) / num_tests,
            "avg_similarity": sum(c["primary"]["similarity_score"] for c in comparisons) / num_tests
        }

        secondary_stats = {
            "avg_time": sum(c["secondary"]["elapsed_time"] for c in comparisons) / num_tests,
            "total_tokens": sum(c["secondary"]["tokens"] for c in comparisons),
            "avg_tokens": sum(c["secondary"]["tokens"] for c in comparisons) / num_tests,
            "avg_similarity": sum(c["secondary"]["similarity_score"] for c in comparisons) / num_tests
        }

        print(f"\nTests Run: {num_tests}")
        print(f"Primary Model: {self.test_results['primary_model']}")
        print(f"Secondary Model: {self.test_results['secondary_model']}")

        print("\nPRIMARY MODEL PERFORMANCE:")
        print(f"  Average Time: {primary_stats['avg_time']:.3f}s")
        print(f"  Total Tokens: {primary_stats['total_tokens']}")
        print(f"  Average Tokens: {primary_stats['avg_tokens']:.1f}")
        print(f"  Average Similarity: {primary_stats['avg_similarity']:.3f}")

        print("\nSECONDARY MODEL PERFORMANCE:")
        print(f"  Average Time: {secondary_stats['avg_time']:.3f}s")
        print(f"  Total Tokens: {secondary_stats['total_tokens']}")
        print(f"  Average Tokens: {secondary_stats['avg_tokens']:.1f}")
        print(f"  Average Similarity: {secondary_stats['avg_similarity']:.3f}")

        # Calculate differences
        time_diff = primary_stats['avg_time'] - secondary_stats['avg_time']
        time_pct = (time_diff / primary_stats['avg_time']) * 100
        token_diff = primary_stats['total_tokens'] - secondary_stats['total_tokens']
        token_pct = (token_diff / primary_stats['total_tokens']) * 100
        similarity_diff = abs(primary_stats['avg_similarity'] - secondary_stats['avg_similarity'])

        print("\nCOMPARATIVE ANALYSIS:")
        print(f"  Time Difference: {time_diff:+.3f}s ({time_pct:+.1f}%)")
        print(f"    {'Secondary' if time_diff > 0 else 'Primary'} model is FASTER")
        print(f"  Token Difference: {token_diff:+d} ({token_pct:+.1f}%)")
        print(f"    {'Secondary' if token_diff > 0 else 'Primary'} model uses FEWER tokens")
        print(f"  Similarity Difference: {similarity_diff:.3f}")
        print(f"    Models {'agree closely' if similarity_diff < 0.1 else 'have moderate differences' if similarity_diff < 0.3 else 'differ significantly'} on similarity scores")

        # Store summary
        self.test_results["summary"] = {
            "primary": primary_stats,
            "secondary": secondary_stats,
            "differences": {
                "time_diff": time_diff,
                "time_pct": time_pct,
                "token_diff": token_diff,
                "token_pct": token_pct,
                "similarity_diff": similarity_diff
            }
        }

        # Save detailed results to file
        output_file = "dual_model_comparison_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"\n  Summary results saved to: {output_file}")

        # Generate recommendations
        print("\nRECOMMENDATIONS:")
        if abs(time_pct) < 10 and abs(token_pct) > 30:
            print("  Consider using secondary model for cost savings with similar performance")
        elif time_pct > 20:
            print("  Secondary model provides significant speed advantage")
        elif similarity_diff > 0.2:
            print("  Models show different analysis patterns - review quality manually")
        else:
            print("  Models perform comparably - choose based on cost/performance needs")

        # Note about detailed comparison files
        print("\nDETAILED ANALYSIS FILES:")
        print("  Full LLM responses and analysis details for each test case are in:")
        print("  dual_model_comparison_details/")
        print("")
        print("  Each test case directory contains:")
        print("    - primary_model_response.txt: Complete primary model analysis")
        print("    - secondary_model_response.txt: Complete secondary model analysis")
        print("    - side_by_side_comparison.txt: Quick comparison summary")
        print("")
        print("  Review these files to compare the quality of:")
        print("    - Risk identification and assessment")
        print("    - Recommendation specificity and relevance")
        print("    - Analysis depth and insights")
        print("    - Suggested text quality")


async def main():
    """Main test execution."""
    print("="*80)
    print("DUAL-MODEL COMPARISON TEST SUITE")
    print("="*80)
    print(f"Testing: GPT-4.1 vs GPT-4.1-mini")
    print(f"Date: {datetime.utcnow().isoformat()}")

    tester = DualModelTester()

    try:
        # Initialize
        initialized = await tester.initialize()
        if not initialized:
            print("\nERROR: Secondary model not configured. Exiting.")
            return

        # Create test clause
        clause_id = await tester.create_test_clause()

        # Run comparison tests
        await tester.run_model_comparison_tests(clause_id)

        # Generate report
        tester.generate_report()

        print("\n  All tests completed successfully!")

    except Exception as e:
        print(f"\n  Test execution failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Always cleanup resources
        try:
            await tester.cleanup()
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
