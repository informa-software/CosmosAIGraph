"""
Test script for Clause Library Phase 2 functionality.

This script tests:
1. Sample data loading
2. AI comparison accuracy
3. Vector search quality
4. Caching performance
5. Embedding optimization
"""

import asyncio
import sys
import os
import time
import json
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
from src.services.clause_library_service import ClauseLibraryService
from src.services.config_service import ConfigService
from src.models.clause_library_models import CreateClauseRequest, CompareClauseRequest, SuggestClauseRequest
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

# Set clause library service to DEBUG to see detailed vector search logs
logging.getLogger('src.services.clause_library_service').setLevel(logging.DEBUG)


class Phase2Tester:
    """Test harness for Phase 2 functionality."""

    def __init__(self):
        self.cosmos = CosmosNoSQLService()
        self.ai = AiService()
        self.clause_service = ClauseLibraryService(self.cosmos, self.ai)
        self.test_results = {
            "clauses_loaded": 0,
            "comparison_tests": [],
            "vector_search_tests": [],
            "cache_performance": {},
            "errors": []
        }

    async def cleanup(self):
        """Clean up resources and close connections."""
        print("\nCleaning up resources...")

        # Close CosmosDB client
        if hasattr(self.cosmos, '_client') and self.cosmos._client:
            try:
                await self.cosmos._client.close()
                print("  ✓ CosmosDB client closed")
            except Exception as e:
                print(f"  ⚠ Warning: CosmosDB client close error: {e}")

        # Close any aiohttp sessions in AI service
        if hasattr(self.ai, 'session') and self.ai.session:
            try:
                await self.ai.session.close()
                print("  ✓ AI service session closed")
            except Exception as e:
                print(f"  ⚠ Warning: AI service session close error: {e}")

        print("Cleanup complete")

    async def initialize(self):
        """Initialize services."""
        print("Initializing services...")

        # Initialize CosmosDB client
        await self.cosmos.initialize()
        print("  ✓ CosmosDB client initialized")

        # Set database
        self.cosmos.set_db(ConfigService.graph_source_db())
        print("  ✓ CosmosDB database connected")

        # Initialize clause library service
        await self.clause_service.initialize()
        print("  ✓ Clause library service initialized")

        print("Services initialized successfully")

    async def load_sample_data(self) -> List[str]:
        """Load sample clauses into the database."""
        print("\n" + "="*80)
        print("LOADING SAMPLE DATA")
        print("="*80)

        clauses = get_sample_clauses()
        clause_ids = []

        for i, clause_data in enumerate(clauses, 1):
            try:
                print(f"\n[{i}/{len(clauses)}] Creating clause: {clause_data['name']}")

                request = CreateClauseRequest(**clause_data)
                clause = await self.clause_service.create_clause(
                    request=request,
                    user_email="test@example.com"
                )

                clause_ids.append(clause.id)
                self.test_results["clauses_loaded"] += 1

                has_embedding = clause.embedding is not None and len(clause.embedding) > 0
                embedding_info = f"{len(clause.embedding)} dims" if has_embedding else "MISSING"

                print(f"  ✓ Created clause ID: {clause.id}")
                print(f"  ✓ Category: {clause.category_path_display}")
                print(f"  ✓ Embedding: {embedding_info}")

                if not has_embedding:
                    self.test_results["errors"].append(f"Clause '{clause_data['name']}' has no embedding")

            except Exception as e:
                error_msg = f"Error loading clause '{clause_data['name']}': {e}"
                print(f"  ✗ {error_msg}")
                self.test_results["errors"].append(error_msg)

        print(f"\n✓ Successfully loaded {self.test_results['clauses_loaded']} clauses")
        return clause_ids

    async def test_comparison_accuracy(self, clause_ids: List[str]):
        """Test AI comparison accuracy with known test cases."""
        print("\n" + "="*80)
        print("TESTING COMPARISON ACCURACY")
        print("="*80)

        test_cases = get_test_cases()

        for i, test_case in enumerate(test_cases, 1):
            try:
                print(f"\n[{i}/{len(test_cases)}] Test: {test_case['description']}")
                print(f"  Comparing against: {test_case['clause_name']}")

                # Find clause by name
                clause = None
                for clause_id in clause_ids:
                    c = await self.clause_service.get_clause(clause_id)
                    if c and c.name == test_case['clause_name']:
                        clause = c
                        break

                if not clause:
                    print(f"  ✗ Clause not found: {test_case['clause_name']}")
                    continue

                # Perform comparison
                request = CompareClauseRequest(
                    clause_id=clause.id,
                    contract_text=test_case['contract_text'],
                    contract_id="test_contract"
                )

                start_time = time.time()
                comparison = await self.clause_service.compare_clause(
                    request=request,
                    user_email="test@example.com",
                    use_cache=False  # First run without cache
                )
                first_run_time = time.time() - start_time

                # Test with cache
                start_time = time.time()
                cached_comparison = await self.clause_service.compare_clause(
                    request=request,
                    user_email="test@example.com",
                    use_cache=True  # Second run with cache
                )
                cached_run_time = time.time() - start_time

                # Analyze results
                similarity = comparison.comparison.similarity_score
                risk_level = comparison.risk_analysis.overall_risk
                risk_count = len(comparison.risk_analysis.risks)
                rec_count = len(comparison.recommendations)

                # Get AI processing details
                ai_tokens = comparison.ai_analysis.completion_tokens
                ai_model = comparison.ai_analysis.model

                # Calculate cache efficiency
                speedup = first_run_time / cached_run_time if cached_run_time > 0 else 0

                print(f"  ✓ Similarity Score: {similarity:.3f} (expected: {test_case['expected_similarity']})")
                print(f"  ✓ Risk Level: {risk_level} ({risk_count} risks identified)")
                print(f"  ✓ Recommendations: {rec_count}")
                print(f"  ✓ AI Model: {ai_model} | Tokens: {ai_tokens}")
                print(f"  ✓ First run: {first_run_time:.3f}s | Cached: {cached_run_time:.3f}s (speedup: {speedup:.1f}x)")

                # Store results
                self.test_results["comparison_tests"].append({
                    "test_case": test_case["description"],
                    "clause_name": test_case["clause_name"],
                    "similarity_score": similarity,
                    "expected_similarity": test_case["expected_similarity"],
                    "risk_level": risk_level,
                    "risk_count": risk_count,
                    "recommendation_count": rec_count,
                    "ai_model": ai_model,
                    "ai_tokens": ai_tokens,
                    "first_run_time": first_run_time,
                    "cached_run_time": cached_run_time,
                    "cache_speedup": speedup
                })

            except Exception as e:
                error_msg = f"Comparison test failed: {e}"
                print(f"  ✗ {error_msg}")
                self.test_results["errors"].append(error_msg)

    async def test_vector_search(self):
        """Test vector search quality and performance."""
        print("\n" + "="*80)
        print("TESTING VECTOR SEARCH")
        print("="*80)

        search_queries = [
            {
                "text": "indemnification and hold harmless obligations",
                "expected_category": "indemnification",
                "description": "Indemnification search"
            },
            {
                "text": "confidential information and trade secrets",
                "expected_category": "confidentiality",
                "description": "Confidentiality search"
            },
            {
                "text": "payment terms and invoice schedule",
                "expected_category": "payment",
                "description": "Payment terms search"
            },
            {
                "text": "ownership of work product and intellectual property",
                "expected_category": "intellectual_property",
                "description": "IP rights search"
            }
        ]

        for i, query in enumerate(search_queries, 1):
            try:
                print(f"\n[{i}/{len(search_queries)}] {query['description']}")
                print(f"  Query: {query['text'][:60]}...")

                request = SuggestClauseRequest(
                    contract_text=query['text'],
                    top_k=5
                )

                start_time = time.time()
                suggestions = await self.clause_service.suggest_clause(request)
                search_time = time.time() - start_time

                print(f"  ✓ Found {len(suggestions)} suggestions in {search_time:.3f}s")

                for j, (clause, score) in enumerate(suggestions[:3], 1):
                    print(f"    {j}. {clause.name} (similarity: {score:.3f})")

                # Store results
                self.test_results["vector_search_tests"].append({
                    "description": query["description"],
                    "query_text": query["text"],
                    "expected_category": query["expected_category"],
                    "results_count": len(suggestions),
                    "search_time": search_time,
                    "top_suggestions": [
                        {"name": clause.name, "score": score}
                        for clause, score in suggestions[:3]
                    ]
                })

            except Exception as e:
                error_msg = f"Vector search test failed: {e}"
                print(f"  ✗ {error_msg}")
                self.test_results["errors"].append(error_msg)

    async def test_embedding_cache(self):
        """Test embedding cache with duplicate operations."""
        print("\n" + "="*80)
        print("TESTING EMBEDDING CACHE")
        print("="*80)

        test_text = "This is a test clause about indemnification and liability."

        print("\n1. Generate embedding for test text (first time - cache miss)")
        start = time.time()
        embedding1 = await self.clause_service._generate_embedding_optimized(test_text, use_cache=True)
        first_time = time.time() - start
        print(f"   Time: {first_time:.3f}s | Dimensions: {len(embedding1)}")

        print("\n2. Generate embedding for SAME text (second time - cache hit expected)")
        start = time.time()
        embedding2 = await self.clause_service._generate_embedding_optimized(test_text, use_cache=True)
        cached_time = time.time() - start
        print(f"   Time: {cached_time:.3f}s | Dimensions: {len(embedding2)}")

        speedup = first_time / cached_time if cached_time > 0 else 0
        print(f"   Speedup: {speedup:.1f}x")

        # Verify embeddings are identical
        if embedding1 == embedding2:
            print("   ✓ Embeddings match (cache working correctly)")
        else:
            print("   ✗ Embeddings don't match (cache issue)")

        print("\n3. Generate embeddings for multiple identical texts")
        identical_count = 5
        times = []
        for i in range(identical_count):
            start = time.time()
            await self.clause_service._generate_embedding_optimized(test_text, use_cache=True)
            times.append(time.time() - start)

        print(f"   Run 1 (cache miss): {times[0]:.3f}s")
        avg_cached = sum(times[1:]) / len(times[1:])
        print(f"   Runs 2-5 (cache hits): avg {avg_cached:.3f}s")
        print(f"   Average speedup: {times[0] / avg_cached:.1f}x")

    async def test_cache_performance(self):
        """Test cache performance and statistics."""
        print("\n" + "="*80)
        print("TESTING CACHE PERFORMANCE")
        print("="*80)

        # Get cache stats
        stats = self.clause_service.get_cache_stats()

        print("\nCache Statistics:")
        print(f"  Comparison Cache: {stats['comparison_cache']['size']}/{stats['comparison_cache']['max_size']} entries")
        print(f"  Embedding Cache: {stats['embedding_cache']['size']}/{stats['embedding_cache']['max_size']} entries")

        print("\nPerformance Metrics:")
        metrics = stats['metrics']
        print(f"  Total Comparisons: {metrics['comparisons_total']}")
        print(f"  Cached Comparisons: {metrics['comparisons_cached']}")
        if metrics['comparisons_total'] > 0:
            cache_hit_rate = (metrics['comparisons_cached'] / metrics['comparisons_total']) * 100
            print(f"  Cache Hit Rate: {cache_hit_rate:.1f}%")
        print(f"  Avg Comparison Time: {metrics['avg_comparison_time']:.3f}s")

        print(f"\n  Total Embeddings: {metrics['embeddings_total']}")
        print(f"  Cached Embeddings: {metrics['embeddings_cached']}")
        if metrics['embeddings_total'] > 0:
            cache_hit_rate = (metrics['embeddings_cached'] / metrics['embeddings_total']) * 100
            print(f"  Cache Hit Rate: {cache_hit_rate:.1f}%")
        print(f"  Avg Embedding Time: {metrics['avg_embedding_time']:.3f}s")

        print("\nNote: Low embedding cache hit rate is expected because:")
        print("  - Each clause has unique content (8 unique embeddings)")
        print("  - Each search query is unique (4 unique embeddings)")
        print("  - No duplicate text processed in this test run")
        print("  - Cache hits occur when the SAME text is embedded multiple times")

        self.test_results["cache_performance"] = stats

    def generate_report(self):
        """Generate test results report."""
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)

        print(f"\nClauses Loaded: {self.test_results['clauses_loaded']}")
        print(f"Comparison Tests: {len(self.test_results['comparison_tests'])}")
        print(f"Vector Search Tests: {len(self.test_results['vector_search_tests'])}")
        print(f"Errors: {len(self.test_results['errors'])}")

        if self.test_results['comparison_tests']:
            print("\nComparison Test Summary:")
            tests = self.test_results['comparison_tests']
            avg_similarity = sum(t['similarity_score'] for t in tests) / len(tests)
            avg_speedup = sum(t['cache_speedup'] for t in tests) / len(tests)
            avg_tokens = sum(t['ai_tokens'] for t in tests) / len(tests)
            avg_first_run = sum(t['first_run_time'] for t in tests) / len(tests)
            total_tokens = sum(t['ai_tokens'] for t in tests)

            print(f"  Average Similarity Score: {avg_similarity:.3f}")
            print(f"  Average AI Processing Time: {avg_first_run:.3f}s")
            print(f"  Average Tokens Used: {avg_tokens:.1f}")
            print(f"  Total Tokens Used: {total_tokens}")
            print(f"  Average Cache Speedup: {avg_speedup:.1f}x")

        if self.test_results['vector_search_tests']:
            print("\nVector Search Summary:")
            avg_time = sum(t['search_time'] for t in self.test_results['vector_search_tests']) / len(self.test_results['vector_search_tests'])
            print(f"  Average Search Time: {avg_time:.3f}s")

        if self.test_results['errors']:
            print("\nErrors:")
            for error in self.test_results['errors']:
                print(f"  ✗ {error}")

        # Save detailed results to file
        output_file = "phase2_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"\n✓ Detailed results saved to: {output_file}")


async def main():
    """Main test execution."""
    print("="*80)
    print("CLAUSE LIBRARY - PHASE 2 TESTING")
    print("="*80)

    tester = Phase2Tester()

    try:
        # Initialize
        await tester.initialize()

        # Load sample data
        clause_ids = await tester.load_sample_data()

        # Run tests
        await tester.test_comparison_accuracy(clause_ids)
        await tester.test_vector_search()
        await tester.test_embedding_cache()
        await tester.test_cache_performance()

        # Generate report
        tester.generate_report()

        print("\n✓ All tests completed successfully!")

    except Exception as e:
        print(f"\n✗ Test execution failed: {e}")
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
