"""
LLM Usage Tracker Service

Centralized service for tracking all LLM API usage across the application.
Tracks completions, embeddings, costs, and provides analytics.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import logging

from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)


# Operation type constants for consistent categorization
OPERATION_TYPES = {
    "sparql_generation": "SPARQL Generation",
    "contract_comparison": "Contract Comparison",
    "compliance_evaluation": "Compliance Rule Evaluation",
    "compliance_recommendation": "Compliance Recommendation",
    "clause_comparison": "Clause Library Comparison",
    "clause_suggestion": "Clause Library Suggestion",
    "query_planning": "Query Planning & Execution",
    "rag_embedding": "RAG Vector Embedding",
    "generic_completion": "Generic AI Completion",
    "word_addin_evaluation": "Word Add-in Evaluation",
    "word_addin_comparison": "Word Add-in Track Changes Comparison"
}


class LLMUsageTracker:
    """
    Centralized service for tracking LLM API usage.

    Tracks all completion and embedding API calls with detailed metadata
    for cost analysis, optimization, and monitoring.
    """

    def __init__(self, cosmos_service: CosmosNoSQLService):
        """
        Initialize the usage tracker.

        Args:
            cosmos_service: CosmosDB service instance
        """
        self.cosmos = cosmos_service
        self.container = "model_usage"

        # Token pricing per 1M tokens (update with actual Azure OpenAI pricing)
        # These are example rates - adjust based on your Azure OpenAI pricing
        self.PRICING = {
            "gpt-4.1": {
                "prompt": 0.00003,      # $30 per 1M tokens
                "completion": 0.00006   # $60 per 1M tokens
            },
            "gpt-4.1-mini": {
                "prompt": 0.00001,      # $10 per 1M tokens
                "completion": 0.00002   # $20 per 1M tokens
            },
            "gpt-4": {
                "prompt": 0.00003,
                "completion": 0.00006
            },
            "gpt-4-mini": {
                "prompt": 0.00001,
                "completion": 0.00002
            },
            "text-embedding-ada-002": {
                "embedding": 0.0001     # $0.10 per 1M tokens
            },
            "text-embedding-3-small": {
                "embedding": 0.00002    # $0.02 per 1M tokens
            },
            "text-embedding-3-large": {
                "embedding": 0.00013    # $0.13 per 1M tokens
            }
        }

    async def track_completion(
        self,
        user_email: str,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        elapsed_time: float,
        operation_details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Track a completion API call.

        Args:
            user_email: User making the request
            operation: Operation type (use OPERATION_TYPES constants)
            model: Model name
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            elapsed_time: Time in seconds
            operation_details: Additional context (rule_set_id, contract_id, etc.)
            success: Whether the call succeeded
            error_message: Error details if failed
        """
        logger.info(f"[LLM_TRACKER] track_completion called: operation={operation}, model={model}, success={success}")
        try:
            total_tokens = prompt_tokens + completion_tokens
            estimated_cost = self._estimate_completion_cost(
                model, prompt_tokens, completion_tokens
            )

            usage_record = {
                "id": str(uuid.uuid4()),
                "type": "model_usage",
                "api_type": "completion",
                "user_email": user_email,
                "operation": operation,
                "operation_details": operation_details or {},
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.utcnow().isoformat(),
                "estimated_cost": estimated_cost,
                "success": success,
                "error_message": error_message
            }

            self.cosmos.set_container(self.container)
            await self.cosmos.upsert_item(usage_record)

            logger.info(
                f"Tracked {operation}: {model}, "
                f"{total_tokens} tokens ({prompt_tokens} prompt + {completion_tokens} completion), "
                f"${estimated_cost:.4f}, {elapsed_time:.2f}s"
            )

        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.error(f"Error tracking completion usage: {e}", exc_info=True)

    async def track_embedding(
        self,
        user_email: str,
        operation: str,
        model: str,
        tokens: int,
        elapsed_time: float,
        operation_details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Track an embedding API call.

        Args:
            user_email: User making the request
            operation: Operation type (use OPERATION_TYPES constants)
            model: Model name
            tokens: Number of tokens processed
            elapsed_time: Time in seconds
            operation_details: Additional context
            success: Whether the call succeeded
            error_message: Error details if failed
        """
        try:
            estimated_cost = self._estimate_embedding_cost(model, tokens)

            usage_record = {
                "id": str(uuid.uuid4()),
                "type": "model_usage",
                "api_type": "embedding",
                "user_email": user_email,
                "operation": operation,
                "operation_details": operation_details or {},
                "model": model,
                "tokens": tokens,
                "elapsed_time": elapsed_time,
                "timestamp": datetime.utcnow().isoformat(),
                "estimated_cost": estimated_cost,
                "success": success,
                "error_message": error_message
            }

            self.cosmos.set_container(self.container)
            await self.cosmos.upsert_item(usage_record)

            logger.info(
                f"Tracked {operation}: {model}, "
                f"{tokens} tokens, ${estimated_cost:.4f}, {elapsed_time:.2f}s"
            )

        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.error(f"Error tracking embedding usage: {e}", exc_info=True)

    def _estimate_completion_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """
        Estimate cost for completion call.

        Args:
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Get pricing for the model (default to gpt-4.1 if unknown)
        pricing = self.PRICING.get(model, self.PRICING["gpt-4.1"])

        prompt_cost = prompt_tokens * pricing.get("prompt", 0.00003)
        completion_cost = completion_tokens * pricing.get("completion", 0.00006)

        return prompt_cost + completion_cost

    def _estimate_embedding_cost(self, model: str, tokens: int) -> float:
        """
        Estimate cost for embedding call.

        Args:
            model: Model name
            tokens: Number of tokens

        Returns:
            Estimated cost in USD
        """
        # Get pricing for the model (default to text-embedding-ada-002 if unknown)
        pricing = self.PRICING.get(model, {"embedding": 0.0001})
        return tokens * pricing["embedding"]

    def get_operation_display_name(self, operation: str) -> str:
        """
        Get display name for operation type.

        Args:
            operation: Operation key

        Returns:
            Human-readable operation name
        """
        return OPERATION_TYPES.get(operation, operation)
