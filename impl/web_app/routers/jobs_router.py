"""
Jobs Router

API endpoints for batch processing job management.
Handles job submission, status checking, cancellation, and retry operations.
"""

import logging
import asyncio
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.models.job_models import (
    BatchJob,
    JobStatus,
    JobType,
    ComparisonJobRequest,
    QueryJobRequest,
    SubmitJobRequest,
    SubmitJobResponse,
    JobStatusResponse,
    UserJobsResponse,
    CancelJobResponse,
    RetryJobResponse
)
from src.services.job_service import JobService
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Initialize services globally (will be initialized on first use)
_nosql_svc = None
_job_svc = None


async def get_job_service():
    """Get or initialize job service"""
    global _nosql_svc, _job_svc

    if _nosql_svc is None:
        logger.info("Initializing Job services...")
        _nosql_svc = CosmosNoSQLService()
        await _nosql_svc.initialize()
        _job_svc = JobService(_nosql_svc)
        logger.info("Job services initialized")

    return _job_svc


# ============================================================================
# Job Submission Endpoints
# ============================================================================

@router.post("/comparison", response_model=SubmitJobResponse)
async def submit_comparison_job(
    request: SubmitJobRequest,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Submit a new contract comparison batch job

    Args:
        request: Job submission request with comparison parameters and priority
        user_id: User ID (defaults to 'system')

    Returns:
        Job ID and initial status

    Example:
        POST /api/jobs/comparison?user_id=system
        Body:
        {
          "request": {
            "standardContractId": "contract_123",
            "compareContractIds": ["contract_456", "contract_789"],
            "comparisonMode": "clauses",
            "selectedClauses": ["Indemnity"],
            "modelSelection": "primary"
          },
          "priority": 5
        }
    """
    try:
        service = await get_job_service()

        # Validate request has comparison parameters
        if not request.request.get("standardContractId"):
            raise HTTPException(
                status_code=400,
                detail="Missing standardContractId in request"
            )
        if not request.request.get("compareContractIds"):
            raise HTTPException(
                status_code=400,
                detail="Missing compareContractIds in request"
            )

        # Create job
        job_id = await service.create_job(
            user_id=user_id,
            job_type=JobType.CONTRACT_COMPARISON,
            request=request.request,
            priority=request.priority
        )

        logger.info(f"Comparison job submitted: {job_id}")

        # Start background worker to process the job
        from src.services.background_worker import BackgroundWorker
        worker = BackgroundWorker()
        asyncio.create_task(worker.process_job(job_id, user_id))
        logger.info(f"Background worker started for job: {job_id}")

        return SubmitJobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Comparison job submitted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting comparison job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit comparison job: {str(e)}"
        )


@router.post("/query", response_model=SubmitJobResponse)
async def submit_query_job(
    request: SubmitJobRequest,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Submit a new contract query batch job

    Args:
        request: Job submission request with query parameters and priority
        user_id: User ID (defaults to 'system')

    Returns:
        Job ID and initial status

    Example:
        POST /api/jobs/query?user_id=system
        Body:
        {
          "request": {
            "question": "What are the payment terms?",
            "contract_ids": ["contract_123", "contract_456"],
            "modelSelection": "primary"
          },
          "priority": 5
        }
    """
    try:
        service = await get_job_service()

        # Validate request has query parameters
        if not request.request.get("question"):
            raise HTTPException(
                status_code=400,
                detail="Missing question in request"
            )
        if not request.request.get("contract_ids"):
            raise HTTPException(
                status_code=400,
                detail="Missing contract_ids in request"
            )

        # Create job
        job_id = await service.create_job(
            user_id=user_id,
            job_type=JobType.CONTRACT_QUERY,
            request=request.request,
            priority=request.priority
        )

        logger.info(f"Query job submitted: {job_id}")

        # Start background worker to process the job
        from src.services.background_worker import BackgroundWorker
        worker = BackgroundWorker()
        asyncio.create_task(worker.process_job(job_id, user_id))
        logger.info(f"Background worker started for job: {job_id}")

        return SubmitJobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Query job submitted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting query job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit query job: {str(e)}"
        )


# ============================================================================
# Job Status Endpoints
# ============================================================================

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Get status and details of a specific job

    Args:
        job_id: Job identifier
        user_id: User ID (defaults to 'system')

    Returns:
        Complete job details including status, progress, and results

    Example:
        GET /api/jobs/job_1729795200_abc123?user_id=system
    """
    try:
        service = await get_job_service()
        job = await service.get_job(job_id, user_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job not found: {job_id}"
            )

        return JobStatusResponse(job=job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=UserJobsResponse)
async def get_user_jobs(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status (comma-separated: queued,processing,completed)"),
    job_type: Optional[str] = Query(None, description="Filter by job type: contract_comparison or contract_query"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of jobs to return")
):
    """
    Get all jobs for a user with optional filtering

    Args:
        user_id: User identifier
        status: Optional comma-separated list of statuses to filter by
        job_type: Optional job type filter
        limit: Maximum number of jobs to return (default 50, max 200)

    Returns:
        List of jobs and total count

    Example:
        GET /api/jobs/user/system?status=queued,processing&limit=20
    """
    try:
        service = await get_job_service()

        # Parse status filter
        status_filter = None
        if status:
            status_list = [s.strip() for s in status.split(",")]
            # Validate statuses
            valid_statuses = [s.value for s in JobStatus]
            status_filter = []
            for s in status_list:
                if s in valid_statuses:
                    status_filter.append(JobStatus(s))
                else:
                    logger.warning(f"Invalid status value ignored: {s}")

        # Parse job type filter
        job_type_filter = None
        if job_type:
            try:
                job_type_filter = JobType(job_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid job_type: {job_type}. Must be 'contract_comparison' or 'contract_query'"
                )

        # Get jobs
        jobs = await service.get_user_jobs(
            user_id=user_id,
            status_filter=status_filter,
            job_type_filter=job_type_filter,
            limit=limit
        )

        return UserJobsResponse(
            jobs=jobs,
            total=len(jobs)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user jobs: {str(e)}"
        )


# ============================================================================
# Job Management Endpoints
# ============================================================================

@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: str,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Cancel a queued or processing job

    Args:
        job_id: Job identifier
        user_id: User ID (defaults to 'system')

    Returns:
        Cancellation status

    Example:
        POST /api/jobs/job_1729795200_abc123/cancel?user_id=system
    """
    try:
        service = await get_job_service()
        success = await service.cancel_job(job_id, user_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job {job_id}. Job may not exist or is already in a final state."
            )

        return CancelJobResponse(
            job_id=job_id,
            success=True,
            message="Job cancelled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.post("/{job_id}/retry", response_model=RetryJobResponse)
async def retry_job(
    job_id: str,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Retry a failed job by creating a new job with the same parameters

    Args:
        job_id: Original job identifier
        user_id: User ID (defaults to 'system')

    Returns:
        New job ID

    Example:
        POST /api/jobs/job_1729795200_abc123/retry?user_id=system
    """
    try:
        service = await get_job_service()
        new_job_id = await service.retry_job(job_id, user_id)

        if not new_job_id:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry job {job_id}. Job may not exist or is not in failed status."
            )

        return RetryJobResponse(
            new_job_id=new_job_id,
            original_job_id=job_id,
            message="Job retry submitted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry job: {str(e)}"
        )


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Delete a job (only for completed/failed/cancelled jobs)

    Args:
        job_id: Job identifier
        user_id: User ID (for partition key)

    Returns:
        Success message

    Example:
        DELETE /api/jobs/job_123456?user_id=system
    """
    try:
        service = await get_job_service()
        success = await service.delete_job(job_id, user_id)

        if success:
            logger.info(f"Job {job_id} deleted successfully")
            return {
                "success": True,
                "message": f"Job {job_id} deleted successfully",
                "job_id": job_id
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete job (may not exist or not in final state)"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job: {str(e)}"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Health check endpoint for job service

    Returns:
        Service status
    """
    try:
        service = await get_job_service()
        return {
            "status": "healthy",
            "service": "jobs",
            "timestamp": "2025-01-10T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


# ============================================================================
# Server-Sent Events (SSE) Endpoints
# ============================================================================

@router.get("/{job_id}/stream")
async def stream_job_progress(
    job_id: str,
    user_id: str = Query(default="system", description="User ID")
):
    """
    Stream real-time progress updates for a specific job via Server-Sent Events

    Args:
        job_id: Job identifier
        user_id: User ID (defaults to 'system')

    Returns:
        SSE stream with job progress updates

    Example:
        GET /api/jobs/job_1729795200_abc123/stream?user_id=system

    Event Format:
        event: job_update
        data: {"job_id": "...", "status": "...", "progress": {...}}

        event: heartbeat
        data: {"timestamp": "2025-01-10T12:00:00Z"}

        event: error
        data: {"error": "Job not found"}
    """
    async def generate_events():
        try:
            service = await get_job_service()
            last_progress = None
            last_status = None
            heartbeat_counter = 0

            while True:
                try:
                    # Get current job state
                    job = await service.get_job(job_id, user_id)

                    if not job:
                        # Job not found
                        yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                        break

                    # Check if status or progress changed
                    status_changed = last_status != job.status
                    progress_changed = (
                        last_progress is None or
                        last_progress.percentage != job.progress.percentage or
                        last_progress.message != job.progress.message
                    )

                    if status_changed or progress_changed:
                        # Send update
                        job_data = {
                            "job_id": job.job_id,
                            "status": job.status.value,
                            "progress": {
                                "current_step": job.progress.current_step.value,
                                "percentage": job.progress.percentage,
                                "message": job.progress.message,
                                "current_item": job.progress.current_item,
                                "total_items": job.progress.total_items
                            },
                            "result_id": job.result_id,
                            "error_message": job.error_message
                        }

                        yield f"event: job_update\ndata: {json.dumps(job_data)}\n\n"

                        last_progress = job.progress
                        last_status = job.status

                    # Check if job is in final state
                    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                        logger.info(f"Job {job_id} reached final state: {job.status}")
                        break

                    # Send heartbeat every 10 iterations (~15 seconds)
                    heartbeat_counter += 1
                    if heartbeat_counter >= 10:
                        yield f"event: heartbeat\ndata: {json.dumps({'timestamp': '2025-01-10T12:00:00Z'})}\n\n"
                        heartbeat_counter = 0

                    # Wait before next poll
                    await asyncio.sleep(1.5)

                except Exception as e:
                    logger.error(f"Error streaming job {job_id}: {str(e)}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    break

        except Exception as e:
            logger.error(f"Failed to initialize SSE stream: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )


@router.get("/user/{user_id}/stream")
async def stream_user_jobs(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status (comma-separated)")
):
    """
    Stream real-time updates for all jobs belonging to a user via Server-Sent Events

    Args:
        user_id: User identifier
        status: Optional comma-separated list of statuses to filter by

    Returns:
        SSE stream with updates for all matching user jobs

    Example:
        GET /api/jobs/user/system/stream?status=queued,processing

    Event Format:
        event: jobs_update
        data: {"jobs": [...], "counts": {"queued": 0, "processing": 1, ...}}

        event: heartbeat
        data: {"timestamp": "2025-01-10T12:00:00Z"}
    """
    async def generate_events():
        try:
            service = await get_job_service()
            last_job_states = {}
            heartbeat_counter = 0

            # Parse status filter
            status_filter = None
            if status:
                status_list = [s.strip() for s in status.split(",")]
                valid_statuses = [s.value for s in JobStatus]
                status_filter = []
                for s in status_list:
                    if s in valid_statuses:
                        status_filter.append(JobStatus(s))

            while True:
                try:
                    # Get current jobs
                    jobs = await service.get_user_jobs(
                        user_id=user_id,
                        status_filter=status_filter,
                        limit=50
                    )

                    # Get counts
                    counts = await service.get_active_jobs_count(user_id)

                    # Check for changes
                    current_states = {
                        job.job_id: {
                            "status": job.status.value,
                            "percentage": job.progress.percentage,
                            "message": job.progress.message
                        }
                        for job in jobs
                    }

                    if current_states != last_job_states:
                        # Send update
                        jobs_data = {
                            "jobs": [
                                {
                                    "job_id": job.job_id,
                                    "job_type": job.job_type.value,
                                    "status": job.status.value,
                                    "progress": {
                                        "percentage": job.progress.percentage,
                                        "message": job.progress.message
                                    },
                                    "created_date": job.created_date.isoformat(),
                                    "completed_date": job.completed_date.isoformat() if job.completed_date else None,
                                    "elapsed_time": job.elapsed_time,
                                    "result_id": job.result_id
                                }
                                for job in jobs
                            ],
                            "counts": counts
                        }

                        yield f"event: jobs_update\ndata: {json.dumps(jobs_data)}\n\n"
                        last_job_states = current_states

                    # Send heartbeat every 10 iterations (~15 seconds)
                    heartbeat_counter += 1
                    if heartbeat_counter >= 10:
                        yield f"event: heartbeat\ndata: {json.dumps({'timestamp': '2025-01-10T12:00:00Z'})}\n\n"
                        heartbeat_counter = 0

                    # Wait before next poll
                    await asyncio.sleep(1.5)

                except Exception as e:
                    logger.error(f"Error streaming user jobs for {user_id}: {str(e)}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    break

        except Exception as e:
            logger.error(f"Failed to initialize SSE stream: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
