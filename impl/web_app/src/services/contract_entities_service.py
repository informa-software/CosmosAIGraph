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

logger = logging.getLogger(__name__)

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
    static_governing_law_states = dict()  # state_name -> entity_doc
    static_contract_types = dict()  # type_name -> entity_doc
    static_clause_types = dict()  # normalized_name -> entity_doc
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
        cls.static_governing_law_states = dict()
        cls.static_contract_types = dict()
        cls.static_clause_types = dict()
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
                    "governing_laws_states": [],
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
            nosql_svc.set_container("governing_law_states")
            governing_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_governing_law_states, "governing_law_states"
            )
            
            # Load contract types from their container
            nosql_svc.set_container("contract_types")
            types_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_contract_types, "contract_types"
            )
            
            # Load clause types from their container
            nosql_svc.set_container("clause_types")
            clause_count = await cls._load_entities_from_container(
                nosql_svc, cls.static_clause_types, "clause_types"
            )
            
            # If no clause types exist, initialize with defaults
            if clause_count == 0:
                await cls._initialize_clause_types(nosql_svc)
                clause_count = len(cls.static_clause_types)
            
            logging.warning(
                f"ContractEntitiesService initialized - "
                f"Contractor Parties: {contractor_count}, "
                f"Contracting Parties: {contracting_count}, "
                f"Governing Law States: {governing_count}, "
                f"Contract Types: {types_count}, "
                f"Clause Types: {clause_count}"
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
    def all_tokens_present(cls, input_text: str, entity_name: str) -> bool:
        """
        Check if all meaningful tokens from input are present in entity name.
        Filters out common suffixes and short words.
        """
        # Get input tokens (normalized)
        input_tokens = set(cls.normalize_entity_name(input_text).split('_'))

        # Filter out very short tokens (like 'co', 'inc') which are common suffixes
        input_tokens = {t for t in input_tokens if len(t) > 2}

        # Get entity tokens (normalized)
        entity_tokens = set(cls.normalize_entity_name(entity_name).split('_'))

        # Check if all input tokens are in entity tokens
        return input_tokens.issubset(entity_tokens)

    @classmethod
    def identify_entities_in_text(cls, text: str) -> Dict:
        """
        Identify contract entities in the given text using hybrid matching.
        Returns a dictionary with lists of identified entities by type.
        Includes detailed confidence scores and matching methods.

        Enhanced to prefer:
        1. Entities containing ALL input tokens
        2. Longer entity names when confidence is similar
        3. Complete matches over partial matches
        """
        results = {
            "contractor_parties": [],
            "contracting_parties": [],
            "governing_law_states": [],
            "contract_types": [],
            "fuzzy_matches": [],  # Entities that matched with lower confidence
            "match_details": [],  # Detailed information about all matches
            "debug_all_scores": []  # ALL entity comparisons for debugging (even below threshold)
        }

        if not text:
            return results

        text_lower = text.lower()

        # Check contractor parties with hybrid matching
        all_contractor_matches = []
        # Normalize the input text for comparison
        normalized_input = cls.normalize_entity_name(text)

        # Debug: Track all entity comparisons
        logger.warning(f"[ENTITY MATCHING] Searching for '{text}' (normalized: '{normalized_input}') in contractor_parties")
        logger.warning(f"[ENTITY MATCHING] Total contractor_parties in database: {len(cls.static_contractor_parties)}")

        for normalized_name, entity in cls.static_contractor_parties.items():
            display_name = entity.get("display_name", "")

            # Exact match: compare normalized input to normalized entity name
            if normalized_input == normalized_name:
                match_info = {
                    "normalized_name": normalized_name,
                    "display_name": display_name,
                    "confidence": 1.0,
                    "match_type": "exact_normalized",
                    "token_completeness": 1.0,
                    "length": len(normalized_name)
                }
                all_contractor_matches.append(match_info)
                results["debug_all_scores"].append(match_info)
            # Use hybrid matching for better accuracy
            elif display_name:
                score, method = cls.hybrid_company_match(display_name, text)

                # Check if all input tokens are present
                has_all_tokens = cls.all_tokens_present(text, display_name)
                token_bonus = 0.1 if has_all_tokens else 0.0

                # Add length preference (longer names get slight bonus)
                length_bonus = min(0.05, len(normalized_name) / 1000.0)

                # Adjust score with bonuses
                adjusted_score = min(1.0, score + token_bonus + length_bonus)

                match_info = {
                    "type": "contractor_party",
                    "normalized_name": normalized_name,
                    "display_name": display_name,
                    "confidence": adjusted_score,
                    "original_score": score,
                    "match_method": method,
                    "has_all_tokens": has_all_tokens,
                    "token_completeness": 1.0 if has_all_tokens else 0.5,
                    "length": len(normalized_name)
                }

                # Add to debug list (ALL comparisons, even below threshold)
                results["debug_all_scores"].append(match_info)

                # Only add to matches if above threshold
                if score >= cls.FUZZY_MATCH_THRESHOLD:
                    all_contractor_matches.append(match_info)
                    results["match_details"].append(match_info)

        # Sort contractor matches by: token_completeness desc, confidence desc, length desc
        all_contractor_matches.sort(
            key=lambda m: (m.get("token_completeness", 0), m["confidence"], m["length"]),
            reverse=True
        )

        # Categorize based on FUZZY_MATCH_THRESHOLD (0.85)
        # Matches above threshold go to main collection, below go to fuzzy_matches
        for match in all_contractor_matches:
            if match.get("original_score", match["confidence"]) >= cls.FUZZY_MATCH_THRESHOLD:
                results["contractor_parties"].append(match)
            else:
                results["fuzzy_matches"].append(match)
        
        # Check contracting parties with hybrid matching
        all_contracting_matches = []

        # Debug: Track all entity comparisons
        logger.warning(f"[ENTITY MATCHING] Searching for '{text}' (normalized: '{normalized_input}') in contracting_parties")
        logger.warning(f"[ENTITY MATCHING] Total contracting_parties in database: {len(cls.static_contracting_parties)}")

        for normalized_name, entity in cls.static_contracting_parties.items():
            display_name = entity.get("display_name", "")

            # Exact match: compare normalized input to normalized entity name
            if normalized_input == normalized_name:
                match_info = {
                    "normalized_name": normalized_name,
                    "display_name": display_name,
                    "confidence": 1.0,
                    "match_type": "exact_normalized",
                    "token_completeness": 1.0,
                    "length": len(normalized_name)
                }
                all_contracting_matches.append(match_info)
                results["debug_all_scores"].append(match_info)
            # Use hybrid matching for better accuracy
            elif display_name:
                score, method = cls.hybrid_company_match(display_name, text)

                # Check if all input tokens are present
                has_all_tokens = cls.all_tokens_present(text, display_name)
                token_bonus = 0.1 if has_all_tokens else 0.0

                # Add length preference (longer names get slight bonus)
                length_bonus = min(0.05, len(normalized_name) / 1000.0)

                # Adjust score with bonuses
                adjusted_score = min(1.0, score + token_bonus + length_bonus)

                match_info = {
                    "type": "contracting_party",
                    "normalized_name": normalized_name,
                    "display_name": display_name,
                    "confidence": adjusted_score,
                    "original_score": score,
                    "match_method": method,
                    "has_all_tokens": has_all_tokens,
                    "token_completeness": 1.0 if has_all_tokens else 0.5,
                    "length": len(normalized_name)
                }

                # Add to debug list (ALL comparisons, even below threshold)
                results["debug_all_scores"].append(match_info)

                # Only add to matches if above threshold
                if score >= cls.FUZZY_MATCH_THRESHOLD:
                    all_contracting_matches.append(match_info)
                    results["match_details"].append(match_info)

        # Sort contracting matches by: token_completeness desc, confidence desc, length desc
        all_contracting_matches.sort(
            key=lambda m: (m.get("token_completeness", 0), m["confidence"], m["length"]),
            reverse=True
        )

        # Categorize based on FUZZY_MATCH_THRESHOLD (0.85)
        # Matches above threshold go to main collection, below go to fuzzy_matches
        for match in all_contracting_matches:
            if match.get("original_score", match["confidence"]) >= cls.FUZZY_MATCH_THRESHOLD:
                results["contracting_parties"].append(match)
            else:
                results["fuzzy_matches"].append(match)
        
        # Check governing laws (states) - use same fuzzy matching as parties
        all_state_matches = []
        for state_name, entity in cls.static_governing_law_states.items():
            display_name = entity.get("display_name", state_name)

            # Normalize the input text for comparison
            normalized_input = cls.normalize_entity_name(text)

            # Exact match: compare normalized input to normalized state name
            if normalized_input == state_name:
                match_info = {
                    "normalized_name": state_name,
                    "display_name": display_name,
                    "confidence": 1.0,
                    "match_type": "exact_normalized",
                    "type": "governing_law_state",
                    "token_completeness": 1.0,
                    "length": len(state_name)
                }
                all_state_matches.append(match_info)
                results["debug_all_scores"].append(match_info)
                continue

            # Fuzzy match: use Jaro-Winkler for display name matching
            if JELLYFISH_AVAILABLE:
                try:
                    similarity = jellyfish.jaro_winkler_similarity(text.lower(), display_name.lower())
                except Exception as e:
                    logger.debug(f"Jaro-Winkler error for states: {e}")
                    similarity = SequenceMatcher(None, text.lower(), display_name.lower()).ratio()
            else:
                similarity = SequenceMatcher(None, text.lower(), display_name.lower()).ratio()

            if similarity > 0:  # Add all comparisons to debug
                # Token-based matching: does text contain all major tokens?
                text_tokens = set(text.lower().split())
                display_tokens = set(display_name.lower().split())

                # Remove common words
                common_words = {"the", "of", "and", "for", "state"}
                display_tokens = display_tokens - common_words
                text_tokens = text_tokens - common_words

                # Check if all display tokens are in text
                all_tokens_present = len(display_tokens) > 0 and display_tokens.issubset(text_tokens)
                token_completeness = len(display_tokens.intersection(text_tokens)) / len(display_tokens) if len(display_tokens) > 0 else 0

                # Boost confidence if all tokens present
                adjusted_confidence = similarity
                if all_tokens_present:
                    adjusted_confidence = min(1.0, similarity + 0.15)

                # Boost for longer matches
                if len(state_name) > 10:
                    adjusted_confidence = min(1.0, adjusted_confidence + 0.05)

                match_info = {
                    "normalized_name": state_name,
                    "display_name": display_name,
                    "confidence": adjusted_confidence,
                    "original_score": similarity,
                    "match_type": "fuzzy",
                    "type": "governing_law_state",
                    "has_all_tokens": all_tokens_present,
                    "token_completeness": token_completeness,
                    "length": len(state_name)
                }

                all_state_matches.append(match_info)
                # Add to debug list (ALL comparisons, even below threshold)
                results["debug_all_scores"].append(match_info)

        # Sort state matches by: token_completeness desc, confidence desc, length desc
        all_state_matches.sort(
            key=lambda m: (m.get("token_completeness", 0), m["confidence"], m["length"]),
            reverse=True
        )

        # Categorize based on FUZZY_MATCH_THRESHOLD (0.85)
        for match in all_state_matches:
            if match.get("original_score", match["confidence"]) >= cls.FUZZY_MATCH_THRESHOLD:
                results["governing_law_states"].append(match)
            else:
                results["fuzzy_matches"].append(match)
        
        # Check contract types - use same fuzzy matching as parties
        all_type_matches = []
        for type_name, entity in cls.static_contract_types.items():
            display_name = entity.get("display_name", type_name)

            # Normalize the input text for comparison
            normalized_input = cls.normalize_entity_name(text)

            # Exact match: compare normalized input to normalized type name
            if normalized_input == type_name:
                match_info = {
                    "normalized_name": type_name,
                    "display_name": display_name,
                    "confidence": 1.0,
                    "match_type": "exact_normalized",
                    "type": "contract_type",
                    "token_completeness": 1.0,
                    "length": len(type_name)
                }
                all_type_matches.append(match_info)
                results["debug_all_scores"].append(match_info)
                continue

            # Fuzzy match: use Jaro-Winkler for display name matching
            if JELLYFISH_AVAILABLE:
                try:
                    similarity = jellyfish.jaro_winkler_similarity(text.lower(), display_name.lower())
                except Exception as e:
                    logger.debug(f"Jaro-Winkler error for contract types: {e}")
                    similarity = SequenceMatcher(None, text.lower(), display_name.lower()).ratio()
            else:
                similarity = SequenceMatcher(None, text.lower(), display_name.lower()).ratio()

            if similarity > 0:  # Add all comparisons to debug
                # Token-based matching: does text contain all major tokens?
                text_tokens = set(text.lower().split())
                display_tokens = set(display_name.lower().split())

                # Remove common words
                common_words = {"the", "of", "and", "for", "agreement", "contract"}
                display_tokens = display_tokens - common_words
                text_tokens = text_tokens - common_words

                # Check if all display tokens are in text
                all_tokens_present = len(display_tokens) > 0 and display_tokens.issubset(text_tokens)
                token_completeness = len(display_tokens.intersection(text_tokens)) / len(display_tokens) if len(display_tokens) > 0 else 0

                # Boost confidence if all tokens present
                adjusted_confidence = similarity
                if all_tokens_present:
                    adjusted_confidence = min(1.0, similarity + 0.15)

                # Boost for longer matches
                if len(type_name) > 5:
                    adjusted_confidence = min(1.0, adjusted_confidence + 0.05)

                match_info = {
                    "normalized_name": type_name,
                    "display_name": display_name,
                    "confidence": adjusted_confidence,
                    "original_score": similarity,
                    "match_type": "fuzzy",
                    "type": "contract_type",
                    "has_all_tokens": all_tokens_present,
                    "token_completeness": token_completeness,
                    "length": len(type_name)
                }

                all_type_matches.append(match_info)
                # Add to debug list (ALL comparisons, even below threshold)
                results["debug_all_scores"].append(match_info)

        # Sort type matches by: token_completeness desc, confidence desc, length desc
        all_type_matches.sort(
            key=lambda m: (m.get("token_completeness", 0), m["confidence"], m["length"]),
            reverse=True
        )

        # Categorize based on FUZZY_MATCH_THRESHOLD (0.85)
        for match in all_type_matches:
            if match.get("original_score", match["confidence"]) >= cls.FUZZY_MATCH_THRESHOLD:
                results["contract_types"].append(match)
            else:
                results["fuzzy_matches"].append(match)

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
    async def update_or_create_governing_law_state(cls, state_name: str, contract_id: str) -> str:
        """
        Update an existing governing law or create a new one.
        Returns the normalized state name.
        """
        # Use the full normalization function to handle punctuation and special characters
        normalized_name = cls.normalize_entity_name(state_name)
        
        if normalized_name in cls.static_governing_law_states:
            # Update existing entity
            entity = cls.static_governing_law_states[normalized_name]
            if contract_id not in entity.get("contracts", []):
                entity["contracts"].append(contract_id)
            entity["contract_count"] = len(entity["contracts"])
            entity["updated_at"] = time.time()
        else:
            # Create new entity
            entity = {
                "id": normalized_name,
                "pk": "governing_law_states",
                "normalized_name": normalized_name,
                "display_name": state_name,
                "contracts": [contract_id],
                "contract_count": 1,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            cls.static_governing_law_states[normalized_name] = entity
            
            # Update reference document
            if normalized_name not in cls.static_entity_reference.get("governing_law_states", []):
                cls.static_entity_reference.setdefault("governing_law_states", []).append(normalized_name)
        
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
            nosql_svc.set_container("governing_law_states")
            for entity in cls.static_governing_law_states.values():
                await nosql_svc.upsert_item(entity)
            
            # Persist contract types
            nosql_svc.set_container("contract_types")
            for entity in cls.static_contract_types.values():
                await nosql_svc.upsert_item(entity)
            
            # Note: Clause types are NOT persisted here as they are static reference data
            # They are only initialized once and don't change during contract processing
            
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
            "governing_law_states": {
                "count": len(cls.static_governing_law_states),
                "total_contracts": sum(e.get("contract_count", 0) for e in cls.static_governing_law_states.values())
            },
            "contract_types": {
                "count": len(cls.static_contract_types),
                "total_contracts": sum(e.get("contract_count", 0) for e in cls.static_contract_types.values())
            },
            "clause_types": {
                "count": len(cls.static_clause_types),
                "categories": len(set(e.get("category", "") for e in cls.static_clause_types.values()))
            }
        }
    
    @classmethod
    def get_contractor_parties_catalog(cls) -> Dict:
        """
        Get the catalog of contractor parties.
        Returns a dictionary of normalized_name -> entity_doc.
        """
        return cls.static_contractor_parties.copy()
    
    @classmethod
    def get_contracting_parties_catalog(cls) -> Dict:
        """
        Get the catalog of contracting parties.
        Returns a dictionary of normalized_name -> entity_doc.
        """
        return cls.static_contracting_parties.copy()
    
    @classmethod
    def get_governing_law_states_catalog(cls) -> Dict:
        """
        Get the catalog of governing law states.
        Returns a dictionary of normalized_name -> entity_doc.
        """
        return cls.static_governing_law_states.copy()
    
    @classmethod
    def get_contract_types_catalog(cls) -> Dict:
        """
        Get the catalog of contract types.
        Returns a dictionary of normalized_name -> entity_doc.
        """
        return cls.static_contract_types.copy()
    
    @classmethod
    def get_clause_types_catalog(cls) -> Dict:
        """
        Get the catalog of clause types.
        Returns a dictionary of normalized_name -> entity_doc.
        """
        return cls.static_clause_types.copy()
    
    @classmethod
    async def _initialize_clause_types(cls, nosql_svc):
        """
        Initialize the default clause types in the database.
        These are static reference data that don't change during contract processing.
        """
        logging.info("Initializing default clause types")
        
        # Define default clause types matching CLAUSE_FIELDS from main_contracts.py
        default_clause_types = [
            {
                "type": "Indemnification",
                "displayName": "Indemnification",
                "icon": "shield",
                "description": "Protection against losses and damages",
                "category": "liability"
            },
            {
                "type": "IndemnificationObligations",
                "displayName": "Indemnification Obligations",
                "icon": "security",
                "description": "Specific indemnity obligations",
                "category": "liability"
            },
            {
                "type": "WorkersCompensationInsurance",
                "displayName": "Workers Compensation Insurance",
                "icon": "medical_services",
                "description": "Workers compensation insurance requirements",
                "category": "insurance"
            },
            {
                "type": "CommercialPublicLiability",
                "displayName": "Commercial Public Liability",
                "icon": "public",
                "description": "Commercial public liability insurance",
                "category": "insurance"
            },
            {
                "type": "AutomobileInsurance",
                "displayName": "Automobile Insurance",
                "icon": "directions_car",
                "description": "Vehicle and automobile insurance requirements",
                "category": "insurance"
            },
            {
                "type": "UmbrellaInsurance",
                "displayName": "Umbrella Insurance",
                "icon": "umbrella",
                "description": "Excess liability umbrella insurance coverage",
                "category": "insurance"
            },
            {
                "type": "Assignability",
                "displayName": "Assignability",
                "icon": "swap_horiz",
                "description": "Assignment and transfer rights",
                "category": "rights"
            },
            {
                "type": "DataBreachObligations",
                "displayName": "Data Breach Obligations",
                "icon": "security_update_warning",
                "description": "Data breach notification and response obligations",
                "category": "security"
            },
            {
                "type": "ComplianceObligations",
                "displayName": "Compliance Obligations",
                "icon": "gavel",
                "description": "Regulatory compliance requirements",
                "category": "regulatory"
            },
            {
                "type": "ConfidentialityObligations",
                "displayName": "Confidentiality Obligations",
                "icon": "lock",
                "description": "Confidentiality and NDA terms",
                "category": "security"
            },
            {
                "type": "EscalationObligations",
                "displayName": "Escalation Obligations",
                "icon": "arrow_upward",
                "description": "Escalation procedures and obligations",
                "category": "process"
            },
            {
                "type": "LimitationOfLiabilityObligations",
                "displayName": "Limitation of Liability Obligations",
                "icon": "warning",
                "description": "Liability limitations and caps",
                "category": "liability"
            },
            {
                "type": "PaymentObligations",
                "displayName": "Payment Obligations",
                "icon": "payment",
                "description": "Payment schedules and terms",
                "category": "financial"
            },
            {
                "type": "RenewalNotification",
                "displayName": "Renewal Notification",
                "icon": "refresh",
                "description": "Renewal notification requirements",
                "category": "lifecycle"
            },
            {
                "type": "ServiceLevelAgreement",
                "displayName": "Service Level Agreement",
                "icon": "trending_up",
                "description": "Service level requirements and SLAs",
                "category": "performance"
            },
            {
                "type": "TerminationObligations",
                "displayName": "Termination Obligations",
                "icon": "cancel",
                "description": "Contract termination conditions",
                "category": "lifecycle"
            },
            {
                "type": "WarrantyObligations",
                "displayName": "Warranty Obligations",
                "icon": "verified",
                "description": "Warranty terms and conditions",
                "category": "quality"
            },
            {
                "type": "GoverningLaw",
                "displayName": "Governing Law",
                "icon": "verified",
                "description": "Laws governing the Contract",
                "category": "quality"
            }
        ]
        
        # Set the clause_types container
        nosql_svc.set_container("clause_types")
        
        for clause_type in default_clause_types:
            # Normalize the name
            normalized_name = cls.normalize_entity_name(clause_type["type"])
            
            # Create the document
            doc = {
                "id": normalized_name,
                "pk": "clause_types",
                "normalized_name": normalized_name,
                **clause_type
            }
            
            # Store in memory cache
            cls.static_clause_types[normalized_name] = doc
            
            # Persist to database
            try:
                await nosql_svc.upsert_item(doc)
                logging.debug(f"Initialized clause type: {clause_type['displayName']}")
            except Exception as e:
                logging.error(f"Error initializing clause type {clause_type['type']}: {e}")
        
        logging.info(f"Initialized {len(cls.static_clause_types)} clause types")