"""
Test script to verify normalized value tracking in contract documents.
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the Azure imports to avoid dependency issues during testing
import unittest.mock as mock
sys.modules['azure.cosmos'] = mock.MagicMock()
sys.modules['azure.cosmos.aio'] = mock.MagicMock()

from src.services.contract_entities_service import ContractEntitiesService

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
        }
    ]
    
    print("Testing entity name normalization:")
    print("-" * 40)
    
    for test in test_cases:
        original = test["original"]
        expected = test["expected_normalized"]
        actual = ContractEntitiesService.normalize_entity_name(original)
        
        print(f"Field: {test['field']}")
        print(f"Original: {original}")
        print(f"Expected Normalized: {expected}")
        print(f"Actual Normalized: {actual}")
        print(f"Status: {'✓ PASS' if actual == expected else '✗ FAIL'}")
        print()
    
    # Example of how the metadata structure should look
    example_metadata = {
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
    }
    
    print("=" * 80)
    print("EXAMPLE CONTRACT METADATA STRUCTURE")
    print("=" * 80)
    print(json.dumps(example_metadata, indent=2))
    
    print()
    print("=" * 80)
    print("KEY POINTS")
    print("=" * 80)
    print("""
1. Metadata contains BOTH original and normalized values
2. Root-level properties use NORMALIZED values for searching
3. Chunks and clauses use NORMALIZED values in their properties
4. Entity catalogs are created with ORIGINAL values (for display)
5. Entity matching/searching uses NORMALIZED values internally
""")


if __name__ == "__main__":
    test_normalized_values()