"""
Analysis Results Router

API endpoints for storing, retrieving, and managing analysis results.
Supports both comparison and query results for PDF generation.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.models.analysis_results_models import (
    AnalysisResult,
    SaveComparisonRequest,
    SaveQueryRequest,
    SaveResultResponse,
    EmailPDFRequest,
    ResultListResponse
)
from src.services.analysis_results_service import AnalysisResultsService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.pdf_generation_service import PDFGenerationService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/analysis-results", tags=["analysis-results"])

# Initialize services globally (will be initialized on first use)
_nosql_svc = None
_results_svc = None
_pdf_svc = None


async def get_results_service():
    """Get or initialize analysis results service"""
    global _nosql_svc, _results_svc

    if _nosql_svc is None:
        logger.info("Initializing Analysis Results services...")
        _nosql_svc = CosmosNoSQLService()
        await _nosql_svc.initialize()
        _results_svc = AnalysisResultsService(_nosql_svc)
        logger.info("Analysis Results services initialized")

    return _results_svc


def get_pdf_service():
    """Get or initialize PDF generation service"""
    global _pdf_svc

    if _pdf_svc is None:
        logger.info("Initializing PDF generation service...")
        _pdf_svc = PDFGenerationService()
        logger.info("PDF generation service initialized")

    return _pdf_svc


# ============================================================================
# Save Results Endpoints
# ============================================================================

@router.post("/comparison", response_model=SaveResultResponse)
async def save_comparison_result(request: SaveComparisonRequest):
    """
    Store comparison results for later PDF generation and historical tracking

    Args:
        request: Comparison result data including:
            - user_id
            - standard_contract_id
            - compare_contract_ids
            - comparison_mode ("full" or "clauses")
            - results (full comparison response)

    Returns:
        result_id and success message
    """
    try:
        service = await get_results_service()
        result_id = await service.save_comparison_result(request)

        return SaveResultResponse(
            result_id=result_id,
            message="Comparison results saved successfully"
        )

    except Exception as e:
        logger.error(f"Error saving comparison result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save comparison results: {str(e)}"
        )


@router.post("/query", response_model=SaveResultResponse)
async def save_query_result(request: SaveQueryRequest):
    """
    Store query results for later PDF generation and historical tracking

    Args:
        request: Query result data including:
            - user_id
            - query_text (natural language question)
            - contracts_queried (list of {contract_id, filename, title})
            - results (query response with rankings)

    Returns:
        result_id and success message
    """
    try:
        service = await get_results_service()
        result_id = await service.save_query_result(request)

        return SaveResultResponse(
            result_id=result_id,
            message="Query results saved successfully"
        )

    except Exception as e:
        logger.error(f"Error saving query result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save query results: {str(e)}"
        )


# ============================================================================
# Retrieve Results Endpoints
# ============================================================================

@router.get("/results/{result_id}", response_model=AnalysisResult)
async def get_result(
    result_id: str,
    user_id: str = Query(..., description="User ID for authorization")
):
    """
    Retrieve a specific analysis result

    Args:
        result_id: Result identifier
        user_id: User identifier (for authorization)

    Returns:
        Full AnalysisResult object
    """
    try:
        service = await get_results_service()
        result = await service.get_result(result_id, user_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Result not found: {result_id}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve result: {str(e)}"
        )


@router.get("/user/{user_id}/results", response_model=ResultListResponse)
async def list_user_results(
    user_id: str,
    result_type: Optional[str] = Query(None, description="Filter by 'comparison' or 'query'"),
    limit: int = Query(50, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List all results for a user with optional filters

    Args:
        user_id: User identifier
        result_type: Optional filter by result type
        limit: Maximum number of results (1-100)
        offset: Pagination offset

    Returns:
        List of results with pagination info
    """
    try:
        service = await get_results_service()
        results = await service.list_user_results(
            user_id=user_id,
            result_type=result_type,
            limit=limit,
            offset=offset
        )

        # Calculate pagination info
        total_count = len(results)  # Simplified - in production, do separate count query
        page = (offset // limit) + 1 if limit > 0 else 1

        return ResultListResponse(
            results=results,
            total_count=total_count,
            page=page,
            page_size=limit
        )

    except Exception as e:
        logger.error(f"Error listing results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list results: {str(e)}"
        )


@router.get("/user/{user_id}/statistics")
async def get_user_statistics(user_id: str):
    """
    Get aggregate statistics for a user's results

    Args:
        user_id: User identifier

    Returns:
        Dictionary with usage statistics
    """
    try:
        service = await get_results_service()
        stats = await service.get_user_statistics(user_id)

        return stats

    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# ============================================================================
# PDF Generation Endpoints (Placeholder - will implement in next phase)
# ============================================================================

@router.get("/results/{result_id}/pdf")
async def generate_pdf(
    result_id: str,
    user_id: str = Query(..., description="User ID for authorization")
):
    """
    Generate and download PDF from stored result

    Args:
        result_id: Result identifier
        user_id: User identifier

    Returns:
        PDF file as streaming response
    """
    try:
        # Get the result
        results_service = await get_results_service()
        result = await results_service.get_result(result_id, user_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Result not found: {result_id}"
            )

        # Generate PDF
        pdf_service = get_pdf_service()
        pdf_bytes = await pdf_service.generate_pdf(result)

        # Update result with PDF metadata
        await pdf_service.save_pdf_metadata(
            result=result,
            pdf_size_bytes=len(pdf_bytes)
        )

        # Update in database
        results_service.cosmos_service.set_container("analysis_results")
        await results_service.cosmos_service.upsert_item(result.model_dump(mode='json'))

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.result_type}_report_{timestamp}.pdf"

        logger.info(f"Generated PDF: {filename} ({len(pdf_bytes)} bytes)")

        # Return PDF as download
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.post("/results/{result_id}/email")
async def email_pdf(result_id: str, request: EmailPDFRequest):
    """
    Generate PDF and email to recipients

    NOTE: Email service will be implemented in Phase 3

    Args:
        result_id: Result identifier
        request: Email parameters (recipients, message)

    Returns:
        Success message with email ID
    """
    # TODO: Implement in Phase 3 with EmailService
    raise HTTPException(
        status_code=501,
        detail="Email functionality not yet implemented - coming in Phase 3"
    )


# ============================================================================
# Delete Endpoint
# ============================================================================

@router.delete("/results/{result_id}")
async def delete_result(
    result_id: str,
    user_id: str = Query(..., description="User ID for authorization")
):
    """
    Delete an analysis result

    Args:
        result_id: Result identifier
        user_id: User identifier (for authorization)

    Returns:
        Success message
    """
    try:
        service = await get_results_service()
        success = await service.delete_result(result_id, user_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Result not found: {result_id}"
            )

        return {"message": f"Result deleted: {result_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting result: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete result: {str(e)}"
        )
