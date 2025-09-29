"""
Simple test for entity name normalization without dependencies.
"""

import re

# Copied from ContractEntitiesService for testing
COMPANY_SUFFIXES = [
    'llc', 'l.l.c.', 'inc', 'incorporated', 'corp', 'corporation',
    'company', 'co', 'ltd', 'limited', 'plc', 'p.l.c.', 'llp',
    'l.l.p.', 'lp', 'l.p.', 'partners', 'partnership', 'group',
    'holdings', 'holding', 'enterprises', 'intl', 'international'
    # Note: 'ent' removed as it's too generic
]

def normalize_entity_name(name: str) -> str:
    """
    Normalize an entity name for consistent storage and matching.
    """
    if not name:
        return ""
        
    # Convert to lowercase and strip
    normalized = name.lower().strip()
    
    # Replace common separators and punctuation with spaces
    # Keep alphanumeric and spaces only
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Replace multiple spaces with single underscore
    normalized = re.sub(r'\s+', '_', normalized)
    
    # Remove trailing common suffixes for matching
    for suffix in COMPANY_SUFFIXES:
        # Remove suffix with underscore before it
        normalized = re.sub(rf'_{re.escape(suffix)}$', '', normalized)
        # Also remove if suffix appears at the end without underscore
        normalized = re.sub(rf'{re.escape(suffix)}$', '', normalized)
    
    # Clean up any trailing underscores
    normalized = re.sub(r'_+$', '', normalized)
    
    # Also remove leading "the"
    normalized = re.sub(r'^the_', '', normalized)
    
    return normalized


def test_normalized_values():
    """Test the normalized value implementation"""
    
    print("=" * 80)
    print("TESTING NORMALIZED VALUE TRACKING")
    print("=" * 80)
    print()
    
    # Test cases with original values that should be normalized
    test_cases = [
        {
            "field": "ContractorPartyName",
            "original": "CAMERON D WILLIAMS DBA C&Y TRANSPORTATION LLC",
            "expected_normalized": "cameron_d_williams_dba_c_y_transportation"
        },
        {
            "field": "ContractingPartyName", 
            "original": "The Westervelt Company",
            "expected_normalized": "westervelt"
        },
        {
            "field": "GoverningLawState",
            "original": "Alabama.",
            "expected_normalized": "alabama"
        },
        {
            "field": "ContractType",
            "original": "Master Services Agreement",
            "expected_normalized": "master_services_agreement"
        },
        {
            "field": "ContractType",
            "original": "Non-Disclosure Agreement",
            "expected_normalized": "non_disclosure_agreement"
        },
        {
            "field": "ContractorPartyName",
            "original": "ABC Corporation",
            "expected_normalized": "abc"
        },
        {
            "field": "ContractorPartyName",
            "original": "XYZ Inc.",
            "expected_normalized": "xyz_inc"  # Period becomes underscore, then "inc" at end
        },
        {
            "field": "ContractorPartyName",
            "original": "XYZ Inc",  # Without period
            "expected_normalized": "xyz"
        }
    ]
    
    print("Testing entity name normalization:")
    print("-" * 40)
    
    all_pass = True
    for test in test_cases:
        original = test["original"]
        expected = test["expected_normalized"]
        actual = normalize_entity_name(original)
        passed = actual == expected
        
        print(f"Field: {test['field']}")
        print(f"Original: '{original}'")
        print(f"Expected: '{expected}'")
        print(f"Actual:   '{actual}'")
        print(f"Status: {'[PASS]' if passed else '[FAIL]'}")
        print()
        
        if not passed:
            all_pass = False
    
    # Show example metadata structure
    print("=" * 80)
    print("EXAMPLE CONTRACT DOCUMENT STRUCTURE")
    print("=" * 80)
    print("""
{
  "id": "contract_abc123",
  "pk": "contracts",
  "metadata": {
    "ContractorPartyName": {
      "value": "CAMERON D WILLIAMS DBA C&Y TRANSPORTATION LLC",
      "normalizedValue": "cameron_d_williams_dba_c_y_transportation",
      "confidence": 0.878
    },
    "ContractingPartyName": {
      "value": "The Westervelt Company",
      "normalizedValue": "westervelt",
      "confidence": 0.95
    },
    "GoverningLawState": {
      "value": "Alabama.",
      "normalizedValue": "alabama",
      "confidence": 1.0
    },
    "ContractType": {
      "value": "Master Services Agreement",
      "normalizedValue": "master_services_agreement",
      "confidence": 0.92
    }
  },
  // Root level uses normalized values for searching
  "contractor_party": "cameron_d_williams_dba_c_y_transportation",
  "contracting_party": "westervelt",
  "governing_law": "alabama",
  "contract_type": "master_services_agreement"
}
""")
    
    print("=" * 80)
    print("KEY IMPLEMENTATION POINTS")
    print("=" * 80)
    print("""
1. Metadata Structure:
   - Contains ORIGINAL value (as extracted by AI)
   - Contains NORMALIZED value (for consistent searching)
   - Contains CONFIDENCE score (from AI extraction)

2. Root-Level Properties:
   - Use NORMALIZED values for database queries
   - Enable consistent searching across contracts

3. Chunks and Clauses:
   - Also use NORMALIZED values in their searchable fields
   - Ensures vector search and filtering work correctly

4. Entity Catalogs:
   - Created with ORIGINAL values as display names
   - Use NORMALIZED values as keys for lookups
   - Track statistics per normalized entity

5. Benefits:
   - "Alabama" and "Alabama." map to same entity
   - "ABC Corp" and "ABC Corporation" map to same entity  
   - Consistent querying across all contract variations
""")
    
    if all_pass:
        print("\n[SUCCESS] All normalization tests passed!")
    else:
        print("\n[WARNING] Some normalization tests failed!")


if __name__ == "__main__":
    test_normalized_values()