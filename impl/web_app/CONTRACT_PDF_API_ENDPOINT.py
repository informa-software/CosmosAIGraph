"""
API Endpoint for Contract PDF Access via Azure Blob Storage

This file contains the API endpoint implementation that should be added to web_app.py
to provide secure PDF access via time-limited SAS URLs.

INSTRUCTIONS:
1. Add the blob_storage_service initialization in the lifespan function
2. Add this endpoint after the /api/contracts/{contract_id}/clauses endpoint
"""

# =============================================================================
# 1. ADD TO IMPORTS SECTION (top of web_app.py)
# =============================================================================
"""
from src.services.blob_storage_service import BlobStorageService
"""

# =============================================================================
# 2. ADD TO GLOBAL VARIABLES SECTION (after other service initializations)
# =============================================================================
"""
# Blob Storage Service for contract PDFs
blob_storage_service: Optional[BlobStorageService] = None
"""

# =============================================================================
# 3. ADD TO LIFESPAN FUNCTION (after other service initializations)
# =============================================================================
"""
    # Initialize Blob Storage Service
    try:
        config = ConfigService()
        conn_str = config.azure_storage_connection_string()

        if conn_str:
            blob_storage_service = BlobStorageService(
                connection_string=conn_str,
                container_name=config.azure_storage_container(),
                folder_prefix=config.azure_storage_folder_prefix()
            )
            logging.info("✅ BlobStorageService initialized successfully")
        else:
            logging.warning("⚠️ Blob storage connection string not configured - PDF access will not be available")
    except Exception as e:
        logging.error(f"❌ Failed to initialize BlobStorageService: {e}")
        blob_storage_service = None
"""

# =============================================================================
# 4. ADD THIS ENDPOINT (after /api/contracts/{contract_id}/clauses)
# =============================================================================
"""
@app.get("/api/contracts/{contract_id}/pdf-url")
async def get_contract_pdf_url(contract_id: str):
    '''
    Generate a time-limited SAS URL for downloading a contract PDF.

    This endpoint provides secure access to contract PDFs stored in Azure Blob Storage
    by generating time-limited Shared Access Signature (SAS) URLs that expire after 1 hour.

    Args:
        contract_id: Contract ID (e.g., "contract_123" or "CONTRACT_NAME")

    Returns:
        JSON response with:
        - contract_id: The requested contract ID
        - pdf_url: Secure time-limited URL to access the PDF
        - expires_in_hours: Number of hours until the URL expires
        - pdf_filename: Name of the PDF file in blob storage

    Example Response:
        {
            "contract_id": "contract_123",
            "pdf_url": "https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/CONTRACT_NAME.pdf?sv=...",
            "expires_in_hours": 1,
            "pdf_filename": "CONTRACT_NAME.pdf"
        }

    Status Codes:
        200: Success - SAS URL generated
        404: Contract not found or PDF not available
        500: Server error during URL generation
        503: Blob storage service not configured
    '''

    # Check if blob storage service is initialized
    if not blob_storage_service:
        logging.error("Blob storage service not available")
        return JSONResponse(
            status_code=503,
            content={
                "error": "PDF access not configured",
                "message": "Blob storage service is not initialized. Please contact administrator."
            }
        )

    try:
        # Set the container for contract queries
        cosmos_nosql_service.set_container(ConfigService.graph_source_db(), ConfigService.graph_source_container())

        # Query to find the contract and get its PDF filename
        # The PDF filename should be stored in the contract metadata
        query = "SELECT c.id, c.filename, c.pdf_filename FROM c WHERE c.id = @contract_id AND c.doctype = 'contract_parent'"
        parameters = [{"name": "@contract_id", "value": contract_id}]

        results = list(cosmos_nosql_service.query_items(query, parameters))

        if not results or len(results) == 0:
            logging.warning(f"Contract not found: {contract_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Contract not found",
                    "message": f"No contract found with ID: {contract_id}"
                }
            )

        contract = results[0]

        # Get PDF filename - try pdf_filename first, fall back to filename
        pdf_filename = contract.get('pdf_filename') or contract.get('filename')

        if not pdf_filename:
            logging.error(f"PDF filename not found for contract: {contract_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "PDF not available",
                    "message": f"No PDF filename found for contract: {contract_id}"
                }
            )

        # Ensure filename has .pdf extension
        if not pdf_filename.lower().endswith('.pdf'):
            pdf_filename = f"{pdf_filename}.pdf"

        # Check if file exists in blob storage
        if not blob_storage_service.file_exists(pdf_filename):
            logging.warning(f"PDF file not found in blob storage: {pdf_filename}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "PDF file not found",
                    "message": f"PDF file not found in storage: {pdf_filename}"
                }
            )

        # Generate SAS URL with configured expiry time
        config = ConfigService()
        expiry_hours = config.blob_sas_expiry_hours()
        sas_url = blob_storage_service.generate_sas_url(
            filename=pdf_filename,
            expiry_hours=expiry_hours
        )

        logging.info(f"Generated SAS URL for contract {contract_id} (PDF: {pdf_filename})")

        return {
            "contract_id": contract_id,
            "pdf_url": sas_url,
            "expires_in_hours": expiry_hours,
            "pdf_filename": pdf_filename
        }

    except Exception as e:
        logging.error(f"Error generating PDF URL for contract {contract_id}: {e}")
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to generate PDF URL",
                "message": str(e)
            }
        )
"""
