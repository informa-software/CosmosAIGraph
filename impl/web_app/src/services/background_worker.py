"""
Background Worker Service

Processes batch jobs for contract comparison and query operations.
Handles job execution, progress tracking, and automatic result saving.
"""

import asyncio
import logging
import json
import re
import time
import traceback
from typing import Dict, Any, Optional

from src.models.job_models import JobStatus, JobType, JobProgress, ProcessingStep
from src.services.job_service import JobService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
from src.services.analysis_results_service import AnalysisResultsService
from src.services.blob_storage_service import BlobStorageService
from src.services.content_understanding_service import ContentUnderstandingService
from src.services.config_service import ConfigService
from src.services.contract_entities_service import ContractEntitiesService
from src.util.counter import Counter
from src.models.analysis_results_models import (
    SaveComparisonRequest,
    SaveQueryRequest,
    AnalysisMetadata,
    ContractQueried
)

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Background worker for processing batch jobs

    Processes jobs from the job queue, updates progress,
    and automatically saves results to analysis_results container.

    Creates its own service instances to avoid connection lifecycle issues.
    """

    def __init__(self):
        """
        Initialize worker without services.
        Services will be created per-job to ensure proper connection lifecycle.
        """
        pass

    async def process_job(self, job_id: str, user_id: str):
        """
        Process a single job

        Creates its own service instances to ensure proper connection lifecycle.

        Args:
            job_id: Job identifier
            user_id: User ID (partition key)
        """
        logger.info(f"Starting job processing: {job_id}")

        # Initialize services for this job
        cosmos_service = None

        try:
            # Create dedicated service instances for this job
            logger.info("Initializing services for job processing...")
            cosmos_service = CosmosNoSQLService()
            await cosmos_service.initialize()

            job_service = JobService(cosmos_service)
            ai_service = AiService()
            analysis_results_service = AnalysisResultsService(cosmos_service)

            logger.info("Services initialized successfully")

            # Get job details
            job = await job_service.get_job(job_id, user_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return

            # Update status to processing
            await job_service.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.PROCESSING
            )

            # Route to appropriate processor
            if job.job_type == JobType.CONTRACT_COMPARISON:
                await self._process_comparison_job(
                    job_id, user_id, job.request,
                    job_service, cosmos_service, ai_service, analysis_results_service
                )
            elif job.job_type == JobType.CONTRACT_QUERY:
                await self._process_query_job(
                    job_id, user_id, job.request,
                    job_service, cosmos_service, ai_service, analysis_results_service
                )
            elif job.job_type == JobType.CONTRACT_UPLOAD:
                await self._process_contract_upload_job(
                    job_id, user_id, job.request,
                    job_service, cosmos_service, ai_service
                )
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            logger.info(f"Job completed successfully: {job_id}")

        except Exception as e:
            logger.error(f"Job processing failed: {job_id}")
            logger.error(traceback.format_exc())

            # Update job as failed (recreate job_service if needed)
            try:
                if cosmos_service is None:
                    cosmos_service = CosmosNoSQLService()
                    await cosmos_service.initialize()

                job_service = JobService(cosmos_service)
                await job_service.update_job_status(
                    job_id=job_id,
                    user_id=user_id,
                    status=JobStatus.FAILED,
                    error_message=str(e),
                    error_details={"traceback": traceback.format_exc()}
                )
            except Exception as cleanup_error:
                logger.error(f"Failed to update job status during error handling: {cleanup_error}")

        finally:
            # Clean up connection
            if cosmos_service:
                try:
                    await cosmos_service.close()
                    logger.info("Services closed successfully")
                except Exception as close_error:
                    logger.error(f"Error closing services: {close_error}")

    async def _process_comparison_job(
        self,
        job_id: str,
        user_id: str,
        request: Dict[str, Any],
        job_service: JobService,
        cosmos_service: CosmosNoSQLService,
        ai_service: AiService,
        analysis_results_service: AnalysisResultsService
    ):
        """
        Process a contract comparison job

        Args:
            job_id: Job identifier
            user_id: User ID
            request: Comparison request parameters
            job_service: Job service instance
            cosmos_service: CosmosDB service instance
            ai_service: AI service instance
            analysis_results_service: Analysis results service instance
        """
        logger.info(f"Processing comparison job: {job_id}")

        # Extract parameters
        standard_contract_id = request.get("standardContractId")
        compare_contract_ids = request.get("compareContractIds", [])
        comparison_mode = request.get("comparisonMode", "clauses")
        selected_clauses = request.get("selectedClauses", "all")
        model_selection = request.get("modelSelection", "primary")

        total_contracts = len(compare_contract_ids)

        # Step 1: Retrieving data
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.RETRIEVING_DATA,
                current_item=0,
                total_items=total_contracts,
                percentage=10.0,
                message="Retrieving contract data..."
            )
        )

        # Import helper functions from web_app
        # Note: In production, these should be refactored into a shared module
        from web_app import retrieve_comparison_data, create_comparison_prompt, enhance_comparison_response

        standard_data, comparison_data, clause_cache = await retrieve_comparison_data(
            cosmos_service,
            standard_contract_id,
            compare_contract_ids,
            comparison_mode,
            selected_clauses if comparison_mode == "clauses" and selected_clauses != "all" else None
        )

        # Step 2: Generating prompt
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.GENERATING_PROMPT,
                current_item=0,
                total_items=total_contracts,
                percentage=30.0,
                message="Preparing AI analysis..."
            )
        )

        if comparison_mode == "clauses" and selected_clauses != "all":
            llm_prompt = create_comparison_prompt(standard_data, comparison_data, comparison_mode, selected_clauses)
        else:
            llm_prompt = create_comparison_prompt(standard_data, comparison_data, comparison_mode)

        # Step 3: Calling LLM
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.CALLING_LLM,
                current_item=0,
                total_items=total_contracts,
                percentage=50.0,
                message=f"Analyzing {total_contracts} contract{'s' if total_contracts > 1 else ''}..."
            )
        )

        # Track start time
        start_time = time.time()

        # Send to LLM
        system_prompt = "You are a legal contract analysis expert. Provide detailed, accurate comparisons in JSON format."

        # Handle full mode truncation if needed
        if comparison_mode == "full":
            max_prompt_chars = 100000
            if len(llm_prompt) > max_prompt_chars:
                logger.warning(f"Prompt too long ({len(llm_prompt)} chars), truncating to {max_prompt_chars}")
                llm_prompt = llm_prompt[:max_prompt_chars] + "\n... [TRUNCATED FOR LENGTH]" + llm_prompt[-2000:]

        llm_response = ai_service.get_completion_for_contracts(
            user_prompt=llm_prompt,
            system_prompt=system_prompt,
            max_tokens=6000,
            model_selection=model_selection
        )

        elapsed_time = time.time() - start_time

        # Step 4: Processing results
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.PROCESSING_RESULTS,
                current_item=0,
                total_items=total_contracts,
                percentage=80.0,
                message="Formatting results..."
            )
        )

        # Parse LLM response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                comparison_results = json.loads(json_str)
            else:
                comparison_results = json.loads(llm_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            comparison_results = {
                "comparisons": [{
                    "contract_id": cid,
                    "error": "Failed to parse comparison results",
                    "raw_response": llm_response[:500]
                } for cid in compare_contract_ids]
            }

        # Enhance response with clause texts (if in clauses mode)
        if comparison_mode == "clauses":
            comparison_results = await enhance_comparison_response(comparison_results, clause_cache)

        # Step 5: Saving results
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.SAVING_RESULTS,
                current_item=0,
                total_items=total_contracts,
                percentage=90.0,
                message="Saving results..."
            )
        )

        # Build full response object
        full_results = {
            "success": True,
            "standardContractId": standard_contract_id,
            "compareContractIds": compare_contract_ids,
            "comparisonMode": comparison_mode,
            "selectedClauses": selected_clauses if comparison_mode == "clauses" else None,
            "results": comparison_results
        }

        # Automatically save results
        save_request = SaveComparisonRequest(
            user_id=user_id,
            standard_contract_id=standard_contract_id,
            compare_contract_ids=compare_contract_ids,
            comparison_mode=comparison_mode,
            selected_clauses=selected_clauses if comparison_mode == "clauses" and selected_clauses != "all" else None,
            results=full_results,
            metadata=AnalysisMetadata(
                title=f"Batch Comparison: {standard_contract_id} vs {len(compare_contract_ids)} contract(s)",
                description=f"{comparison_mode} comparison (Job: {job_id})",
                execution_time_seconds=elapsed_time
            )
        )

        result_id = await analysis_results_service.save_comparison_result(save_request)

        # Step 6: Mark as completed
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.COMPLETED,
                current_item=total_contracts,
                total_items=total_contracts,
                percentage=100.0,
                message="Comparison completed successfully"
            )
        )

        await job_service.update_job_status(
            job_id=job_id,
            user_id=user_id,
            status=JobStatus.COMPLETED,
            result_id=result_id
        )

        logger.info(f"Comparison job completed: {job_id}, result_id: {result_id}")

    async def _process_query_job(
        self,
        job_id: str,
        user_id: str,
        request: Dict[str, Any],
        job_service: JobService,
        cosmos_service: CosmosNoSQLService,
        ai_service: AiService,
        analysis_results_service: AnalysisResultsService
    ):
        """
        Process a contract query job

        Args:
            job_id: Job identifier
            user_id: User ID
            request: Query request parameters
            job_service: Job service instance
            cosmos_service: CosmosDB service instance
            ai_service: AI service instance
            analysis_results_service: Analysis results service instance
        """
        logger.info(f"Processing query job: {job_id}")

        # Extract parameters
        question = request.get("question", "")
        contract_ids = request.get("contract_ids", [])
        model_selection = request.get("modelSelection", "primary")

        total_contracts = len(contract_ids)

        # Step 1: Retrieving data
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.RETRIEVING_DATA,
                current_item=0,
                total_items=total_contracts,
                percentage=10.0,
                message=f"Retrieving {total_contracts} contracts..."
            )
        )

        # Import helper function from web_app
        from web_app import get_contract_full_text

        # Retrieve contract texts
        contract_texts = {}
        contracts_queried = []

        for i, contract_id in enumerate(contract_ids):
            contract_text = await get_contract_full_text(cosmos_service, contract_id)
            contract_texts[contract_id] = contract_text

            contracts_queried.append(ContractQueried(
                contract_id=contract_id,
                filename=f"{contract_id}.json",
                contract_title=contract_id
            ))

            # Update progress
            progress_pct = 10.0 + (20.0 * (i + 1) / total_contracts)
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.RETRIEVING_DATA,
                    current_item=i + 1,
                    total_items=total_contracts,
                    percentage=progress_pct,
                    message=f"Retrieved {i + 1} of {total_contracts} contracts..."
                )
            )

        # Step 2: Generating prompt
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.GENERATING_PROMPT,
                current_item=0,
                total_items=total_contracts,
                percentage=35.0,
                message="Preparing query..."
            )
        )

        # Build prompt
        combined_text = "\n\n---\n\n".join([
            f"CONTRACT {i+1} ({cid}):\n{text}"
            for i, (cid, text) in enumerate(contract_texts.items())
        ])

        # Truncate if needed
        max_chars = 80000  # ~20K tokens
        if len(combined_text) > max_chars:
            logger.warning(f"Combined text too long ({len(combined_text)} chars), truncating to {max_chars}")
            combined_text = combined_text[:max_chars] + "\n... [TRUNCATED FOR LENGTH]"

        # Build system prompt with markdown formatting instructions (same as streaming endpoint)
        system_prompt = """You are a legal contract analysis expert. Analyze the provided contracts and answer the user's question.

**IMPORTANT: You MUST respond in Markdown format, NOT JSON.**

**Instructions:**
- Provide a clear, well-structured response in **Markdown format**
- DO NOT use JSON format - use Markdown with headings, paragraphs, and lists
- Break out your analysis **by contract**, using headings (## Contract Title)
- **Cite specific sections** from the contract text to support your findings
- Use bullet points or numbered lists for clarity
- Be precise and professional in your language

**Response Format (Markdown, NOT JSON):**
```markdown
# Analysis

## Contract 1: [Title/ID]
[Your analysis with specific citations]

## Contract 2: [Title/ID]
[Your analysis with specific citations]

# Summary
[Brief summary of findings across all contracts]
```"""

        # Build user prompt
        user_prompt = f"""**Question:** {question}

---

**Contracts to analyze:**

{combined_text}

---

Please provide a comprehensive answer based on the contracts above, following the markdown format specified."""

        # Step 3: Calling LLM
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.CALLING_LLM,
                current_item=0,
                total_items=total_contracts,
                percentage=50.0,
                message="Analyzing contracts with AI..."
            )
        )

        # Track start time
        start_time = time.time()

        # Send to LLM
        llm_response = ai_service.get_completion_for_contracts(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            model_selection=model_selection
        )

        elapsed_time = time.time() - start_time

        # Step 4: Saving results
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.SAVING_RESULTS,
                current_item=0,
                total_items=total_contracts,
                percentage=90.0,
                message="Saving results..."
            )
        )

        # Build results object
        results = {
            "answer_summary": llm_response,
            "ranked_contracts": [],
            "execution_metadata": {
                "contracts_analyzed": len(contract_ids),
                "query_time_seconds": elapsed_time,
                "llm_model": model_selection
            }
        }

        # Automatically save results
        save_request = SaveQueryRequest(
            user_id=user_id,
            query_text=question,
            query_type="natural_language",
            contracts_queried=contracts_queried,
            results=results,
            metadata=AnalysisMetadata(
                title=f"Query: {question[:50]}{'...' if len(question) > 50 else ''}",
                description=f"Analyzed {len(contract_ids)} contracts (Job: {job_id})",
                execution_time_seconds=elapsed_time
            )
        )

        result_id = await analysis_results_service.save_query_result(save_request)

        # Step 5: Mark as completed
        await job_service.update_job_progress(
            job_id=job_id,
            user_id=user_id,
            progress=JobProgress(
                current_step=ProcessingStep.COMPLETED,
                current_item=total_contracts,
                total_items=total_contracts,
                percentage=100.0,
                message="Query completed successfully"
            )
        )

        await job_service.update_job_status(
            job_id=job_id,
            user_id=user_id,
            status=JobStatus.COMPLETED,
            result_id=result_id
        )

        logger.info(f"Query job completed: {job_id}, result_id: {result_id}")

    async def _process_contract_upload_job(
        self,
        job_id: str,
        user_id: str,
        request: Dict[str, Any],
        job_service: JobService,
        cosmos_service: CosmosNoSQLService,
        ai_service: AiService
    ):
        """
        Process a contract upload job

        Downloads PDF from blob storage, processes through Azure Content Understanding,
        and loads into CosmosDB using the contract processing pipeline.

        Args:
            job_id: Job identifier
            user_id: User ID
            request: Upload request parameters (filename, blob_url, uploaded_by, etc.)
            job_service: Job service instance
            cosmos_service: CosmosDB service instance
            ai_service: AI service instance
        """
        logger.info(f"Processing contract upload job: {job_id}")

        # Extract request parameters
        filename = request.get("filename", "")
        original_filename = request.get("original_filename", filename)
        blob_url = request.get("blob_url", "")
        uploaded_by = request.get("uploaded_by", "system")
        file_size_bytes = request.get("file_size_bytes", 0)

        logger.info(f"Upload job details - Filename: {filename}, Uploader: {uploaded_by}, Size: {file_size_bytes} bytes")

        # Initialize blob storage and content understanding services
        blob_storage_service = None
        content_understanding_service = None

        try:
            # Step 1: Initialize blob storage service
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.UPLOADING,
                    current_item=0,
                    total_items=4,  # EXTRACTING, PROCESSING, LOADING, COMPLETED
                    percentage=5.0,
                    message=f"Initializing services for {filename}..."
                )
            )

            # Initialize BlobStorageService
            connection_string = ConfigService.azure_storage_connection_string()
            if not connection_string:
                raise ValueError("Azure Storage connection string not configured")

            blob_storage_service = BlobStorageService(
                connection_string=connection_string,
                container_name="tenant1-dev20",
                folder_prefix="system/contract-intelligence"
            )

            # Initialize ContentUnderstandingService
            cu_endpoint = ConfigService.content_understanding_endpoint()
            cu_key = ConfigService.content_understanding_key()
            cu_analyzer_id = ConfigService.content_understanding_analyzer_id()
            cu_api_version = ConfigService.content_understanding_api_version()

            if not all([cu_endpoint, cu_key, cu_analyzer_id]):
                raise ValueError("Azure Content Understanding not properly configured")

            content_understanding_service = ContentUnderstandingService(
                endpoint=cu_endpoint,
                api_version=cu_api_version,
                subscription_key=cu_key,
                analyzer_id=cu_analyzer_id
            )

            logger.info("Services initialized successfully")

            # Step 2: Download PDF from blob storage
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.UPLOADING,
                    current_item=0,
                    total_items=4,
                    percentage=10.0,
                    message=f"Downloading {filename} from blob storage..."
                )
            )

            # Run blocking I/O in thread pool to avoid blocking the event loop
            file_bytes = await asyncio.to_thread(blob_storage_service.download_file_bytes, filename)
            logger.info(f"Downloaded {len(file_bytes)} bytes from blob storage")

            # Step 3: Extract contract data using Azure Content Understanding
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.EXTRACTING,
                    current_item=1,
                    total_items=4,
                    percentage=25.0,
                    message=f"Extracting contract data from {filename}..."
                )
            )

            # Call Azure Content Understanding to analyze the PDF (in thread pool to avoid blocking)
            cu_result = await asyncio.to_thread(
                content_understanding_service.analyze_document_from_bytes,
                file_bytes,
                filename
            )
            logger.info(f"Azure Content Understanding analysis completed for {filename}")

            # Step 4: Process the contract through the main pipeline
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.PROCESSING,
                    current_item=2,
                    total_items=4,
                    percentage=50.0,
                    message=f"Processing contract data and generating embeddings..."
                )
            )

            # Initialize contract entities service if not already done
            try:
                await ContractEntitiesService.initialize(force_reinitialize=False)
            except Exception as e:
                logger.warning(f"ContractEntitiesService already initialized or initialization failed: {e}")

            # Prepare contract data in the expected format
            # The Azure CU result needs to be wrapped with metadata
            contract_data = {
                "filename": filename,  # Use the actual filename in blob storage (with versioning if duplicate)
                "imageQuestDocumentId": cu_result.get("result", {}).get("id", f"upload_{int(time.time())}"),
                "status": "succeeded",
                "result": cu_result.get("result", {}),
                "upload_metadata": {
                    "uploaded_by": uploaded_by,
                    "upload_date": time.time(),
                    "file_size_bytes": file_size_bytes,
                    "blob_url": blob_url,
                    "original_filename": original_filename  # Keep track of original name if user wants to see it
                }
            }

            # Import process_contract from main_contracts
            # We'll import the function directly since it's already designed for this
            import sys
            import os

            # Add web_app directory to path to import main_contracts
            web_app_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if web_app_path not in sys.path:
                sys.path.insert(0, web_app_path)

            from main_contracts import process_contract

            # Create a counter for tracking
            load_counter = Counter()

            # Set the database
            cosmos_service.set_db("caig")

            # Step 5: Load contract into CosmosDB
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.LOADING,
                    current_item=3,
                    total_items=4,
                    percentage=75.0,
                    message=f"Loading contract into database..."
                )
            )

            # Process the contract (this creates parent, clause, and chunk documents)
            # Returns the contract document ID for viewing
            contract_doc_id = await process_contract(
                nosql_svc=cosmos_service,
                ai_svc=ai_service,
                contract_data=contract_data,
                cname="contracts",  # Main contracts container
                load_counter=load_counter,
                compliance_svc=None,  # No compliance evaluation for single uploads
                compliance_enabled=False
            )

            # Persist contract entities
            await ContractEntitiesService.persist_entities()

            logger.info(f"Contract loaded successfully - ID: {contract_doc_id}, Stats: {json.dumps(load_counter.get_data())}")

            # Step 6: Mark job as completed
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.COMPLETED,
                    current_item=4,
                    total_items=4,
                    percentage=100.0,
                    message=f"Contract upload completed successfully"
                )
            )

            await job_service.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.COMPLETED,
                result_id=contract_doc_id  # Use the actual contract document ID
            )

            logger.info(f"Contract upload job completed: {job_id}, filename: {filename}, result_id: {contract_doc_id}")

        except Exception as e:
            logger.error(f"Contract upload job failed: {job_id}")
            logger.error(traceback.format_exc())

            # Update job progress to failed
            await job_service.update_job_progress(
                job_id=job_id,
                user_id=user_id,
                progress=JobProgress(
                    current_step=ProcessingStep.FAILED,
                    current_item=0,
                    total_items=4,
                    percentage=0.0,
                    message=f"Upload failed: {str(e)}"
                )
            )

            # Update job status to failed
            await job_service.update_job_status(
                job_id=job_id,
                user_id=user_id,
                status=JobStatus.FAILED,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()}
            )

            raise
