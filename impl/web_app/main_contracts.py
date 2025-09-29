"""
Usage:
    python main_contracts.py load_contracts <dbname> <cname> <contracts_dir> <max_docs>
    python main_contracts.py load_contracts caig contracts data/contracts 999999
    python main_contracts.py preprocess_contracts <input_dir> <output_dir>
    python main_contracts.py preprocess_contracts data/contracts data/contracts/processed
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

# This program loads contract documents with clauses and chunks into CosmosDB.
# It follows the multi-level vector storage design for contracts.
# David Ambrose, Informa Software, 2025

import asyncio
import json
import os
import sys
import time
import logging
import traceback
import uuid
from datetime import datetime

from docopt import docopt
from dotenv import load_dotenv

from src.services.ai_service import AiService
from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.contract_entities_service import ContractEntitiesService
from src.util.counter import Counter
from src.util.fs import FS


# List of field names that represent clauses in the contract
CLAUSE_FIELDS = [
    "Indemnification",
    "IndemnificationObligations",
    "WorkersCompensationInsurance", 
    "CommercialPublicLiability",
    "AutomobileInsurance",
    "UmbrellaInsurance",
    "Assignability",
    "DataBreachObligations",
    "ComplianceObligations",
    "ConfidentialityObligations",
    "EscalationObligations",
    "LimitationOfLiabilityObligations",
    "PaymentObligations",
    "RenewalNotification",
    "ServiceLevelAgreement",
    "TerminationObligations",
    "WarrantyObligations"
]

# Fields to exclude from the contract parent document
EXCLUDED_FIELDS = [
    "pages",
    "paragraphs", 
    "sections",
    "tables",
    "figures"
]


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


async def load_contracts(dbname, cname, contracts_dir, max_docs):
    """
    Load contracts with their clauses and chunks from JSON files.
    Creates parent contract documents, clause documents, and chunk documents.
    """
    logging.info(
        "load_contracts, dbname: {}, cname: {}, contracts_dir: {}, max_docs: {}".format(
            dbname, cname, contracts_dir, max_docs
        )
    )
    
    try:
        # Initialize services
        ai_svc = AiService()
        opts = dict()
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()
        
        # Initialize contract entities service
        await ContractEntitiesService.initialize(force_reinitialize=True)
        
        # Set up database and containers
        nosql_svc.set_db(dbname)
        
        # Load counters for tracking
        load_counter = Counter()
        
        # Get contract files
        files_list = FS.list_files_in_dir(contracts_dir)
        contract_files = [f for f in files_list if f.endswith(".json")]
        
        logging.info(f"Found {len(contract_files)} contract files to process")
        
        for idx, filename in enumerate(contract_files):
            if idx >= max_docs:
                break
                
            fq_name = os.path.join(contracts_dir, filename)
            logging.info(f"Processing contract {idx + 1}/{min(len(contract_files), max_docs)}: {filename}")
            
            try:
                # Read contract JSON
                contract_data = FS.read_json(fq_name)
                load_counter.increment("contracts_read")
                
                # Process the contract
                await process_contract(
                    nosql_svc, 
                    ai_svc, 
                    contract_data, 
                    cname,
                    load_counter
                )
                
            except Exception as e:
                logging.error(f"Error processing {fq_name}: {str(e)}")
                logging.error(traceback.format_exc())
                load_counter.increment("contracts_failed")
                
        # Persist all entities to CosmosDB after loading contracts
        logging.info("Persisting contract entities to CosmosDB...")
        await ContractEntitiesService.persist_entities()
        
        # Log entity statistics
        entity_stats = ContractEntitiesService.get_statistics()
        logging.info(
            "Entity statistics: {}".format(json.dumps(entity_stats, indent=2))
        )
        
        # Log final statistics
        logging.info(
            "load_contracts completed; results: {}".format(
                json.dumps(load_counter.get_data())
            )
        )
        
    except Exception as e:
        logging.error(str(e))
        logging.error(traceback.format_exc())
    finally:
        await nosql_svc.close()


async def process_contract(nosql_svc, ai_svc, contract_data, cname, load_counter):
    """
    Process a single contract JSON file and create parent, clause, and chunk documents.
    Handles both preprocessed (with embeddings) and non-preprocessed files.
    """
    # Extract the unique identifier - clean it for use in document IDs
    raw_id = contract_data.get("imageQuestDocumentId", str(uuid.uuid4()))
    # Remove any characters that might cause issues in CosmosDB IDs
    contract_id = raw_id.replace("-", "").replace("_", "").lower()[:32]  # Limit length
    
    # Check if this is a preprocessed file with embeddings
    is_preprocessed = "chunk_embeddings" in contract_data
    
    # Get the markdown content for chunking
    markdown_content = ""
    if "result" in contract_data and "contents" in contract_data["result"]:
        if len(contract_data["result"]["contents"]) > 0:
            markdown_content = contract_data["result"]["contents"][0].get("markdown", "")
    
    # Create parent contract document
    parent_doc = create_parent_contract_doc(contract_data, contract_id)
    
    # Extract contract metadata for reuse in clause and chunk documents
    contract_metadata = extract_contract_metadata(parent_doc)
    
    # Create clause documents with embeddings
    if is_preprocessed:
        # Use existing embeddings from preprocessed file
        clause_docs = await create_clause_documents_preprocessed(
            contract_data, 
            contract_id,
            contract_metadata
        )
        # Use existing chunk embeddings
        chunk_docs = create_chunk_documents_preprocessed(
            contract_data,
            contract_id,
            contract_metadata
        )
    else:
        # Generate embeddings on the fly
        clause_docs = await create_clause_documents(
            contract_data, 
            contract_id, 
            ai_svc,
            contract_metadata
        )
        # Create chunk documents from markdown with embeddings
        chunk_docs = await create_chunk_documents(
            markdown_content,
            contract_id,
            ai_svc,
            contract_metadata
        )
    
    # Update parent doc with clause and chunk IDs
    parent_doc["clause_ids"] = [doc["id"] for doc in clause_docs]
    parent_doc["chunk_ids"] = [doc["id"] for doc in chunk_docs]
    
    # Store all documents in CosmosDB
    await store_contract_documents(
        nosql_svc,
        cname,
        parent_doc,
        clause_docs,
        chunk_docs,
        load_counter
    )


def create_parent_contract_doc(contract_data, contract_id):
    """
    Create the parent contract document from the contract JSON.
    """
    doc = {
        "id": f"contract_{contract_id}",  # CosmosDB uses 'id' not '_id'
        "pk": "contracts",
        "doctype": "contract_parent",
        "imageQuestDocumentId": contract_id,
        "filename": contract_data.get("filename", ""),  # Add filename from root of JSON
        "status": contract_data.get("status", "Unknown"),
        "created_at": time.time(),
        "created_date": str(datetime.now()),
        "clause_ids": [],  # Will be populated later
        "chunk_ids": [],   # Will be populated later
        "metadata": {}
    }
    
    # Extract fields from result.contents[0].fields if available
    if "result" in contract_data and "contents" in contract_data["result"]:
        if len(contract_data["result"]["contents"]) > 0:
            fields = contract_data["result"]["contents"][0].get("fields", {})
            
            # Extract contract metadata fields (non-clause fields)
            metadata_fields = {
                "ContractorPartyName": fields.get("ContractorPartyName", {}),
                "ContractingPartyName": fields.get("ContractingPartyName", {}),
                "EffectiveDate": fields.get("EffectiveDate", {}),
                "ExpirationDate": fields.get("ExpirationDate", {}),
                "MaximumContractValue": fields.get("MaximumContractValue", {}),
                "GoverningLawState": fields.get("GoverningLawState", {}),
                "ContractType": fields.get("ContractType", {}),
                "Jurisdiction": fields.get("Jurisdiction", {}),
                "ContractSummary": fields.get("ContractSummary", {}),
                "ContractorContactIinformation": fields.get("ContractorContactIinformation", {}),
                "ContractingPartyName": fields.get("ContractingPartyName", {}),
                "ExpirationDate": fields.get("ExpirationDate", {})
            }
            
            # Store metadata fields with their values and confidence
            for field_name, field_data in metadata_fields.items():
                if field_data:
                    value = extract_field_value(field_data)
                    if value:
                        doc["metadata"][field_name] = {
                            "value": value,
                            "confidence": field_data.get("confidence", 0)
                        }
                        
                        # Add normalized values for entity fields
                        if field_name == "ContractorPartyName":
                            normalized = ContractEntitiesService.normalize_entity_name(value)
                            doc["metadata"][field_name]["normalizedValue"] = normalized
                        elif field_name == "ContractingPartyName":
                            normalized = ContractEntitiesService.normalize_entity_name(value)
                            doc["metadata"][field_name]["normalizedValue"] = normalized
                        elif field_name == "GoverningLawState":
                            normalized = ContractEntitiesService.normalize_entity_name(value)
                            doc["metadata"][field_name]["normalizedValue"] = normalized
                        elif field_name == "ContractType":
                            normalized = ContractEntitiesService.normalize_entity_name(value)
                            doc["metadata"][field_name]["normalizedValue"] = normalized
    
    # Add normalized values as top-level fields for easier querying
    if "ContractorPartyName" in doc["metadata"]:
        doc["contractor_party"] = doc["metadata"]["ContractorPartyName"].get("normalizedValue", doc["metadata"]["ContractorPartyName"]["value"])
    if "ContractingPartyName" in doc["metadata"]:
        doc["contracting_party"] = doc["metadata"]["ContractingPartyName"].get("normalizedValue", doc["metadata"]["ContractingPartyName"]["value"])
    if "EffectiveDate" in doc["metadata"]:
        doc["effective_date"] = doc["metadata"]["EffectiveDate"]["value"]
    if "ExpirationDate" in doc["metadata"]:
        doc["expiration_date"] = doc["metadata"]["ExpirationDate"]["value"]
    if "MaximumContractValue" in doc["metadata"]:
        doc["contract_value"] = doc["metadata"]["MaximumContractValue"]["value"]
    if "ContractType" in doc["metadata"]:
        doc["contract_type"] = doc["metadata"]["ContractType"].get("normalizedValue", doc["metadata"]["ContractType"]["value"])
    if "GoverningLawState" in doc["metadata"]:
        doc["governing_law"] = doc["metadata"]["GoverningLawState"].get("normalizedValue", doc["metadata"]["GoverningLawState"]["value"])
    if "Jurisdiction" in doc["metadata"]:
        doc["jurisdiction"] = doc["metadata"]["Jurisdiction"]["value"]
    
    # Update entity catalogs with this contract's entities
    asyncio.create_task(update_contract_entities(doc))
        
    return doc


def extract_contract_metadata(parent_doc):
    """
    Extract contract metadata fields that should be included in clause and chunk documents.
    Uses normalized values for searchable entity fields.
    """
    metadata = {
        "filename": parent_doc.get("filename", ""),
        "contractor_party": parent_doc.get("contractor_party", ""),  # Already normalized
        "contracting_party": parent_doc.get("contracting_party", ""),  # Already normalized
        "effective_date": parent_doc.get("effective_date", ""),
        "expiration_date": parent_doc.get("expiration_date", ""),
        "contract_value": parent_doc.get("contract_value", ""),
        "governing_law": parent_doc.get("governing_law", ""),  # Already normalized
        "contract_type": parent_doc.get("contract_type", ""),  # Already normalized
        "jurisdiction": parent_doc.get("jurisdiction", "")
    }
    return metadata


async def create_clause_documents(contract_data, contract_id, ai_svc, contract_metadata):
    """
    Extract clauses from the contract and create individual clause documents with embeddings.
    """
    clause_docs = []
    
    if "result" not in contract_data or "contents" not in contract_data["result"]:
        return clause_docs
        
    if len(contract_data["result"]["contents"]) == 0:
        return clause_docs
        
    fields = contract_data["result"]["contents"][0].get("fields", {})
    
    # Process each clause field
    for clause_field in CLAUSE_FIELDS:
        if clause_field in fields:
            field_data = fields[clause_field]
            clause_text = extract_field_value(field_data)
            
            if clause_text:
                # Generate embedding for clause text
                try:
                    embedding_response = ai_svc.generate_embeddings(clause_text)
                    embedding = embedding_response.data[0].embedding
                except Exception as e:
                    logging.error(f"Error generating embedding for clause {clause_field}: {str(e)}")
                    embedding = None
                
                # Create clause document with contract metadata
                clause_doc = {
                    "id": f"contract_{contract_id}_clause_{clause_field.lower()}",
                    "pk": "contract_clauses",
                    "doctype": "contract_clause",
                    "parent_id": f"contract_{contract_id}",
                    "clause_type": clause_field,
                    "clause_text": clause_text,
                    "embedding": embedding,
                    "confidence": field_data.get("confidence", 0),
                    "spans": field_data.get("spans", []),  # For display purposes
                    "source": field_data.get("source", ""),  # Page coordinates
                    "created_at": time.time(),
                    # Add contract metadata fields
                    "filename": contract_metadata.get("filename", ""),
                    "contractor_party": contract_metadata.get("contractor_party", ""),
                    "contracting_party": contract_metadata.get("contracting_party", ""),
                    "effective_date": contract_metadata.get("effective_date", ""),
                    "expiration_date": contract_metadata.get("expiration_date", ""),
                    "contract_value": contract_metadata.get("contract_value", ""),
                    "governing_law": contract_metadata.get("governing_law", ""),
                    "contract_type": contract_metadata.get("contract_type", ""),
                    "jurisdiction": contract_metadata.get("jurisdiction", "")
                }
                
                clause_docs.append(clause_doc)
                logging.info(f"Created clause document: {clause_doc['id']}")
    
    return clause_docs


async def create_clause_documents_preprocessed(contract_data, contract_id, contract_metadata):
    """
    Extract clauses from a preprocessed contract that already has embeddings.
    """
    clause_docs = []
    
    if "result" not in contract_data or "contents" not in contract_data["result"]:
        return clause_docs
        
    if len(contract_data["result"]["contents"]) == 0:
        return clause_docs
        
    fields = contract_data["result"]["contents"][0].get("fields", {})
    
    # Process each clause field
    for clause_field in CLAUSE_FIELDS:
        if clause_field in fields:
            field_data = fields[clause_field]
            clause_text = extract_field_value(field_data)
            
            if clause_text:
                # Use existing embedding from preprocessed data
                embedding = field_data.get("embedding", None)
                
                # Create clause document with contract metadata
                clause_doc = {
                    "id": f"contract_{contract_id}_clause_{clause_field.lower()}",
                    "pk": "contract_clauses",
                    "doctype": "contract_clause",
                    "parent_id": f"contract_{contract_id}",
                    "clause_type": clause_field,
                    "clause_text": clause_text,
                    "embedding": embedding,
                    "confidence": field_data.get("confidence", 0),
                    "spans": field_data.get("spans", []),  # For display purposes
                    "source": field_data.get("source", ""),  # Page coordinates
                    "created_at": time.time(),
                    # Add contract metadata fields
                    "filename": contract_metadata.get("filename", ""),
                    "contractor_party": contract_metadata.get("contractor_party", ""),
                    "contracting_party": contract_metadata.get("contracting_party", ""),
                    "effective_date": contract_metadata.get("effective_date", ""),
                    "expiration_date": contract_metadata.get("expiration_date", ""),
                    "contract_value": contract_metadata.get("contract_value", ""),
                    "governing_law": contract_metadata.get("governing_law", ""),
                    "contract_type": contract_metadata.get("contract_type", ""),
                    "jurisdiction": contract_metadata.get("jurisdiction", "")
                }
                
                clause_docs.append(clause_doc)
                logging.info(f"Created clause document from preprocessed: {clause_doc['id']}")
    
    return clause_docs


def create_chunk_documents_preprocessed(contract_data, contract_id, contract_metadata):
    """
    Create chunk documents from preprocessed contract data that already has chunk embeddings.
    """
    chunk_docs = []
    
    if "chunk_embeddings" not in contract_data:
        return chunk_docs
    
    for chunk_data in contract_data["chunk_embeddings"]:
        chunk_doc = {
            "id": f"contract_{contract_id}_chunk_{chunk_data['chunk_index']:03d}",
            "pk": "contract_chunks",
            "doctype": "contract_chunk",
            "parent_id": f"contract_{contract_id}",
            "chunk_index": chunk_data["chunk_index"],
            "chunk_text": chunk_data["chunk_text"],
            "embedding": chunk_data["embedding"],
            "chunk_size": len(chunk_data["chunk_text"]),
            "created_at": time.time(),
            # Add contract metadata fields
            "filename": contract_metadata.get("filename", ""),
            "contractor_party": contract_metadata.get("contractor_party", ""),
            "contracting_party": contract_metadata.get("contracting_party", ""),
            "effective_date": contract_metadata.get("effective_date", ""),
            "expiration_date": contract_metadata.get("expiration_date", ""),
            "contract_value": contract_metadata.get("contract_value", ""),
            "governing_law": contract_metadata.get("governing_law", ""),
            "contract_type": contract_metadata.get("contract_type", ""),
            "jurisdiction": contract_metadata.get("jurisdiction", "")
        }
        
        chunk_docs.append(chunk_doc)
        logging.info(f"Created chunk document from preprocessed: {chunk_doc['id']}")
    
    return chunk_docs


async def create_chunk_documents(markdown_content, contract_id, ai_svc, contract_metadata, chunk_size=750, overlap=0.15):
    """
    Create chunk documents from the markdown content with embeddings.
    """
    chunk_docs = []
    
    if not markdown_content:
        return chunk_docs
    
    # Split content into chunks with overlap
    chunks = create_text_chunks(markdown_content, chunk_size, overlap)
    
    for idx, chunk_text in enumerate(chunks):
        # Generate embedding for chunk
        try:
            embedding_response = ai_svc.generate_embeddings(chunk_text)
            embedding = embedding_response.data[0].embedding
        except Exception as e:
            logging.error(f"Error generating embedding for chunk {idx}: {str(e)}")
            embedding = None
        
        # Create chunk document with contract metadata
        chunk_doc = {
            "id": f"contract_{contract_id}_chunk_{idx:03d}",
            "pk": "contract_chunks",
            "doctype": "contract_chunk",
            "parent_id": f"contract_{contract_id}",
            "chunk_index": idx,
            "chunk_text": chunk_text,
            "embedding": embedding,
            "chunk_size": len(chunk_text),
            "created_at": time.time(),
            # Add contract metadata fields
            "filename": contract_metadata.get("filename", ""),
            "contractor_party": contract_metadata.get("contractor_party", ""),
            "contracting_party": contract_metadata.get("contracting_party", ""),
            "effective_date": contract_metadata.get("effective_date", ""),
            "expiration_date": contract_metadata.get("expiration_date", ""),
            "contract_value": contract_metadata.get("contract_value", ""),
            "governing_law": contract_metadata.get("governing_law", ""),
            "contract_type": contract_metadata.get("contract_type", ""),
            "jurisdiction": contract_metadata.get("jurisdiction", "")
        }
        
        chunk_docs.append(chunk_doc)
        logging.info(f"Created chunk document {idx + 1}/{len(chunks)}")
    
    return chunk_docs


def create_text_chunks(text, chunk_size=750, overlap_ratio=0.15):
    """
    Split text into chunks with overlap.
    """
    words = text.split()
    chunk_words = chunk_size // 5  # Rough estimate: 5 characters per word
    overlap_words = int(chunk_words * overlap_ratio)
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        
        if end >= len(words):
            break
            
        # Move start position with overlap
        start = end - overlap_words
    
    return chunks


async def store_contract_documents(nosql_svc, cname, parent_doc, clause_docs, chunk_docs, load_counter):
    """
    Store all contract documents in CosmosDB.
    """
    # Store parent document
    try:
        nosql_svc.set_container(cname)  # Main contracts container
        await nosql_svc.upsert_item(parent_doc)
        load_counter.increment("parent_docs_stored")
        logging.info(f"Stored parent document: {parent_doc['id']}")
    except Exception as e:
        logging.error(f"Error storing parent document: {str(e)}")
        load_counter.increment("parent_docs_failed")
    
    # Store clause documents
    nosql_svc.set_container("contract_clauses")
    for clause_doc in clause_docs:
        try:
            await nosql_svc.upsert_item(clause_doc)
            load_counter.increment("clause_docs_stored")
        except Exception as e:
            logging.error(f"Error storing clause document {clause_doc['id']}: {str(e)}")
            load_counter.increment("clause_docs_failed")
    
    # Store chunk documents
    nosql_svc.set_container("contract_chunks")
    for chunk_doc in chunk_docs:
        try:
            await nosql_svc.upsert_item(chunk_doc)
            load_counter.increment("chunk_docs_stored")
        except Exception as e:
            logging.error(f"Error storing chunk document {chunk_doc['id']}: {str(e)}")
            load_counter.increment("chunk_docs_failed")


def extract_field_value(field_data):
    """
    Extract the appropriate value from a field based on its type.
    """
    if not field_data:
        return None
        
    field_type = field_data.get("type", "string")
    
    if field_type == "string":
        return field_data.get("valueString", "")
    elif field_type == "number":
        return field_data.get("valueNumber", 0)
    elif field_type == "date":
        return field_data.get("valueDate", "")
    elif field_type == "boolean":
        return field_data.get("valueBoolean", False)
    else:
        # Default to string value
        return field_data.get("valueString", "")


async def update_contract_entities(parent_doc):
    """
    Update entity catalogs based on contract metadata.
    Uses the ORIGINAL values from metadata to create/update entities (for display names).
    This runs asynchronously to avoid blocking contract loading.
    """
    try:
        contract_id = parent_doc.get("id", "")
        metadata = parent_doc.get("metadata", {})
        
        # Extract contract value for statistics from metadata
        contract_value = 0.0
        try:
            if "MaximumContractValue" in metadata:
                value_field = metadata["MaximumContractValue"].get("value")
                if value_field:
                    contract_value = float(value_field)
        except (ValueError, TypeError):
            pass
        
        # Update contractor party entity with ORIGINAL value
        if "ContractorPartyName" in metadata:
            original_value = metadata["ContractorPartyName"].get("value")
            if original_value:
                await ContractEntitiesService.update_or_create_contractor_party(
                    original_value, contract_id, contract_value
                )
        
        # Update contracting party entity with ORIGINAL value
        if "ContractingPartyName" in metadata:
            original_value = metadata["ContractingPartyName"].get("value")
            if original_value:
                await ContractEntitiesService.update_or_create_contracting_party(
                    original_value, contract_id, contract_value
                )
        
        # Update governing law entity with ORIGINAL value
        if "GoverningLawState" in metadata:
            original_value = metadata["GoverningLawState"].get("value")
            if original_value:
                await ContractEntitiesService.update_or_create_governing_law(
                    original_value, contract_id
                )
        
        # Update contract type entity with ORIGINAL value  
        if "ContractType" in metadata:
            original_value = metadata["ContractType"].get("value")
            if original_value:
                await ContractEntitiesService.update_or_create_contract_type(
                    original_value, contract_id
                )
            
    except Exception as e:
        logging.error(f"Error updating contract entities for {contract_id}: {str(e)}")


async def preprocess_contracts(input_dir, output_dir):
    """
    Preprocess contracts to generate embeddings and save enriched JSON files.
    This allows reloading without regenerating embeddings.
    """
    logging.info(f"Preprocessing contracts from {input_dir} to {output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize AI service for embeddings
    ai_svc = AiService()
    
    # Get contract files
    files_list = FS.list_files_in_dir(input_dir)
    contract_files = [f for f in files_list if f.endswith(".json")]
    
    for idx, filename in enumerate(contract_files):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, f"processed_{filename}")
        
        logging.info(f"Processing {idx + 1}/{len(contract_files)}: {filename}")
        
        try:
            # Read original contract
            contract_data = FS.read_json(input_path)
            
            # Generate embeddings for clauses
            if "result" in contract_data and "contents" in contract_data["result"]:
                if len(contract_data["result"]["contents"]) > 0:
                    fields = contract_data["result"]["contents"][0].get("fields", {})
                    
                    # Process each clause field
                    for clause_field in CLAUSE_FIELDS:
                        if clause_field in fields:
                            field_data = fields[clause_field]
                            clause_text = extract_field_value(field_data)
                            
                            if clause_text:
                                # Generate and store embedding
                                try:
                                    embedding_response = ai_svc.generate_embeddings(clause_text)
                                    field_data["embedding"] = embedding_response.data[0].embedding
                                    logging.info(f"Generated embedding for {clause_field}")
                                except Exception as e:
                                    logging.error(f"Error generating embedding for {clause_field}: {str(e)}")
                    
                    # Generate embeddings for markdown chunks
                    markdown_content = contract_data["result"]["contents"][0].get("markdown", "")
                    if markdown_content:
                        chunks = create_text_chunks(markdown_content)
                        chunk_embeddings = []
                        
                        for chunk_idx, chunk_text in enumerate(chunks):
                            try:
                                embedding_response = ai_svc.generate_embeddings(chunk_text)
                                chunk_embeddings.append({
                                    "chunk_index": chunk_idx,
                                    "chunk_text": chunk_text,
                                    "embedding": embedding_response.data[0].embedding
                                })
                                logging.info(f"Generated embedding for chunk {chunk_idx + 1}/{len(chunks)}")
                            except Exception as e:
                                logging.error(f"Error generating chunk embedding: {str(e)}")
                        
                        # Store chunk embeddings in the contract data
                        contract_data["chunk_embeddings"] = chunk_embeddings
            
            # Save processed contract
            FS.write_json(contract_data, output_path)
            logging.info(f"Saved processed contract to {output_path}")
            
        except Exception as e:
            logging.error(f"Error processing {filename}: {str(e)}")
            logging.error(traceback.format_exc())
    
    logging.info("Preprocessing completed")


if __name__ == "__main__":
    # Standard initialization of env and logger
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            
            if func == "load_contracts":
                dbname = sys.argv[2]
                cname = sys.argv[3]
                contracts_dir = sys.argv[4]
                max_docs = int(sys.argv[5])
                asyncio.run(load_contracts(dbname, cname, contracts_dir, max_docs))
                
            elif func == "preprocess_contracts":
                input_dir = sys.argv[2]
                output_dir = sys.argv[3]
                asyncio.run(preprocess_contracts(input_dir, output_dir))
                
            else:
                print_options(f"Error: unknown function {func}")
                
        except Exception as e:
            logging.critical(str(e))
            logging.critical(traceback.format_exc())