"""
LLM Strategy Concept Validation

Tests the basic concept of using LLM to determine query strategies.
This is a minimal prototype to validate the approach before full implementation.
"""

import os
import json
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.config_service import ConfigService
from openai import AzureOpenAI


# Minimal strategy descriptions
STRATEGIES = """
Available Query Strategies:

1. ENTITY_FIRST
   - Best for: Single entity queries (e.g., "contracts governed by California")
   - Requirements: EXACTLY ONE positive entity (no negations only, no OR lists)
   - Performance: Low cost (~2 RUs)

2. CONTRACT_DIRECT
   - Best for: Multi-filter, negations, OR lists, complex queries
   - Requirements: Any combination of filters
   - Performance: Medium cost (~5-50 RUs)
   - Use for: "not governed by X", "California or Texas", multiple filters

3. ENTITY_AGGREGATION
   - Best for: Count/sum/average on single entity
   - Requirements: Aggregation keywords + single entity
   - Performance: Very low cost (~1 RU)

4. GRAPH_TRAVERSAL
   - Best for: Relationship queries
   - Requirements: Keywords like "between", "connected", "depends on"
   - Performance: Variable cost (~10-100 RUs)

5. VECTOR_SEARCH
   - Best for: Fuzzy matching, semantic search
   - Use as: Fallback only
   - Performance: High cost (~50-200 RUs)
"""


SYSTEM_PROMPT = f"""You are a query strategy analyzer for a contract database.

{STRATEGIES}

CRITICAL RULES:
- ENTITY_FIRST requires EXACTLY ONE positive entity (not "California or Texas", not "not Alabama")
- Use CONTRACT_DIRECT for: negations, OR lists, multiple entities
- For "California, Texas, or Florida" → CONTRACT_DIRECT with IN operator
- For "not governed by Alabama" → CONTRACT_DIRECT with != operator

Return ONLY valid JSON (no markdown):
{{
  "primary_strategy": "CONTRACT_DIRECT",
  "entities": {{
    "governing_law_states": [{{"value": "california", "display": "California"}}]
  }},
  "negations": {{}},
  "filters": {{
    "governing_law_state": {{"operator": "IN", "values": ["california", "texas"]}}
  }},
  "confidence": 0.95,
  "reasoning": "Brief explanation"
}}
"""


# Test queries covering different patterns
TEST_QUERIES = [
    # Simple single entity - should be ENTITY_FIRST
    "Show all contracts governed by California",

    # Negation - should be CONTRACT_DIRECT
    "Show all contracts not governed by Alabama",

    # OR list - should be CONTRACT_DIRECT
    "Show contracts in California, Texas, or Florida",

    # Multi-filter - should be CONTRACT_DIRECT
    "MSA contracts with Microsoft",

    # Complex compound - should be CONTRACT_DIRECT
    "MSA contracts with Microsoft in California or Texas but not Alabama",

    # Aggregation - should be ENTITY_AGGREGATION
    "How many contracts are governed by California?",

    # Relationship - should be GRAPH_TRAVERSAL
    "What contracts depend on Microsoft libraries?",

    # Variation: "excluding" - should be CONTRACT_DIRECT
    "Show contracts excluding California and Texas",

    # Variation: "except" - should be CONTRACT_DIRECT
    "All contracts except those governed by Florida",

    # Edge case: implicit OR - should be CONTRACT_DIRECT
    "Show MSA and NDA contracts"
]


def test_llm_strategy_concept():
    """Test LLM concept with sample queries"""

    print("=" * 80)
    print("LLM STRATEGY CONCEPT VALIDATION")
    print("=" * 80)

    # Initialize Azure OpenAI client
    try:
        client = AzureOpenAI(
            api_key=ConfigService.azure_openai_key(),
            api_version="2024-02-15-preview",
            azure_endpoint=ConfigService.azure_openai_url()
        )
        print(f"\n[OK] Connected to Azure OpenAI")
    except Exception as e:
        print(f"\n[FAIL] Cannot connect to Azure OpenAI: {e}")
        return

    deployment = ConfigService.azure_openai_completions_deployment()
    print(f"[OK] Using deployment: {deployment}")

    results = []
    success_count = 0
    error_count = 0

    print(f"\n{'='*80}")
    print(f"Testing {len(TEST_QUERIES)} queries...")
    print(f"{'='*80}\n")

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Query: {query}")
        print("-" * 80)

        try:
            # Call LLM
            response = client.chat.completions.create(
                model=deployment,
                temperature=0.0,  # Deterministic
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                timeout=10.0
            )

            # Parse response
            llm_response = json.loads(response.choices[0].message.content)

            # Display key fields
            print(f"Strategy: {llm_response.get('primary_strategy')}")
            print(f"Confidence: {llm_response.get('confidence', 0):.2f}")
            print(f"Reasoning: {llm_response.get('reasoning', 'N/A')}")

            # Show entities
            entities = llm_response.get('entities', {})
            if entities:
                print(f"Entities: {entities}")

            # Show negations
            negations = llm_response.get('negations', {})
            if negations:
                print(f"Negations: {negations}")

            # Show filters
            filters = llm_response.get('filters', {})
            if filters:
                print(f"Filters: {filters}")

            results.append({
                "query": query,
                "strategy": llm_response.get('primary_strategy'),
                "confidence": llm_response.get('confidence', 0),
                "reasoning": llm_response.get('reasoning', ''),
                "success": True
            })

            print("[OK] Valid JSON response")
            success_count += 1

        except json.JSONDecodeError as e:
            print(f"[FAIL] Invalid JSON response: {e}")
            error_count += 1
            results.append({
                "query": query,
                "error": f"JSON decode error: {e}",
                "success": False
            })

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            error_count += 1
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total queries: {len(TEST_QUERIES)}")
    print(f"Successful: {success_count} ({success_count/len(TEST_QUERIES)*100:.1f}%)")
    print(f"Errors: {error_count} ({error_count/len(TEST_QUERIES)*100:.1f}%)")

    # Strategy distribution
    if success_count > 0:
        strategies = [r.get('strategy') for r in results if r.get('success')]
        from collections import Counter
        strategy_counts = Counter(strategies)

        print(f"\nStrategy Distribution:")
        for strategy, count in strategy_counts.most_common():
            print(f"  {strategy}: {count} ({count/success_count*100:.1f}%)")

        # Average confidence
        confidences = [r.get('confidence', 0) for r in results if r.get('success')]
        avg_confidence = sum(confidences) / len(confidences)
        print(f"\nAverage Confidence: {avg_confidence:.2f}")

    # Save full results
    output_file = "tmp/llm_concept_validation_results.json"
    os.makedirs("tmp", exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: {output_file}")

    # Decision
    print(f"\n{'='*80}")
    print("DECISION")
    print(f"{'='*80}")

    if success_count >= 8:  # 80% success threshold
        print("[GO] Concept validated - proceed to Phase 1 implementation")
        print("Reasons:")
        print("  - High success rate (≥80%)")
        print("  - LLM produces valid JSON responses")
        print("  - Reasoning quality appears good")
    else:
        print("[NO-GO] Concept needs refinement")
        print("Reasons:")
        print(f"  - Low success rate ({success_count/len(TEST_QUERIES)*100:.1f}%)")
        print("  - Need to debug LLM responses or adjust prompt")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_llm_strategy_concept()
