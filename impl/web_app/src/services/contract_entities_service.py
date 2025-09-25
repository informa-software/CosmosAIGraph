import datetime
import logging
import time
import traceback
from typing import Dict, List, Set, Optional, Tuple
from difflib import SequenceMatcher
import re

# Advanced string matching libraries
try:
    import jellyfish
    JELLYFISH_AVAILABLE = True
except ImportError:
    JELLYFISH_AVAILABLE = False
    logging.warning("jellyfish library not available - using basic matching only")

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.util.counter import Counter

# Service for managing contract-related entities:
# - Contractor Parties
# - Contracting Parties  
# - Governing Law States
# - Contract Types
#
# This service maintains separate entity collections and provides
# entity identification, normalization, and statistics tracking.
#
# TODO: Implement more sophisticated matching algorithms:
# - Consider using phonetic matching (Soundex, Metaphone) for company names
# - Implement n-gram similarity for partial matches
# - Add domain-specific abbreviation expansion (LLC, Corp, Inc, etc.)
# - Consider ML-based entity resolution for complex cases
#
# Chris Joakim & David Ambrose, Microsoft, 2025


class ContractEntitiesService:
    
    # Class variables for caching entities in memory
    static_contractor_parties = dict()  # normalized_name -> entity_doc
    static_contracting_parties = dict()  # normalized_name -> entity_doc
    static_governing_laws = dict()  # state_name -> entity_doc
    static_contract_types = dict()  # type_name -> entity_doc
    static_entity_reference = dict()  # The reference document with all entity lists
    static_initialized = False
    
    # Fuzzy matching threshold (0.0 to 1.0)
    FUZZY_MATCH_THRESHOLD = 0.85
    
    # Company suffix patterns to remove for matching
    # Note: Be careful with short suffixes that might be part of other words
    COMPANY_SUFFIXES = [
        'llc', 'l.l.c.', 'inc', 'incorporated', 'corp', 'corporation',
        'company', 'co', 'ltd', 'limited', 'plc', 'p.l.c.', 'llp',
        'l.l.p.', 'lp', 'l.p.', 'partners', 'partnership', 'group',
        'holdings', 'holding', 'enterprises', 'intl', 'international'
        # Removed 'ent' as it's too generic and matches words like 'agreement', 'statement', etc.
    ]
    
    @classmethod
    async def initialize(cls, force_reinitialize=False):
        """
        Initialize the service by loading all contract entities from CosmosDB.
        Entities are cached in memory for fast lookup.
        """
        logging.warning(
            f"ContractEntitiesService#initialize - force_reinitialize: {force_reinitialize}"
        )
        
        # Skip if already initialized unless forced
        if cls.static_initialized and not force_reinitialize:
            logging.info("ContractEntitiesService already initialized, skipping")
            return
            
        # Reset all static collections
        cls.static_contractor_parties = dict()
        cls.static_contracting_parties = dict()
        cls.static_governing_laws = dict()
        cls.static_contract_types = dict()
        cls.static_entity_reference = dict()
        
        try:
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            db_name = ConfigService.graph_source_db()
            
            # Load the entity reference document from config container
            nosql_svc.set_db(db_name)
            nosql_svc.set_container(ConfigService.config_container())
            
            try:
                cls.static_entity_reference = await nosql_svc.point_read(
                    "contract_entities", "contract_entities"
                )
                logging.info("Loaded contract_entities reference document")
            except Exception as e:
                logging.warning(f"No contract_entities reference document found: {e}")
                # Initialize with empty structure
                cls.static_entity_reference = {
                    "id": "contract_entities",
                    "pk": "contract_entities",
                    "contractor_parties": [],
                    "contracting_parties": [],
                    "governing_laws": [],
                    "contract_types": []
                }
            
            # Load contractor parties from their container
            nosql_svc.set_container("contractor_parties")
            contractor_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_contractor_parties, "contractor_parties"
            )
            
            # Load contracting parties from their container
            nosql_svc.set_container("contracting_parties")
            contracting_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_contracting_parties, "contracting_parties"
            )
            
            # Load governing laws from their container
            nosql_svc.set_container("governing_laws")
            governing_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_governing_laws, "governing_laws"
            )
            
            # Load contract types from their container
            nosql_svc.set_container("contract_types")
            types_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_contract_types, "contract_types"
            )
            
            logging.warning(
                f"ContractEntitiesService initialized - "
                f"Contractor Parties: {contractor_count}, "
                f"Contracting Parties: {contracting_count}, "
                f"Governing Laws: {governing_count}, "
                f"Contract Types: {types_count}"
            )
            
            cls.static_initialized = True
            await nosql_svc.close()
            
        except Exception as e:
            logging.error(f"Error initializing ContractEntitiesService: {str(e)}")
            logging.error(traceback.format_exc())
    
    @classmethod
    async def _load_entities_from_container(cls, nosql_svc, target_dict, container_name):
        """
        Load all entities from a specific container into the target dictionary.
        Returns the count of entities loaded.
        """
        count = 0
        try:
            # Query all documents in the container
            query = f"SELECT * FROM c WHERE c.pk = '{container_name}'"
            results = await nosql_svc.query_items(query)
            
            for doc in results:
                # Store by normalized name for fast lookup
                normalized_name = doc.get("normalized_name", doc.get("id", ""))
                target_dict[normalized_name] = doc
                count += 1
                
        except Exception as e:
            logging.warning(f"Container {container_name} may not exist yet: {e}")
            
        return count
    
    @classmethod
    def normalize_entity_name(cls, name: str) -> str:
        """
        Normalize an entity name for consistent storage and matching.
        Removes special characters, converts to lowercase, removes extra spaces,
        and handles common business entity suffixes.
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
        
        # Remove trailing common suffixes for matching (but keep in display name)
        # Build pattern from COMPANY_SUFFIXES list, handling both with and without underscores
        for suffix in cls.COMPANY_SUFFIXES:
            # Remove suffix with underscore before it
            normalized = re.sub(rf'_{re.escape(suffix)}$', '', normalized)
            # Also remove if suffix appears at the end without underscore (for cases like "inc")
            normalized = re.sub(rf'{re.escape(suffix)}$', '', normalized)
        
        # Clean up any trailing underscores that might be left
        normalized = re.sub(r'_+$', '', normalized)
        
        # Also remove leading "the" which is common in company names
        normalized = re.sub(r'^the_', '', normalized)
        
        return normalized
    
    @classmethod
    def token_similarity(cls, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity between two texts based on word tokens.
        Good for handling reordered words in company names.
        """
        if not text1 or not text2:
            return 0.0
            
        # Tokenize into words
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
            
        # Jaccard similarity: intersection / union
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    @classmethod
    def hybrid_company_match(cls, name1: str, name2: str) -> Tuple[float, str]:
        """
        Hybrid matching approach specifically designed for company names.
        Combines multiple matching techniques for best accuracy.
        
        Returns:
            Tuple of (similarity_score, matching_method_used)
        """
        if not name1 or not name2:
            return 0.0, "empty"
            
        # Step 1: Normalize both names
        norm1 = cls.normalize_entity_name(name1)
        norm2 = cls.normalize_entity_name(name2)
        
        # Step 2: Check exact match after normalization
        if norm1 == norm2:
            return 1.0, "exact_normalized"
        
        # Step 3: Calculate multiple similarity scores
        scores = {}
        
        # Jaro-Winkler (best for company names with similar prefixes)
        if JELLYFISH_AVAILABLE:
            try:
                jw_score = jellyfish.jaro_winkler_similarity(norm1, norm2)
                scores['jaro_winkler'] = jw_score
            except Exception as e:
                logging.debug(f"Jaro-Winkler error: {e}")
                scores['jaro_winkler'] = 0.0
        else:
            # Fallback to SequenceMatcher if jellyfish not available
            scores['sequence'] = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Token-based similarity (handles word reordering)
        token_score = cls.token_similarity(name1, name2)
        scores['token'] = token_score
        
        # Step 4: Check phonetic similarity for bonus points
        phonetic_bonus = 0.0
        if JELLYFISH_AVAILABLE:
            try:
                # Use Metaphone for phonetic matching
                meta1 = jellyfish.metaphone(norm1)
                meta2 = jellyfish.metaphone(norm2)
                if meta1 and meta2 and meta1 == meta2:
                    phonetic_bonus = 0.1  # Add 10% bonus for phonetic match
            except Exception as e:
                logging.debug(f"Metaphone error: {e}")
        
        # Step 5: Calculate weighted final score
        if 'jaro_winkler' in scores:
            # Prefer Jaro-Winkler when available (70% weight)
            final_score = (scores['jaro_winkler'] * 0.7) + (scores['token'] * 0.3)
            method = f"hybrid_jw_{scores['jaro_winkler']:.2f}_tok_{scores['token']:.2f}"
        else:
            # Use SequenceMatcher as fallback (60% weight)
            final_score = (scores['sequence'] * 0.6) + (scores['token'] * 0.4)
            method = f"hybrid_seq_{scores['sequence']:.2f}_tok_{scores['token']:.2f}"
        
        # Add phonetic bonus (capped at 1.0)
        final_score = min(1.0, final_score + phonetic_bonus)
        if phonetic_bonus > 0:
            method += "_phonetic"
        
        return final_score, method
    
    @classmethod
    def fuzzy_match(cls, text1: str, text2: str) -> float:
        """
        Calculate similarity between two strings using the hybrid approach.
        This is the main entry point for fuzzy matching company names.
        Returns a score between 0.0 and 1.0.
        """
        if not text1 or not text2:
            return 0.0
            
        # Use hybrid matching for company names
        score, _ = cls.hybrid_company_match(text1, text2)
        return score
    
    @classmethod
    def identify_entities_in_text(cls, text: str) -> Dict:
        """
        Identify contract entities in the given text using hybrid matching.
        Returns a dictionary with lists of identified entities by type.
        Includes detailed confidence scores and matching methods.
        """
        results = {
            "contractor_parties": [],
            "contracting_parties": [],
            "governing_laws": [],
            "contract_types": [],
            "fuzzy_matches": [],  # Entities that matched with lower confidence
            "match_details": []  # Detailed information about all matches
        }
        
        if not text:
            return results
            
        text_lower = text.lower()
        
        # Check contractor parties with hybrid matching
        for normalized_name, entity in cls.static_contractor_parties.items():
            display_name = entity.get("display_name", "")
            
            # Exact match on normalized name
            if normalized_name in text_lower:
                results["contractor_parties"].append({
                    "normalized_name": normalized_name,
                    "display_name": display_name,
                    "confidence": 1.0,
                    "match_type": "exact_normalized"
                })
            # Use hybrid matching for better accuracy
            elif display_name:
                score, method = cls.hybrid_company_match(display_name, text)
                if score >= cls.FUZZY_MATCH_THRESHOLD:
                    match_info = {
                        "type": "contractor_party",
                        "normalized_name": normalized_name,
                        "display_name": display_name,
                        "confidence": score,
                        "match_method": method
                    }
                    
                    # Add to high confidence matches if score is very high
                    if score >= 0.95:
                        results["contractor_parties"].append(match_info)
                    else:
                        results["fuzzy_matches"].append(match_info)
                    
                    # Always add to match details for debugging
                    results["match_details"].append(match_info)
        
        # Check contracting parties with hybrid matching
        for normalized_name, entity in cls.static_contracting_parties.items():
            display_name = entity.get("display_name", "")
            
            if normalized_name in text_lower:
                results["contracting_parties"].append({
                    "normalized_name": normalized_name,
                    "display_name": display_name,
                    "confidence": 1.0,
                    "match_type": "exact_normalized"
                })
            elif display_name:
                score, method = cls.hybrid_company_match(display_name, text)
                if score >= cls.FUZZY_MATCH_THRESHOLD:
                    match_info = {
                        "type": "contracting_party",
                        "normalized_name": normalized_name,
                        "display_name": display_name,
                        "confidence": score,
                        "match_method": method
                    }
                    
                    # Add to high confidence matches if score is very high
                    if score >= 0.95:
                        results["contracting_parties"].append(match_info)
                    else:
                        results["fuzzy_matches"].append(match_info)
                    
                    results["match_details"].append(match_info)
        
        # Check governing laws (usually state names, more straightforward)
        for state_name, entity in cls.static_governing_laws.items():
            if state_name in text_lower:
                results["governing_laws"].append({
                    "state": state_name,
                    "display_name": entity.get("display_name", state_name),
                    "confidence": 1.0,
                    "match_type": "exact"
                })
        
        # Check contract types
        for type_name, entity in cls.static_contract_types.items():
            if type_name in text_lower:
                results["contract_types"].append({
                    "type": type_name,
                    "display_name": entity.get("display_name", type_name),
                    "confidence": 1.0,
                    "match_type": "exact"
                })
        
        return results
    
    @classmethod
    async def update_or_create_contractor_party(cls, party_name: str, contract_id: str, 
                                               contract_value: float = 0.0) -> str:
        """
        Update an existing contractor party or create a new one.
        Returns the normalized name of the entity.
        """
        normalized_name = cls.normalize_entity_name(party_name)
        
        if normalized_name in cls.static_contractor_parties:
            # Update existing entity
            entity = cls.static_contractor_parties[normalized_name]
            if contract_id not in entity.get("contracts", []):
                entity["contracts"].append(contract_id)
            entity["total_value"] = entity.get("total_value", 0) + contract_value
            entity["contract_count"] = len(entity["contracts"])
            entity["updated_at"] = time.time()
        else:
            # Create new entity
            entity = {
                "id": normalized_name,
                "pk": "contractor_parties",
                "normalized_name": normalized_name,
                "display_name": party_name,
                "contracts": [contract_id],
                "contract_count": 1,
                "total_value": contract_value,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            cls.static_contractor_parties[normalized_name] = entity
            
            # Update reference document
            if normalized_name not in cls.static_entity_reference.get("contractor_parties", []):
                cls.static_entity_reference.setdefault("contractor_parties", []).append(normalized_name)
        
        return normalized_name
    
    @classmethod
    async def update_or_create_contracting_party(cls, party_name: str, contract_id: str,
                                                contract_value: float = 0.0) -> str:
        """
        Update an existing contracting party or create a new one.
        Returns the normalized name of the entity.
        """
        normalized_name = cls.normalize_entity_name(party_name)
        
        if normalized_name in cls.static_contracting_parties:
            # Update existing entity
            entity = cls.static_contracting_parties[normalized_name]
            if contract_id not in entity.get("contracts", []):
                entity["contracts"].append(contract_id)
            entity["total_value"] = entity.get("total_value", 0) + contract_value
            entity["contract_count"] = len(entity["contracts"])
            entity["updated_at"] = time.time()
        else:
            # Create new entity
            entity = {
                "id": normalized_name,
                "pk": "contracting_parties",
                "normalized_name": normalized_name,
                "display_name": party_name,
                "contracts": [contract_id],
                "contract_count": 1,
                "total_value": contract_value,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            cls.static_contracting_parties[normalized_name] = entity
            
            # Update reference document
            if normalized_name not in cls.static_entity_reference.get("contracting_parties", []):
                cls.static_entity_reference.setdefault("contracting_parties", []).append(normalized_name)
        
        return normalized_name
    
    @classmethod
    async def update_or_create_governing_law(cls, state_name: str, contract_id: str) -> str:
        """
        Update an existing governing law or create a new one.
        Returns the normalized state name.
        """
        # Use the full normalization function to handle punctuation and special characters
        normalized_name = cls.normalize_entity_name(state_name)
        
        if normalized_name in cls.static_governing_laws:
            # Update existing entity
            entity = cls.static_governing_laws[normalized_name]
            if contract_id not in entity.get("contracts", []):
                entity["contracts"].append(contract_id)
            entity["contract_count"] = len(entity["contracts"])
            entity["updated_at"] = time.time()
        else:
            # Create new entity
            entity = {
                "id": normalized_name,
                "pk": "governing_laws",
                "normalized_name": normalized_name,
                "display_name": state_name,
                "contracts": [contract_id],
                "contract_count": 1,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            cls.static_governing_laws[normalized_name] = entity
            
            # Update reference document
            if normalized_name not in cls.static_entity_reference.get("governing_laws", []):
                cls.static_entity_reference.setdefault("governing_laws", []).append(normalized_name)
        
        return normalized_name
    
    @classmethod
    async def update_or_create_contract_type(cls, type_name: str, contract_id: str) -> str:
        """
        Update an existing contract type or create a new one.
        Returns the normalized type name.
        """
        normalized_name = cls.normalize_entity_name(type_name)
        
        if normalized_name in cls.static_contract_types:
            # Update existing entity
            entity = cls.static_contract_types[normalized_name]
            if contract_id not in entity.get("contracts", []):
                entity["contracts"].append(contract_id)
            entity["contract_count"] = len(entity["contracts"])
            entity["updated_at"] = time.time()
        else:
            # Create new entity
            entity = {
                "id": normalized_name,
                "pk": "contract_types",
                "normalized_name": normalized_name,
                "display_name": type_name,
                "contracts": [contract_id],
                "contract_count": 1,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            cls.static_contract_types[normalized_name] = entity
            
            # Update reference document
            if normalized_name not in cls.static_entity_reference.get("contract_types", []):
                cls.static_entity_reference.setdefault("contract_types", []).append(normalized_name)
        
        return normalized_name
    
    @classmethod
    async def persist_entities(cls):
        """
        Persist all in-memory entities back to CosmosDB.
        Should be called after batch loading contracts.
        """
        logging.info("Persisting contract entities to CosmosDB")
        
        try:
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            db_name = ConfigService.graph_source_db()
            nosql_svc.set_db(db_name)
            
            # Persist contractor parties
            nosql_svc.set_container("contractor_parties")
            for entity in cls.static_contractor_parties.values():
                await nosql_svc.upsert_item(entity)
            
            # Persist contracting parties
            nosql_svc.set_container("contracting_parties")
            for entity in cls.static_contracting_parties.values():
                await nosql_svc.upsert_item(entity)
            
            # Persist governing laws
            nosql_svc.set_container("governing_laws")
            for entity in cls.static_governing_laws.values():
                await nosql_svc.upsert_item(entity)
            
            # Persist contract types
            nosql_svc.set_container("contract_types")
            for entity in cls.static_contract_types.values():
                await nosql_svc.upsert_item(entity)
            
            # Persist the reference document
            nosql_svc.set_container(ConfigService.config_container())
            cls.static_entity_reference["updated_at"] = time.time()
            await nosql_svc.upsert_item(cls.static_entity_reference)
            
            await nosql_svc.close()
            logging.info("Successfully persisted all contract entities")
            
        except Exception as e:
            logging.error(f"Error persisting entities: {str(e)}")
            logging.error(traceback.format_exc())
    
    @classmethod
    def get_statistics(cls) -> Dict:
        """
        Get statistics about the loaded entities.
        """
        return {
            "contractor_parties": {
                "count": len(cls.static_contractor_parties),
                "total_contracts": sum(e.get("contract_count", 0) for e in cls.static_contractor_parties.values()),
                "total_value": sum(e.get("total_value", 0) for e in cls.static_contractor_parties.values())
            },
            "contracting_parties": {
                "count": len(cls.static_contracting_parties),
                "total_contracts": sum(e.get("contract_count", 0) for e in cls.static_contracting_parties.values()),
                "total_value": sum(e.get("total_value", 0) for e in cls.static_contracting_parties.values())
            },
            "governing_laws": {
                "count": len(cls.static_governing_laws),
                "total_contracts": sum(e.get("contract_count", 0) for e in cls.static_governing_laws.values())
            },
            "contract_types": {
                "count": len(cls.static_contract_types),
                "total_contracts": sum(e.get("contract_count", 0) for e in cls.static_contract_types.values())
            }
        }