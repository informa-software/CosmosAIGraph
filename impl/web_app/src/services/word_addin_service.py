"""
Word Add-in Service

Manages evaluation sessions from the Word Add-in, including:
- Session creation and tracking
- Status updates
- Historical query
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.models.word_addin_models import (
    WordAddinEvaluationSession,
    CreateSessionRequest,
    UpdateSessionRequest,
    TrackChangesInfo,
    ComparisonSummary,
    ComplianceSummary
)
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)


class WordAddinService:
    """Service for managing Word Add-in evaluation sessions"""

    def __init__(self, cosmos_service: CosmosNoSQLService):
        self.cosmos_service = cosmos_service
        self.container_name = "word_addin_evaluations"

    async def create_session(self, request: CreateSessionRequest) -> WordAddinEvaluationSession:
        """
        Create a new evaluation session

        Args:
            request: Session creation request

        Returns:
            Created session with generated evaluation_id
        """
        # Generate unique session ID
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        evaluation_id = f"session_{timestamp}_{uuid4().hex[:8]}"

        logger.info(f"Creating Word Add-in session: {evaluation_id}")

        # Create session object
        session = WordAddinEvaluationSession(
            evaluation_id=evaluation_id,
            document_title=request.document_title,
            document_character_count=request.document_character_count,
            track_changes_info=request.track_changes_info,
            original_contract_id=request.original_contract_id,
            revised_contract_id=request.revised_contract_id,
            rule_set_id=request.rule_set_id,
            rule_set_name=request.rule_set_name,
            compliance_mode=request.compliance_mode,
            user_id=request.user_id,
            client_version=request.client_version,
            status="in_progress"
        )

        # Store in CosmosDB
        self.cosmos_service.set_container(self.container_name)
        session_dict = session.model_dump(mode='json')

        # Add required CosmosDB 'id' field
        session_dict['id'] = evaluation_id

        await self.cosmos_service.upsert_item(session_dict)

        logger.info(f"Session created successfully: {evaluation_id}")
        return session

    async def get_session(self, evaluation_id: str) -> Optional[WordAddinEvaluationSession]:
        """
        Retrieve a session by ID

        Args:
            evaluation_id: Session identifier

        Returns:
            Session object or None if not found
        """
        self.cosmos_service.set_container(self.container_name)

        try:
            item = await self.cosmos_service.point_read(
                id=evaluation_id,
                pk=evaluation_id
            )

            if item:
                return WordAddinEvaluationSession(**item)
            return None

        except Exception as e:
            logger.error(f"Error retrieving session {evaluation_id}: {str(e)}")
            return None

    async def update_session(
        self,
        evaluation_id: str,
        update: UpdateSessionRequest
    ) -> Optional[WordAddinEvaluationSession]:
        """
        Update an existing session

        Args:
            evaluation_id: Session identifier
            update: Fields to update

        Returns:
            Updated session or None if not found
        """
        logger.info(f"Updating session: {evaluation_id}")

        # Get existing session
        session = await self.get_session(evaluation_id)
        if not session:
            logger.warning(f"Session not found: {evaluation_id}")
            return None

        # Update fields with proper model conversion
        update_dict = update.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if value is not None:
                # Convert nested dicts to proper Pydantic models
                if field == 'comparison_summary' and isinstance(value, dict):
                    from src.models.word_addin_models import ComparisonSummary
                    value = ComparisonSummary(**value)
                elif field == 'compliance_summary' and isinstance(value, dict):
                    from src.models.word_addin_models import ComplianceSummary
                    value = ComplianceSummary(**value)

                setattr(session, field, value)

        # Update completion time if status changed to completed or failed
        if update.status in ['completed', 'failed']:
            session.completed_at = datetime.utcnow()
            if session.started_at:
                duration = (session.completed_at - session.started_at).total_seconds()
                session.duration_seconds = duration

        # Save to database
        self.cosmos_service.set_container(self.container_name)
        session_dict = session.model_dump(mode='json')

        # Add required CosmosDB 'id' field
        session_dict['id'] = evaluation_id

        await self.cosmos_service.upsert_item(session_dict)

        logger.info(f"Session updated successfully: {evaluation_id}")
        return session

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        rule_set_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[WordAddinEvaluationSession]:
        """
        List evaluation sessions with optional filters

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            rule_set_id: Filter by rule set
            status: Filter by status
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)

        Returns:
            List of sessions
        """
        self.cosmos_service.set_container(self.container_name)

        # Build query
        query = "SELECT * FROM c WHERE 1=1"
        parameters = []

        if rule_set_id:
            query += " AND c.rule_set_id = @rule_set_id"
            parameters.append({"name": "@rule_set_id", "value": rule_set_id})

        if status:
            query += " AND c.status = @status"
            parameters.append({"name": "@status", "value": status})

        if start_date:
            query += " AND c.started_at >= @start_date"
            parameters.append({"name": "@start_date", "value": start_date.isoformat()})

        if end_date:
            query += " AND c.started_at <= @end_date"
            parameters.append({"name": "@end_date", "value": end_date.isoformat()})

        # Order by most recent first
        query += " ORDER BY c.started_at DESC"

        # Add pagination
        query += f" OFFSET {offset} LIMIT {limit}"

        logger.info(f"Querying sessions with filters: rule_set={rule_set_id}, status={status}")

        items = await self.cosmos_service.query_items(
            query,
            parameters=parameters if parameters else None,
            cross_partition=True
        )

        sessions = [WordAddinEvaluationSession(**item) for item in items]
        logger.info(f"Retrieved {len(sessions)} sessions")

        return sessions

    async def get_sessions_by_contract(self, contract_id: str) -> List[WordAddinEvaluationSession]:
        """
        Get sessions associated with a specific contract ID

        Args:
            contract_id: Contract identifier (original or revised)

        Returns:
            List of sessions
        """
        self.cosmos_service.set_container(self.container_name)

        query = """
            SELECT * FROM c
            WHERE c.original_contract_id = @contract_id
               OR c.revised_contract_id = @contract_id
            ORDER BY c.started_at DESC
        """

        parameters = [{"name": "@contract_id", "value": contract_id}]

        items = await self.cosmos_service.query_items(
            query,
            parameters=parameters,
            cross_partition=True
        )

        return [WordAddinEvaluationSession(**item) for item in items]

    async def delete_session(self, evaluation_id: str) -> bool:
        """
        Delete a session

        Args:
            evaluation_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting session: {evaluation_id}")

        self.cosmos_service.set_container(self.container_name)

        try:
            await self.cosmos_service.delete_item(
                id=evaluation_id,
                pk=evaluation_id
            )
            logger.info(f"Session deleted: {evaluation_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session {evaluation_id}: {str(e)}")
            return False

    async def get_session_statistics(self) -> dict:
        """
        Get aggregate statistics about Word Add-in usage

        Returns:
            Dictionary with statistics
        """
        self.cosmos_service.set_container(self.container_name)

        # Total sessions
        total_query = "SELECT VALUE COUNT(1) FROM c"
        total_result = await self.cosmos_service.query_items(total_query, cross_partition=True)
        total_sessions = total_result[0] if total_result else 0

        # Sessions by status
        status_query = """
            SELECT c.status, COUNT(1) as count
            FROM c
            GROUP BY c.status
        """
        status_results = await self.cosmos_service.query_items(status_query, cross_partition=True)

        # Sessions by compliance mode
        mode_query = """
            SELECT c.compliance_mode, COUNT(1) as count
            FROM c
            GROUP BY c.compliance_mode
        """
        mode_results = await self.cosmos_service.query_items(mode_query, cross_partition=True)

        # Average duration
        duration_query = """
            SELECT AVG(c.duration_seconds) as avg_duration
            FROM c
            WHERE c.duration_seconds != null
        """
        duration_result = await self.cosmos_service.query_items(duration_query, cross_partition=True)
        avg_duration = duration_result[0].get('avg_duration') if duration_result else None

        return {
            "total_sessions": total_sessions,
            "by_status": {r['status']: r['count'] for r in status_results},
            "by_compliance_mode": {r['compliance_mode']: r['count'] for r in mode_results},
            "average_duration_seconds": avg_duration
        }
