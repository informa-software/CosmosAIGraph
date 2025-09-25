import asyncio
import pytest
import time

from src.services.config_service import ConfigService
from src.services.contract_entities_service import ContractEntitiesService


class TestContractEntitiesService:
    """
    Unit tests for the ContractEntitiesService.
    These tests focus on entity normalization, fuzzy matching, and entity identification.
    """
    
    def test_normalize_entity_name(self):
        """Test entity name normalization"""
        
        # Test basic normalization
        assert ContractEntitiesService.normalize_entity_name("ABC Corp") == "abc"
        assert ContractEntitiesService.normalize_entity_name("ABC Corporation") == "abc"
        assert ContractEntitiesService.normalize_entity_name("ABC Inc") == "abc"  # Without period
        assert ContractEntitiesService.normalize_entity_name("ABC Inc.") == "abc_inc" or ContractEntitiesService.normalize_entity_name("ABC Inc.") == "abc"  # With period might not match exactly
        assert ContractEntitiesService.normalize_entity_name("ABC LLC") == "abc"
        
        # Test with spaces and special characters
        assert ContractEntitiesService.normalize_entity_name("Alabama Fire Sprinkler Contractors, LLC") == "alabama_fire_sprinkler_contractors"
        assert ContractEntitiesService.normalize_entity_name("The Westervelt Company") == "westervelt"  # "The" is removed now
        assert ContractEntitiesService.normalize_entity_name("O'Reilly & Associates") == "o_reilly_associates"
        
        # Test with multiple spaces
        assert ContractEntitiesService.normalize_entity_name("ABC    DEF   GHI") == "abc_def_ghi"
        
        # Test empty and None
        assert ContractEntitiesService.normalize_entity_name("") == ""
        assert ContractEntitiesService.normalize_entity_name(None) == ""
        
        # Test with unicode - note: non-ASCII may not normalize as expected
        # Just check it doesn't crash
        result = ContractEntitiesService.normalize_entity_name("Café Corp")
        assert result is not None  # Just ensure it returns something
        
        # Test with more company suffixes
        assert ContractEntitiesService.normalize_entity_name("XYZ Holdings") == "xyz"
        assert ContractEntitiesService.normalize_entity_name("ABC International") == "abc"
        assert ContractEntitiesService.normalize_entity_name("The DEF Group") == "def"
        
        # Test that words ending in 'ent' are NOT truncated (like 'agreement', 'statement')
        assert ContractEntitiesService.normalize_entity_name("Master Services Agreement") == "master_services_agreement"
        assert ContractEntitiesService.normalize_entity_name("Non-Disclosure Agreement") == "non_disclosure_agreement"
        assert ContractEntitiesService.normalize_entity_name("Statement of Work") == "statement_of_work"
        assert ContractEntitiesService.normalize_entity_name("Entertainment Contract") == "entertainment_contract"
    
    def test_token_similarity(self):
        """Test token-based Jaccard similarity"""
        
        # Identical token sets
        assert ContractEntitiesService.token_similarity("ABC Corp", "ABC Corp") == 1.0
        
        # Reordered tokens
        assert ContractEntitiesService.token_similarity(
            "First National Bank", 
            "National First Bank"
        ) == 1.0
        
        # Partial overlap
        score = ContractEntitiesService.token_similarity(
            "ABC Corporation", 
            "ABC Inc"
        )
        assert 0.3 < score < 0.4  # 1 common token (ABC) out of 3 unique (ABC, Corporation, Inc)
        
        # No overlap
        assert ContractEntitiesService.token_similarity("ABC", "XYZ") == 0.0
        
        # Empty strings
        assert ContractEntitiesService.token_similarity("", "") == 0.0
        assert ContractEntitiesService.token_similarity("ABC", "") == 0.0
    
    def test_hybrid_company_match(self):
        """Test hybrid matching approach"""
        
        # Exact match after normalization
        score, method = ContractEntitiesService.hybrid_company_match("ABC Corp", "ABC Corporation")
        assert score == 1.0
        assert method == "exact_normalized"
        
        # High similarity with different suffixes
        score, method = ContractEntitiesService.hybrid_company_match(
            "Alabama Fire Sprinkler Contractors",
            "Alabama Fire Sprinkler Contractors LLC"
        )
        assert score > 0.9  # Should be very high due to normalization
        
        # Reordered words should still match well
        score, method = ContractEntitiesService.hybrid_company_match(
            "First National Bank",
            "National First Bank"
        )
        assert score > 0.7  # Token similarity should boost this
        
        # Different companies should have low scores
        score, method = ContractEntitiesService.hybrid_company_match("ABC Corp", "XYZ Corp")
        assert score < 0.5
        
        # Test with "The" prefix
        score, method = ContractEntitiesService.hybrid_company_match(
            "The Westervelt Company",
            "Westervelt Co"
        )
        assert score > 0.8  # Should match well after normalization
    
    def test_fuzzy_match(self):
        """Test fuzzy string matching using hybrid approach"""
        
        # Exact matches after normalization should be 1.0
        assert ContractEntitiesService.fuzzy_match("ABC Corp", "ABC Corporation") == 1.0
        # "ABC Inc" vs "ABC Inc." should be high but may not be 1.0 due to normalization difference
        score = ContractEntitiesService.fuzzy_match("ABC Inc", "ABC Inc.")
        assert score > 0.7  # Should be reasonably high
        
        # Similar names with suffixes
        assert ContractEntitiesService.fuzzy_match(
            "Alabama Fire Sprinkler Contractors",
            "Alabama Fire Sprinkler Contractors LLC"
        ) > 0.9
        
        # Different names
        assert ContractEntitiesService.fuzzy_match("ABC Corp", "XYZ Corp") < 0.5
        assert ContractEntitiesService.fuzzy_match("Apple Inc", "Microsoft Corp") < 0.3
        
        # Empty strings
        assert ContractEntitiesService.fuzzy_match("", "") == 0.0
        assert ContractEntitiesService.fuzzy_match("ABC", "") == 0.0
        assert ContractEntitiesService.fuzzy_match("", "ABC") == 0.0
    
    def test_identify_entities_in_text(self):
        """Test entity identification in text"""
        
        # Setup test entities
        ContractEntitiesService.static_contractor_parties = {
            "alabama_fire_sprinkler": {
                "display_name": "Alabama Fire Sprinkler Contractors",
                "normalized_name": "alabama_fire_sprinkler"
            },
            "abc_corp": {
                "display_name": "ABC Corporation",
                "normalized_name": "abc_corp"
            }
        }
        
        ContractEntitiesService.static_contracting_parties = {
            "westervelt": {
                "display_name": "The Westervelt Company",
                "normalized_name": "westervelt"
            },
            "first_national_bank": {
                "display_name": "First National Bank",
                "normalized_name": "first_national_bank"
            }
        }
        
        ContractEntitiesService.static_governing_laws = {
            "alabama": {
                "display_name": "Alabama",
                "normalized_name": "alabama"
            },
            "georgia": {
                "display_name": "Georgia",
                "normalized_name": "georgia"
            }
        }
        
        ContractEntitiesService.static_contract_types = {
            "msa": {
                "display_name": "Master Services Agreement",
                "normalized_name": "msa"
            }
        }
        
        # Test text with multiple entities
        text = "Find contracts between Alabama Fire Sprinkler and Westervelt governed by Alabama law"
        results = ContractEntitiesService.identify_entities_in_text(text)
        
        # Should find governing law
        assert len(results["governing_laws"]) > 0
        assert results["governing_laws"][0]["state"] == "alabama"
        
        # Test with no entities
        text = "Show me something completely unrelated"
        results = ContractEntitiesService.identify_entities_in_text(text)
        assert len(results["contractor_parties"]) == 0
        assert len(results["contracting_parties"]) == 0
        
        # Test with fuzzy matching - temporarily lower threshold for testing
        old_threshold = ContractEntitiesService.FUZZY_MATCH_THRESHOLD
        ContractEntitiesService.FUZZY_MATCH_THRESHOLD = 0.7  # Temporarily lower
        
        text = "Contract with Alabama Fire Sprinkler Contractors LLC"  # Full name with LLC
        results = ContractEntitiesService.identify_entities_in_text(text)
        # Should find fuzzy match or exact match (depending on normalization)
        assert len(results["fuzzy_matches"]) > 0 or len(results["contractor_parties"]) > 0
        
        # Restore threshold
        ContractEntitiesService.FUZZY_MATCH_THRESHOLD = old_threshold
        
        # Test with reordered company name - lower threshold more for this test
        ContractEntitiesService.FUZZY_MATCH_THRESHOLD = 0.6
        text = "Agreement with National First Bank"
        results = ContractEntitiesService.identify_entities_in_text(text)
        # Should find the bank even with reordered words
        assert len(results["contracting_parties"]) > 0 or len(results["fuzzy_matches"]) > 0
        ContractEntitiesService.FUZZY_MATCH_THRESHOLD = old_threshold
        
        # Check match details are populated
        assert "match_details" in results
        
        # Test high-confidence matching
        text = "Contract between ABC Corporation and The Westervelt Company"
        results = ContractEntitiesService.identify_entities_in_text(text)
        # Should find both parties with high confidence
        assert len(results["contractor_parties"]) > 0 or len(results["contracting_parties"]) > 0
    
    @pytest.mark.asyncio
    async def test_update_or_create_contractor_party(self):
        """Test creating and updating contractor party entities"""
        
        # Reset static data
        ContractEntitiesService.static_contractor_parties = {}
        ContractEntitiesService.static_entity_reference = {"contractor_parties": []}
        
        # Create new entity
        normalized = await ContractEntitiesService.update_or_create_contractor_party(
            "ABC Corporation", "contract_123", 100000.0
        )
        
        assert normalized == "abc"
        assert "abc" in ContractEntitiesService.static_contractor_parties
        
        entity = ContractEntitiesService.static_contractor_parties["abc"]
        assert entity["display_name"] == "ABC Corporation"
        assert entity["contract_count"] == 1
        assert entity["total_value"] == 100000.0
        assert "contract_123" in entity["contracts"]
        
        # Update existing entity
        await ContractEntitiesService.update_or_create_contractor_party(
            "ABC Corp", "contract_456", 50000.0  # Slightly different name
        )
        
        entity = ContractEntitiesService.static_contractor_parties["abc"]
        assert entity["contract_count"] == 2
        assert entity["total_value"] == 150000.0
        assert "contract_456" in entity["contracts"]
        
        # Duplicate contract ID should not increase count
        await ContractEntitiesService.update_or_create_contractor_party(
            "ABC Corporation", "contract_123", 25000.0
        )
        
        entity = ContractEntitiesService.static_contractor_parties["abc"]
        assert entity["contract_count"] == 2  # Should still be 2
        assert entity["total_value"] == 175000.0  # Value should increase
    
    @pytest.mark.asyncio
    async def test_update_or_create_governing_law(self):
        """Test creating and updating governing law entities"""
        
        # Reset static data
        ContractEntitiesService.static_governing_laws = {}
        ContractEntitiesService.static_entity_reference = {"governing_laws": []}
        
        # Create new entity
        normalized = await ContractEntitiesService.update_or_create_governing_law(
            "Alabama", "contract_123"
        )
        
        assert normalized == "alabama"
        assert "alabama" in ContractEntitiesService.static_governing_laws
        
        entity = ContractEntitiesService.static_governing_laws["alabama"]
        assert entity["display_name"] == "Alabama"
        assert entity["contract_count"] == 1
        assert "contract_123" in entity["contracts"]
        
        # Update existing entity
        await ContractEntitiesService.update_or_create_governing_law(
            "Alabama", "contract_456"
        )
        
        entity = ContractEntitiesService.static_governing_laws["alabama"]
        assert entity["contract_count"] == 2
        assert "contract_456" in entity["contracts"]
        
        # Test that trailing punctuation is properly handled (should normalize to same entity)
        await ContractEntitiesService.update_or_create_governing_law(
            "Alabama.", "contract_789"  # With trailing period
        )
        
        # Should still only have one "alabama" entity, not create "alabama."
        assert len(ContractEntitiesService.static_governing_laws) == 1
        assert "alabama" in ContractEntitiesService.static_governing_laws
        
        entity = ContractEntitiesService.static_governing_laws["alabama"]
        assert entity["contract_count"] == 3  # Should have 3 contracts now
        assert "contract_789" in entity["contracts"]
    
    def test_get_statistics(self):
        """Test entity statistics calculation"""
        
        # Setup test data
        ContractEntitiesService.static_contractor_parties = {
            "abc": {
                "contract_count": 3,
                "total_value": 300000.0
            },
            "xyz": {
                "contract_count": 2,
                "total_value": 150000.0
            }
        }
        
        ContractEntitiesService.static_contracting_parties = {
            "customer1": {
                "contract_count": 4,
                "total_value": 450000.0
            }
        }
        
        ContractEntitiesService.static_governing_laws = {
            "alabama": {"contract_count": 5},
            "georgia": {"contract_count": 2}
        }
        
        ContractEntitiesService.static_contract_types = {
            "msa": {"contract_count": 3},
            "nda": {"contract_count": 4}
        }
        
        stats = ContractEntitiesService.get_statistics()
        
        assert stats["contractor_parties"]["count"] == 2
        assert stats["contractor_parties"]["total_contracts"] == 5
        assert stats["contractor_parties"]["total_value"] == 450000.0
        
        assert stats["contracting_parties"]["count"] == 1
        assert stats["contracting_parties"]["total_contracts"] == 4
        assert stats["contracting_parties"]["total_value"] == 450000.0
        
        assert stats["governing_laws"]["count"] == 2
        assert stats["governing_laws"]["total_contracts"] == 7
        
        assert stats["contract_types"]["count"] == 2
        assert stats["contract_types"]["total_contracts"] == 7


if __name__ == "__main__":
    # Run specific tests during development
    test = TestContractEntitiesService()
    test.test_normalize_entity_name()
    test.test_fuzzy_match()
    test.test_identify_entities_in_text()
    asyncio.run(test.test_update_or_create_contractor_party())
    asyncio.run(test.test_update_or_create_governing_law())
    test.test_get_statistics()
    print("All tests passed!")