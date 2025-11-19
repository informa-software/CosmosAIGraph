"""
Word Add-in Router

API endpoints for managing Word Add-in evaluation sessions.
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.models.word_addin_models import (
    WordAddinEvaluationSession,
    CreateSessionRequest,
    UpdateSessionRequest,
    SessionListResponse
)
from src.services.word_addin_service import WordAddinService
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/word-addin", tags=["word-addin"])

# Initialize services globally (will be initialized on first use)
_nosql_svc = None
_word_addin_svc = None


async def get_word_addin_service():
    """Get or initialize word add-in service"""
    global _nosql_svc, _word_addin_svc

    if _nosql_svc is None:
        logger.info("Initializing Word Add-in services...")
        _nosql_svc = CosmosNoSQLService()
        await _nosql_svc.initialize()
        _word_addin_svc = WordAddinService(_nosql_svc)
        logger.info("Word Add-in services initialized")

    return _word_addin_svc


@router.post("/sessions", response_model=WordAddinEvaluationSession)
async def create_session(request: CreateSessionRequest):
    """
    Create a new Word Add-in evaluation session

    Args:
        request: Session creation parameters

    Returns:
        Created session with generated evaluation_id
    """
    try:
        service = await get_word_addin_service()
        session = await service.create_session(request)
        return session

    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/sessions/{evaluation_id}", response_model=WordAddinEvaluationSession)
async def get_session(evaluation_id: str):
    """
    Get a specific evaluation session

    Args:
        evaluation_id: Session identifier

    Returns:
        Session object
    """
    try:
        service = await get_word_addin_service()
        session = await service.get_session(evaluation_id)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {evaluation_id}")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")


@router.patch("/sessions/{evaluation_id}", response_model=WordAddinEvaluationSession)
async def update_session(evaluation_id: str, update: UpdateSessionRequest):
    """
    Update an existing evaluation session

    Args:
        evaluation_id: Session identifier
        update: Fields to update

    Returns:
        Updated session object
    """
    try:
        service = await get_word_addin_service()
        session = await service.update_session(evaluation_id, update)

        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {evaluation_id}")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    rule_set_id: Optional[str] = Query(None, description="Filter by rule set ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)")
):
    """
    List evaluation sessions with optional filters

    Args:
        limit: Maximum sessions to return (1-100)
        offset: Number of sessions to skip for pagination
        rule_set_id: Optional filter by rule set
        status: Optional filter by status
        start_date: Optional filter by start date
        end_date: Optional filter by end date

    Returns:
        List of sessions with pagination info
    """
    try:
        service = await get_word_addin_service()
        sessions = await service.list_sessions(
            limit=limit,
            offset=offset,
            rule_set_id=rule_set_id,
            status=status,
            start_date=start_date,
            end_date=end_date
        )

        # Get total count (for pagination)
        # Note: This is a simplified approach. For production, you might want
        # a separate count query for better performance
        total_count = len(sessions) if len(sessions) < limit else limit + 1

        return SessionListResponse(
            sessions=sessions,
            total_count=total_count,
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit
        )

    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/sessions/by-contract/{contract_id}", response_model=List[WordAddinEvaluationSession])
async def get_sessions_by_contract(contract_id: str):
    """
    Get sessions associated with a specific contract

    Args:
        contract_id: Contract identifier (original or revised)

    Returns:
        List of sessions containing this contract
    """
    try:
        service = await get_word_addin_service()
        sessions = await service.get_sessions_by_contract(contract_id)
        return sessions

    except Exception as e:
        logger.error(f"Error retrieving sessions for contract {contract_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@router.delete("/sessions/{evaluation_id}")
async def delete_session(evaluation_id: str):
    """
    Delete an evaluation session

    Args:
        evaluation_id: Session identifier

    Returns:
        Success message
    """
    try:
        service = await get_word_addin_service()
        success = await service.delete_session(evaluation_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Session not found: {evaluation_id}")

        return {"message": f"Session deleted: {evaluation_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/statistics")
async def get_statistics():
    """
    Get aggregate statistics about Word Add-in usage

    Returns:
        Dictionary with usage statistics
    """
    try:
        service = await get_word_addin_service()
        stats = await service.get_session_statistics()
        return stats

    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")
