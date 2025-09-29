"""
Demonstration of the hybrid matching implementation for company names.
This shows how the system handles various name variations and typos.
"""

from src.services.contract_entities_service import ContractEntitiesService

def test_company_variations():
    """Test various company name variations"""
    
    test_cases = [
        ("ABC Corporation", "ABC Corp"),
        ("ABC Inc.", "ABC Incorporated"),
        ("First National Bank", "National First Bank"),
        ("The Westervelt Company", "Westervelt Co"),
        ("Alabama Fire Sprinkler Contractors", "Alabama Fire Sprinkler Contractors LLC"),
        ("Microsoft Corporation", "Microsoft Corp."),
        ("Apple Inc", "Apple Incorporated"),
        ("Google LLC", "Google L.L.C."),
        ("JPMorgan Chase & Co.", "JP Morgan Chase and Company"),
        ("AT&T Inc.", "AT and T Inc"),
    ]
    
    print("=" * 80)
    print("HYBRID COMPANY NAME MATCHING DEMONSTRATION")
    print("=" * 80)
    print()
    
    for name1, name2 in test_cases:
        score, method = ContractEntitiesService.hybrid_company_match(name1, name2)
        normalized1 = ContractEntitiesService.normalize_entity_name(name1)
        normalized2 = ContractEntitiesService.normalize_entity_name(name2)
        
        print(f"Company 1: {name1}")
        print(f"Company 2: {name2}")
        print(f"Normalized 1: {normalized1}")
        print(f"Normalized 2: {normalized2}")
        print(f"Match Score: {score:.3f}")
        print(f"Match Method: {method}")
        print(f"Match Result: {'[MATCH]' if score >= 0.85 else '[NO MATCH]' if score < 0.7 else '[POSSIBLE MATCH]'}")
        print("-" * 40)
        print()


def test_token_similarity():
    """Test token-based similarity for reordered words"""
    
    test_cases = [
        ("First National Bank", "National First Bank"),
        ("Bank of America", "America Bank of"),
        ("Wells Fargo Bank", "Fargo Wells Bank"),
        ("New York Life Insurance", "Life Insurance New York"),
    ]
    
    print("=" * 80)
    print("TOKEN SIMILARITY FOR REORDERED WORDS")
    print("=" * 80)
    print()
    
    for name1, name2 in test_cases:
        token_score = ContractEntitiesService.token_similarity(name1, name2)
        print(f"Name 1: {name1}")
        print(f"Name 2: {name2}")
        print(f"Token Similarity: {token_score:.3f}")
        print(f"Result: {'Perfect token match' if token_score == 1.0 else 'Partial token match'}")
        print("-" * 40)
        print()


def test_fuzzy_matching():
    """Test overall fuzzy matching with various scenarios"""
    
    test_cases = [
        # Exact matches after normalization
        ("ABC Corp", "ABC Corporation", "Should match - same company, different suffix"),
        
        # Similar companies with minor differences
        ("Microsoft Corp", "Microsft Corp", "Should handle typos"),
        ("Goldman Sachs", "Goldman Sacks", "Should handle phonetic similarities"),
        
        # Different companies
        ("Apple Inc", "Microsoft Corp", "Should NOT match - different companies"),
        ("Google LLC", "Amazon Inc", "Should NOT match - different companies"),
    ]
    
    print("=" * 80)
    print("FUZZY MATCHING SCENARIOS")
    print("=" * 80)
    print()
    
    for name1, name2, description in test_cases:
        score = ContractEntitiesService.fuzzy_match(name1, name2)
        print(f"Scenario: {description}")
        print(f"Name 1: {name1}")
        print(f"Name 2: {name2}")
        print(f"Fuzzy Match Score: {score:.3f}")
        print(f"Result: {'[MATCH]' if score >= 0.85 else '[NO MATCH]' if score < 0.5 else '[POSSIBLE MATCH]'}")
        print("-" * 40)
        print()


if __name__ == "__main__":
    test_company_variations()
    test_token_similarity()
    test_fuzzy_matching()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The hybrid matching system combines:
1. Jaro-Winkler distance (70% weight) - Best for company names with similar prefixes
2. Token-based similarity (30% weight) - Handles reordered words
3. Phonetic matching bonus (10% bonus) - Catches spelling variations
4. Domain-specific normalization - Removes common suffixes (LLC, Inc, Corp, etc.)

This provides robust matching for:
- Company name variations (ABC Corp vs ABC Corporation)
- Reordered words (First National Bank vs National First Bank)
- Minor typos and spelling differences
- Different legal entity suffixes

Threshold recommendations:
- >= 0.95: Very high confidence match
- >= 0.85: High confidence match (default threshold)
- >= 0.70: Moderate confidence, may need human review
- < 0.70: Low confidence, likely different entities
""")