"""
Job Service

Manages batch processing job queue for contract comparisons and queries.
Handles job creation, status updates, progress tracking, and job lifecycle management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from src.models.job_models import (
    BatchJob,
    JobStatus,
    JobType,
    JobProgress,
    ProcessingStep,
    ComparisonJobRequest,
    QueryJobRequest
)
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing batch processing jobs"""

    def __init__(self, cosmos_service: CosmosNoSQLService):
        self.cosmos_service = cosmos_service
        self.container_name = "job_queue"

    async def create_job(
        self,
        user_id: str,
        job_type: JobType,
        request: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """
        Create a new batch processing job

        Args:
            user_id: User who submitted the job
            job_type: Type of job (comparison or query)
            request: Job request parameters
            priority: Job priority (1-10, 10 is highest)

        Returns:
            job_id: Unique identifier for the created job
        """
        # Generate unique job ID
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        job_id = f"job_{timestamp}_{uuid4().hex[:8]}"

        logger.info(f"Creating {job_type} job: {job_id}")
        logger.info(f"  - User: {user_id}")
        logger.info(f"  - Priority: {priority}")

        # Create initial progress
        progress = JobProgress(
            current_step=ProcessingStep.QUEUED,
            percentage=0.0,
            message="Job queued and waiting to be processed"
        )

        # Create job document
        job = BatchJob(
            id=job_id,
            job_id=job_id,
            job_type=job_type,
            user_id=user_id,
            status=JobStatus.QUEUED,
            priority=priority,
            request=request,
            progress=progress,
            created_date=datetime.utcnow()
        )

        # Store in CosmosDB
        self.cosmos_service.set_container(self.container_name)
        job_dict = job.model_dump(mode='json')

        await self.cosmos_service.upsert_item(job_dict)

        logger.info(f"Job created successfully: {job_id}")
        return job_id

    async def get_job(self, job_id: str, user_id: str) -> Optional[BatchJob]:
        """
        Get job by ID

        Args:
            job_id: Job identifier
            user_id: User ID (partition key)

        Returns:
            BatchJob or None if not found
        """
        self.cosmos_service.set_container(self.container_name)

        query = """
        SELECT * FROM c
        WHERE c.job_id = @job_id
          AND c.user_id = @user_id
        """

        parameters = [
            {"name": "@job_id", "value": job_id},
            {"name": "@user_id", "value": user_id}
        ]

        items = await self.cosmos_service.parameterized_query(query, parameters)

        if not items:
            logger.warning(f"Job not found: {job_id}")
            return None

        return BatchJob(**items[0])

    async def get_user_jobs(
        self,
        user_id: str,
        status_filter: Optional[List[JobStatus]] = None,
        job_type_filter: Optional[JobType] = None,
        limit: int = 50
    ) -> List[BatchJob]:
        """
        Get all jobs for a user with optional filtering

        Args:
            user_id: User identifier
            status_filter: List of statuses to filter by (e.g., ["queued", "processing"])
            job_type_filter: Optional job type filter
            limit: Maximum number of jobs to return

        Returns:
            List of BatchJob objects
        """
        self.cosmos_service.set_container(self.container_name)

        # Build query
        query = "SELECT * FROM c WHERE c.user_id = @user_id"
        parameters = [{"name": "@user_id", "value": user_id}]

        # Add status filter
        if status_filter:
            status_values = [s.value if isinstance(s, JobStatus) else s for s in status_filter]
            placeholders = ", ".join([f"@status{i}" for i in range(len(status_values))])
            query += f" AND c.status IN ({placeholders})"
            for i, status in enumerate(status_values):
                parameters.append({"name": f"@status{i}", "value": status})

        # Add job type filter
        if job_type_filter:
            job_type_value = job_type_filter.value if isinstance(job_type_filter, JobType) else job_type_filter
            query += " AND c.job_type = @job_type"
            parameters.append({"name": "@job_type", "value": job_type_value})

        # Order by created date descending (most recent first)
        query += " ORDER BY c.created_date DESC"

        # Execute query
        items = await self.cosmos_service.parameterized_query(query, parameters, max_items=limit)

        logger.info(f"Found {len(items)} jobs for user {user_id}")

        return [BatchJob(**item) for item in items]

    async def update_job_status(
        self,
        job_id: str,
        user_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        result_id: Optional[str] = None
    ) -> bool:
        """
        Update job status

        Args:
            job_id: Job identifier
            user_id: User ID (partition key)
            status: New job status
            error_message: Optional error message (for failed jobs)
            error_details: Optional detailed error information
            result_id: Optional result ID (for completed jobs)

        Returns:
            True if updated successfully, False otherwise
        """
        # Get current job
        job = await self.get_job(job_id, user_id)
        if not job:
            logger.error(f"Cannot update status for non-existent job: {job_id}")
            return False

        logger.info(f"Updating job {job_id} status: {job.status} → {status}")

        # Update status
        job.status = status

        # Update timestamps
        if status == JobStatus.PROCESSING and not job.started_date:
            job.started_date = datetime.utcnow()

        if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_date = datetime.utcnow()
            if job.started_date:
                job.elapsed_time = (job.completed_date - job.started_date).total_seconds()

        # Update error information
        if status == JobStatus.FAILED:
            job.error_message = error_message
            job.error_details = error_details

        # Update result ID
        if status == JobStatus.COMPLETED and result_id:
            job.result_id = result_id

        # Save to database
        self.cosmos_service.set_container(self.container_name)
        job_dict = job.model_dump(mode='json')

        await self.cosmos_service.upsert_item(job_dict)

        logger.info(f"Job status updated successfully: {job_id}")
        return True

    async def update_job_progress(
        self,
        job_id: str,
        user_id: str,
        progress: JobProgress
    ) -> bool:
        """
        Update job progress information

        Args:
            job_id: Job identifier
            user_id: User ID (partition key)
            progress: New progress information

        Returns:
            True if updated successfully, False otherwise
        """
        # Get current job
        job = await self.get_job(job_id, user_id)
        if not job:
            logger.error(f"Cannot update progress for non-existent job: {job_id}")
            return False

        logger.debug(f"Updating job {job_id} progress: {progress.percentage}% - {progress.message}")

        # Update progress
        job.progress = progress

        # Save to database
        self.cosmos_service.set_container(self.container_name)
        job_dict = job.model_dump(mode='json')

        await self.cosmos_service.upsert_item(job_dict)

        return True

    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """
        Cancel a queued or processing job

        Args:
            job_id: Job identifier
            user_id: User ID (partition key)

        Returns:
            True if cancelled successfully, False otherwise
        """
        # Get current job
        job = await self.get_job(job_id, user_id)
        if not job:
            logger.error(f"Cannot cancel non-existent job: {job_id}")
            return False

        # Check if job can be cancelled
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            logger.warning(f"Cannot cancel job in {job.status} status: {job_id}")
            return False

        logger.info(f"Cancelling job: {job_id}")

        # Update status to cancelled
        return await self.update_job_status(
            job_id=job_id,
            user_id=user_id,
            status=JobStatus.CANCELLED
        )

    async def retry_job(self, job_id: str, user_id: str) -> Optional[str]:
        """
        Create a new job from a failed job

        Args:
            job_id: Original job identifier
            user_id: User ID (partition key)

        Returns:
            new_job_id: ID of the new job, or None if retry failed
        """
        # Get original job
        original_job = await self.get_job(job_id, user_id)
        if not original_job:
            logger.error(f"Cannot retry non-existent job: {job_id}")
            return None

        # Check if job can be retried
        if original_job.status != JobStatus.FAILED:
            logger.warning(f"Cannot retry job in {original_job.status} status: {job_id}")
            return None

        logger.info(f"Retrying failed job: {job_id}")

        # Create new job with same parameters
        new_job_id = await self.create_job(
            user_id=user_id,
            job_type=original_job.job_type,
            request=original_job.request,
            priority=original_job.priority
        )

        logger.info(f"Retry job created: {new_job_id} (from {job_id})")
        return new_job_id

    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """
        Delete a job from the queue (only for completed/failed/cancelled jobs)

        Args:
            job_id: Job identifier
            user_id: User ID (partition key)

        Returns:
            True if deleted successfully, False otherwise
        """
        # Get current job
        job = await self.get_job(job_id, user_id)
        if not job:
            logger.error(f"Cannot delete non-existent job: {job_id}")
            return False

        # Only allow deletion of finished jobs
        if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            logger.warning(f"Cannot delete job in {job.status} status: {job_id}")
            return False

        logger.info(f"Deleting job: {job_id}")

        # Delete from CosmosDB
        self.cosmos_service.set_container(self.container_name)
        try:
            await self.cosmos_service.delete_item(job_id, user_id)
            logger.info(f"Job deleted successfully: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            return False

    async def get_next_job(self) -> Optional[BatchJob]:
        """
        Get the next queued job to process (highest priority first)

        Used by background workers to fetch jobs from the queue.

        Returns:
            BatchJob or None if no jobs available
        """
        self.cosmos_service.set_container(self.container_name)

        # Query for queued jobs, ordered by priority (desc) then created_date (asc)
        # Note: CosmosDB will use composite index (status, priority, created_date)
        query = """
        SELECT TOP 1 * FROM c
        WHERE c.status = 'queued'
        ORDER BY c.priority DESC, c.created_date ASC
        """

        items = await self.cosmos_service.query_items(query)

        if not items:
            return None

        job = BatchJob(**items[0])
        logger.info(f"Retrieved next queued job: {job.job_id} (priority: {job.priority})")

        return job

    async def get_active_jobs_count(self, user_id: str) -> Dict[str, int]:
        """
        Get count of active jobs by status for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary with counts by status
        """
        self.cosmos_service.set_container(self.container_name)

        # Fetch all jobs for user and count in Python
        # (GROUP BY not supported by CosmosDB SDK)
        query = """
        SELECT c.status
        FROM c
        WHERE c.user_id = @user_id
        """

        parameters = [{"name": "@user_id", "value": user_id}]

        items = await self.cosmos_service.parameterized_query(query, parameters)

        # Count by status in Python
        counts = {
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }

        for item in items:
            status = item.get("status", "")
            if status in counts:
                counts[status] += 1

        return counts
