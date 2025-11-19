"""
FastAPI router for User Preferences endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user-preferences", tags=["user-preferences"])


# ========== Models ==========

class ModelPreference(BaseModel):
    """Model preference settings."""
    default_model: str  # "primary" or "secondary"
    auto_select: bool = False  # Automatically select based on contract characteristics (future)
    cost_optimization: bool = False  # Prefer secondary model when quality is similar (future)


class UserPreferences(BaseModel):
    """User preferences model."""
    id: Optional[str] = None
    type: str = "user_preferences"
    user_email: str
    model_preference: ModelPreference
    created_date: Optional[str] = None
    modified_date: Optional[str] = None


# ========== Dependency ==========

# NOTE: This will be set during app startup
_cosmos_service: Optional[CosmosNoSQLService] = None


def get_cosmos_service() -> CosmosNoSQLService:
    """Get CosmosDB service instance."""
    if _cosmos_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CosmosDB service not initialized"
        )
    return _cosmos_service


def set_cosmos_service(service: CosmosNoSQLService):
    """Set CosmosDB service instance."""
    global _cosmos_service
    _cosmos_service = service


# ========== Endpoints ==========

@router.get("/ping")
async def ping():
    """Simple ping endpoint to verify router is working."""
    return {"message": "User preferences router is working", "router": "user-preferences"}


@router.get("/model-preference")
async def get_model_preference(
    user_email: str,
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Get user's model preference.

    Args:
        user_email: Email address of the user

    Returns:
        UserPreferences with model preference settings
    """
    try:
        # Set container
        container_name = "user_preferences"
        cosmos.set_container(container_name)

        # Query for user preferences
        query = "SELECT * FROM c WHERE c.type = 'user_preferences' AND c.user_email = @email"
        params = [{"name": "@email", "value": user_email}]

        results = await cosmos.parameterized_query(query, params)

        if results:
            logger.info(f"Found preferences for user: {user_email}")
            return results[0]

        # Return default preferences if none exist
        logger.info(f"No preferences found for user: {user_email}, returning defaults")
        default_prefs = UserPreferences(
            user_email=user_email,
            model_preference=ModelPreference(
                default_model="primary",
                auto_select=False,
                cost_optimization=False
            ),
            created_date=datetime.utcnow().isoformat(),
            modified_date=datetime.utcnow().isoformat()
        )
        return default_prefs.model_dump(mode='json', exclude_none=True)

    except Exception as e:
        logger.error(f"Error getting model preference: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model preference: {str(e)}"
        )


@router.post("/model-preference")
async def save_model_preference(
    user_email: str,
    preference: ModelPreference,
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Save user's model preference.

    Args:
        user_email: Email address of the user
        preference: Model preference settings to save

    Returns:
        Success message with saved preferences
    """
    try:
        # Validate default_model
        if preference.default_model not in ["primary", "secondary"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="default_model must be 'primary' or 'secondary'"
            )

        # Set container
        container_name = "user_preferences"
        cosmos.set_container(container_name)

        # Check if preferences exist
        query = "SELECT * FROM c WHERE c.type = 'user_preferences' AND c.user_email = @email"
        params = [{"name": "@email", "value": user_email}]
        results = await cosmos.parameterized_query(query, params)

        now = datetime.utcnow().isoformat()

        if results:
            # Update existing preferences
            prefs = results[0]
            prefs["model_preference"] = preference.model_dump()
            prefs["modified_date"] = now
            logger.info(f"Updating preferences for user: {user_email}")
        else:
            # Create new preferences
            prefs = UserPreferences(
                id=f"prefs_{user_email.replace('@', '_').replace('.', '_')}",
                user_email=user_email,
                model_preference=preference,
                created_date=now,
                modified_date=now
            ).model_dump(mode='json', exclude_none=True)
            logger.info(f"Creating new preferences for user: {user_email}")

        # Save to database
        await cosmos.upsert_item(prefs)

        return {
            "message": "Preferences saved successfully",
            "preferences": prefs
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving model preference: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save model preference: {str(e)}"
        )


@router.delete("/model-preference")
async def delete_model_preference(
    user_email: str,
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Delete user's model preference (reset to defaults).

    Args:
        user_email: Email address of the user

    Returns:
        Success message
    """
    try:
        # Set container
        container_name = "user_preferences"
        cosmos.set_container(container_name)

        # Query for user preferences
        query = "SELECT * FROM c WHERE c.type = 'user_preferences' AND c.user_email = @email"
        params = [{"name": "@email", "value": user_email}]
        results = await cosmos.parameterized_query(query, params)

        if results:
            # Delete preferences
            item_id = results[0]["id"]
            partition_key = user_email
            await cosmos.delete_item(item_id, partition_key)
            logger.info(f"Deleted preferences for user: {user_email}")
            return {"message": "Preferences deleted successfully"}
        else:
            return {"message": "No preferences to delete"}

    except Exception as e:
        logger.error(f"Error deleting model preference: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model preference: {str(e)}"
        )
