"""
FastAPI router for Clause Library endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import logging

from src.models.clause_library_models import (
    Clause, ClauseCategory, SystemVariables, ClauseComparison,
    CreateClauseRequest, UpdateClauseRequest, CreateVersionRequest,
    CompareClauseRequest, SuggestClauseRequest, CreateCategoryRequest,
    CreateCustomVariableRequest, CategoryTreeNode, ClauseListResponse,
    SearchClausesRequest, ClauseVariable
)
from src.services.clause_library_service import ClauseLibraryService

logger = logging.getLogger(__name__)

# Create router with explicit configuration
router = APIRouter(prefix="/api/clause-library", tags=["clause-library"])
logger.error(f"Clause library router created with prefix: {router.prefix}, id: {id(router)}")


# Dependency to get service instance
# NOTE: This will be set during app startup
_clause_service: Optional[ClauseLibraryService] = None


def get_clause_service() -> ClauseLibraryService:
    """Get clause library service instance."""
    if _clause_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clause library service not initialized"
        )
    return _clause_service


def set_clause_service(service: ClauseLibraryService):
    """Set clause library service instance."""
    global _clause_service
    _clause_service = service


# ========== Test Endpoint ==========

@router.get("/ping", include_in_schema=True)
async def ping():
    """Simple ping endpoint to verify router is working."""
    return {"status": "ok", "message": "Clause library router is active"}

@router.get("/test")
async def test():
    """Another simple test endpoint."""
    return {"test": "working"}


# ========== Clause Endpoints ==========

@router.post("/clauses", response_model=Clause, status_code=status.HTTP_201_CREATED)
async def create_clause(
    request: CreateClauseRequest,
    user_email: str = "user@example.com",  # TODO: Get from auth
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Create a new clause in the library."""
    try:
        return await service.create_clause(request, user_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating clause: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create clause"
        )


# Version endpoints must come BEFORE the general /clauses/{clause_id} endpoint
# to avoid route matching issues

@router.get("/clauses/{clause_id}/versions", response_model=List[Clause])
async def get_clause_versions(
    clause_id: str,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get version history for a clause."""
    try:
        return await service.get_version_history(clause_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting clause versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get clause versions"
        )


@router.post("/clauses/{clause_id}/versions", response_model=Clause)
async def create_clause_version(
    clause_id: str,
    request: CreateVersionRequest,
    user_email: str = "user@example.com",  # TODO: Get from auth
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Create a new version of a clause."""
    try:
        return await service.create_clause_version(
            clause_id,
            request.change_notes,
            user_email
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating clause version: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create clause version"
        )


@router.get("/clauses/{clause_id}", response_model=Clause)
async def get_clause(
    clause_id: str,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get a clause by ID."""
    clause = await service.get_clause(clause_id)
    if not clause:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause not found: {clause_id}"
        )
    return clause


@router.put("/clauses/{clause_id}", response_model=Clause)
async def update_clause(
    clause_id: str,
    request: UpdateClauseRequest,
    user_email: str = "user@example.com",  # TODO: Get from auth
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Update an existing clause."""
    try:
        return await service.update_clause(clause_id, request, user_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating clause: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update clause"
        )


@router.delete("/clauses/{clause_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clause(
    clause_id: str,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Delete a clause (soft delete)."""
    success = await service.delete_clause(clause_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause not found: {clause_id}"
        )


@router.get("/clauses", response_model=ClauseListResponse)
async def get_clauses(
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = "active",
    risk_level: Optional[str] = None,
    tags: Optional[str] = None,
    contract_types: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get clauses with optional filters using query parameters."""
    try:
        # Convert query parameters to SearchClausesRequest
        request = SearchClausesRequest(
            category_id=category_id,
            search_text=search,
            status=status,
            risk_level=risk_level,
            tags=tags.split(',') if tags else None,
            contract_types=contract_types.split(',') if contract_types else None,
            limit=limit,
            offset=offset
        )
        return await service.search_clauses(request)
    except Exception as e:
        logger.error(f"Error getting clauses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get clauses"
        )


@router.post("/clauses/search", response_model=ClauseListResponse)
async def search_clauses(
    request: SearchClausesRequest,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Search clauses with filters and pagination."""
    try:
        return await service.search_clauses(request)
    except Exception as e:
        logger.error(f"Error searching clauses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search clauses"
        )


# ========== Category Endpoints ==========

@router.get("/categories", response_model=List[ClauseCategory])
async def get_all_categories(
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get all categories as a flat list."""
    try:
        return await service.get_all_categories()
    except Exception as e:
        logger.error(f"Error getting all categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get categories"
        )


@router.get("/categories/tree", response_model=List[CategoryTreeNode])
async def get_category_tree(
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get the complete category hierarchy as a tree."""
    try:
        return await service.get_category_tree()
    except Exception as e:
        logger.error(f"Error getting category tree: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get category tree"
        )


@router.get("/categories/{category_id}", response_model=ClauseCategory)
async def get_category(
    category_id: str,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get a category by ID."""
    category = await service.get_category(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_id}"
        )
    return category


@router.post("/categories", response_model=ClauseCategory, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CreateCategoryRequest,
    user_email: str = "user@example.com",  # TODO: Get from auth
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Create a new category."""
    try:
        return await service.create_category(request, user_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


# ========== Variable Endpoints ==========

@router.get("/variables", response_model=SystemVariables)
async def get_system_variables(
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get system variables configuration."""
    try:
        return await service.get_system_variables()
    except Exception as e:
        logger.error(f"Error getting system variables: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system variables"
        )


@router.post("/variables/custom", response_model=ClauseVariable, status_code=status.HTTP_201_CREATED)
async def create_custom_variable(
    request: CreateCustomVariableRequest,
    user_email: str = "user@example.com",  # TODO: Get from auth
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Create a new custom variable."""
    try:
        return await service.create_custom_variable(request, user_email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating custom variable: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom variable"
        )


# ========== Comparison & AI Endpoints ==========

@router.post("/compare", response_model=ClauseComparison)
async def compare_clause(
    request: CompareClauseRequest,
    user_email: str = "user@example.com",  # TODO: Get from auth
    model_selection: str = "primary",  # "primary" (GPT-4.1) or "secondary" (GPT-4.1-mini)
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """
    Compare contract text with a clause from the library.

    Args:
        request: Comparison request with clause_id and contract_text
        user_email: Email of the user performing the comparison
        model_selection: AI model to use - "primary" (GPT-4.1) or "secondary" (GPT-4.1-mini)

    Returns:
        ClauseComparison with similarity analysis, risks, and recommendations
    """
    try:
        # Validate model_selection
        if model_selection not in ["primary", "secondary"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="model_selection must be 'primary' or 'secondary'"
            )

        return await service.compare_clause(
            request=request,
            user_email=user_email,
            model_selection=model_selection
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing clause: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare clause"
        )


@router.post("/suggest")
async def suggest_clause(
    request: SuggestClauseRequest,
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Use AI to suggest the best matching clauses for given text."""
    try:
        suggestions = await service.suggest_clause(request)
        return {
            "suggestions": [
                {
                    "clause": clause.model_dump(mode='json'),
                    "similarity_score": score
                }
                for clause, score in suggestions
            ]
        }
    except Exception as e:
        logger.error(f"Error suggesting clause: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suggest clause"
        )


# ========== Performance & Monitoring Endpoints ==========

@router.get("/cache-stats")
async def get_cache_stats(
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Get cache statistics and performance metrics."""
    try:
        stats = service.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cache stats"
        )


@router.post("/clear-caches")
async def clear_caches(
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """Clear all caches (admin operation)."""
    try:
        service.clear_caches()
        return {"message": "All caches cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing caches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear caches"
        )


@router.post("/recalculate-counts")
async def recalculate_category_counts(
    service: ClauseLibraryService = Depends(get_clause_service)
):
    """
    Recalculate clause counts for all categories (admin operation).

    This endpoint recalculates the clause_count field for all categories
    by counting actual clauses in the database. This fixes any incorrect
    counts that may have accumulated due to bugs or data inconsistencies.

    Parent categories will include counts from all child categories.
    """
    try:
        counts = await service.recalculate_category_counts()
        return {
            "message": "Category counts recalculated successfully",
            "updated_counts": counts,
            "total_categories": len(counts)
        }
    except Exception as e:
        logger.error(f"Error recalculating category counts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recalculate category counts"
        )
