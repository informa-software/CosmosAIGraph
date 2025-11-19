"""
Evaluation Job Service

Manages async evaluation jobs for tracking progress of compliance evaluations.
Jobs auto-expire after 7 days via CosmosDB TTL.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.models.compliance_models import EvaluationJob, JobStatus, JobType
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)


class EvaluationJobService:
    """
    Service for managing evaluation jobs in CosmosDB.

    Provides job creation, progress tracking, status updates, and job retrieval.
    Jobs are automatically cleaned up after 7 days by CosmosDB TTL.
    """

    def __init__(self, cosmos_service: CosmosNoSQLService):
        """
        Initialize the evaluation job service.

        Args:
            cosmos_service: Initialized CosmosDB service instance
        """
        self.cosmos_service = cosmos_service
        self.container_name = "evaluation_jobs"

    async def create_job(
        self,
        job_type: str,
        total_items: int,
        contract_id: Optional[str] = None,
        rule_ids: Optional[List[str]] = None,
        contract_ids: Optional[List[str]] = None
    ) -> EvaluationJob:
        """
        Create a new evaluation job.

        Args:
            job_type: Type of job (evaluate_contract, evaluate_rule, etc.)
            total_items: Total number of items to process
            contract_id: For single contract evaluations
            rule_ids: List of rule IDs being evaluated
            contract_ids: List of contract IDs being evaluated

        Returns:
            Created EvaluationJob instance

        Raises:
            ValueError: If validation fails
            Exception: If CosmosDB operation fails
        """
        try:
            # Create job instance (validates fields)
            job = EvaluationJob(
                job_type=job_type,
                total_items=total_items,
                contract_id=contract_id,
                rule_ids=rule_ids or [],
                contract_ids=contract_ids or []
            )

            # Store in CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.create_item(job.to_dict())

            logger.info(f"Created evaluation job: {job.id} - {job_type} ({total_items} items)")
            return EvaluationJob.from_dict(doc)

        except ValueError as e:
            logger.error(f"Validation error creating job: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    async def get_job(self, job_id: str) -> Optional[EvaluationJob]:
        """
        Get an evaluation job by ID.

        Args:
            job_id: Job ID

        Returns:
            EvaluationJob if found, None otherwise
        """
        try:
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.point_read(job_id, job_id)  # partition key is /id

            if doc:
                return EvaluationJob.from_dict(doc)
            return None

        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            raise

    async def update_progress(
        self,
        job_id: str,
        completed: int,
        failed: int = 0
    ) -> EvaluationJob:
        """
        Update job progress.

        Args:
            job_id: Job ID
            completed: Number of items completed
            failed: Number of items that failed

        Returns:
            Updated EvaluationJob instance

        Raises:
            ValueError: If job not found
            Exception: If CosmosDB operation fails
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            # Update progress
            job.update_progress(completed, failed)

            # Save to CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.upsert_item(job.to_dict())

            logger.debug(f"Updated job {job_id} progress: {completed}/{job.total_items} (failed: {failed})")
            return EvaluationJob.from_dict(doc)

        except Exception as e:
            logger.error(f"Failed to update job progress {job_id}: {e}")
            raise

    async def add_result(self, job_id: str, result_id: str) -> EvaluationJob:
        """
        Add a result ID to a job's result list.

        Args:
            job_id: Job ID
            result_id: Result ID to add

        Returns:
            Updated EvaluationJob instance
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            # Add result ID
            job.result_ids.append(result_id)

            # Save to CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.upsert_item(job.to_dict())

            return EvaluationJob.from_dict(doc)

        except Exception as e:
            logger.error(f"Failed to add result to job {job_id}: {e}")
            raise

    async def complete_job(
        self,
        job_id: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> EvaluationJob:
        """
        Mark a job as completed or failed.

        Args:
            job_id: Job ID
            success: Whether the job completed successfully
            error_message: Error message if job failed

        Returns:
            Updated EvaluationJob instance

        Raises:
            ValueError: If job not found
            Exception: If CosmosDB operation fails
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            # Mark as complete
            job.complete(success=success, error_message=error_message)

            # Save to CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.upsert_item(job.to_dict())

            status_str = "completed" if success else "failed"
            logger.info(f"Job {job_id} {status_str}: {job.completed_items}/{job.total_items} items processed")

            return EvaluationJob.from_dict(doc)

        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            raise

    async def cancel_job(self, job_id: str) -> EvaluationJob:
        """
        Cancel a running job.

        Args:
            job_id: Job ID

        Returns:
            Updated EvaluationJob instance

        Raises:
            ValueError: If job not found
            Exception: If CosmosDB operation fails
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            # Cancel job
            job.cancel()

            # Save to CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.upsert_item(job.to_dict())

            logger.info(f"Job {job_id} cancelled")
            return EvaluationJob.from_dict(doc)

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise

    async def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50
    ) -> List[EvaluationJob]:
        """
        List evaluation jobs with optional filtering.

        Args:
            status: Filter by status (pending, in_progress, completed, failed, cancelled)
            job_type: Filter by job type
            limit: Maximum number of jobs to return

        Returns:
            List of EvaluationJob instances (most recent first)
        """
        try:
            self.cosmos_service.set_container(self.container_name)

            # Build query
            where_clauses = []
            if status:
                where_clauses.append(f"c.status = '{status}'")
            if job_type:
                where_clauses.append(f"c.job_type = '{job_type}'")

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            query = f"SELECT TOP {limit} * FROM c WHERE {where_clause} ORDER BY c.started_date DESC"

            docs = await self.cosmos_service.query_items(query, cross_partition=True)

            jobs = [EvaluationJob.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(jobs)} evaluation jobs (status={status}, type={job_type})")

            return jobs

        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            raise

    async def get_active_jobs(self) -> List[EvaluationJob]:
        """
        Get all active (pending or in_progress) jobs.

        Returns:
            List of active EvaluationJob instances
        """
        try:
            self.cosmos_service.set_container(self.container_name)

            query = f"""
                SELECT * FROM c
                WHERE c.status IN ('{JobStatus.PENDING.value}', '{JobStatus.IN_PROGRESS.value}')
                ORDER BY c.started_date DESC
            """

            docs = await self.cosmos_service.query_items(query, cross_partition=True)
            jobs = [EvaluationJob.from_dict(doc) for doc in docs]

            logger.info(f"Retrieved {len(jobs)} active jobs")
            return jobs

        except Exception as e:
            logger.error(f"Failed to get active jobs: {e}")
            raise

    async def get_jobs_by_contract(self, contract_id: str) -> List[EvaluationJob]:
        """
        Get all jobs for a specific contract.

        Args:
            contract_id: Contract ID

        Returns:
            List of EvaluationJob instances
        """
        try:
            self.cosmos_service.set_container(self.container_name)

            query = f"""
                SELECT * FROM c
                WHERE c.contract_id = '{contract_id}'
                ORDER BY c.started_date DESC
            """

            docs = await self.cosmos_service.query_items(query, cross_partition=True)
            jobs = [EvaluationJob.from_dict(doc) for doc in docs]

            logger.info(f"Retrieved {len(jobs)} jobs for contract {contract_id}")
            return jobs

        except Exception as e:
            logger.error(f"Failed to get jobs for contract {contract_id}: {e}")
            raise

    async def delete_old_jobs(self, days: int = 30) -> int:
        """
        Manually delete jobs older than specified days (backup to TTL).

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted

        Note:
            This is a backup cleanup. CosmosDB TTL (7 days) handles primary cleanup.
        """
        try:
            from datetime import timedelta

            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

            self.cosmos_service.set_container(self.container_name)

            query = f"""
                SELECT c.id FROM c
                WHERE c.started_date < '{cutoff_date}'
            """

            docs = await self.cosmos_service.query_items(query, cross_partition=True)

            deleted_count = 0
            for doc in docs:
                try:
                    await self.cosmos_service.delete_item(doc['id'], doc['id'])  # partition key is /id
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete job {doc['id']}: {e}")

            logger.info(f"Deleted {deleted_count} old jobs (older than {days} days)")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete old jobs: {e}")
            return 0
