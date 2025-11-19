"""
FastAPI router for Analytics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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
    return {"message": "Analytics router is working", "router": "analytics"}


@router.get("/usage-summary")
async def get_usage_summary(
    user_email: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to include in summary"),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Get usage summary for the specified time period.
    Now includes operation-level breakdowns with new data format.

    Args:
        user_email: Email address of the user
        days: Number of days to include (1-365)

    Returns:
        Usage summary with per-operation and per-model breakdowns and totals
    """
    try:
        # Set container
        container_name = "model_usage"
        cosmos.set_container(container_name)

        # Calculate start date
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Query for completion records using NEW data format
        query = """
        SELECT c.model, c.operation, c.api_type,
               c.prompt_tokens, c.completion_tokens, c.total_tokens,
               c.estimated_cost, c.elapsed_time, c.success
        FROM c
        WHERE c.type = 'model_usage'
          AND c.api_type = 'completion'
          AND c.user_email = @email
          AND c.timestamp >= @start_date
        """

        params = [
            {"name": "@email", "value": user_email},
            {"name": "@start_date", "value": start_date}
        ]

        records = await cosmos.parameterized_query(query, params)

        # Aggregate by operation in Python
        operation_stats = {}
        model_stats = {}

        for record in records:
            operation = record.get("operation", "unknown")
            model = record.get("model", "unknown")
            success = record.get("success", True)

            # Operation-level aggregation
            if operation not in operation_stats:
                operation_stats[operation] = {
                    "operation": operation,
                    "total_count": 0,
                    "success_count": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_time": 0.0,
                    "models_used": set()
                }

            operation_stats[operation]["total_count"] += 1
            if success:
                operation_stats[operation]["success_count"] += 1
            operation_stats[operation]["total_prompt_tokens"] += record.get("prompt_tokens", 0)
            operation_stats[operation]["total_completion_tokens"] += record.get("completion_tokens", 0)
            operation_stats[operation]["total_tokens"] += record.get("total_tokens", 0)
            operation_stats[operation]["total_cost"] += record.get("estimated_cost", 0.0)
            operation_stats[operation]["total_time"] += record.get("elapsed_time", 0.0)
            operation_stats[operation]["models_used"].add(model)

            # Model-level aggregation
            if model not in model_stats:
                model_stats[model] = {
                    "model": model,
                    "total_operations": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_time": 0.0
                }

            model_stats[model]["total_operations"] += 1
            model_stats[model]["total_tokens"] += record.get("total_tokens", 0)
            model_stats[model]["total_cost"] += record.get("estimated_cost", 0.0)
            model_stats[model]["total_time"] += record.get("elapsed_time", 0.0)

        # Format operation results
        operation_results = []
        for operation, stats in operation_stats.items():
            operation_results.append({
                "operation": stats["operation"],
                "total_count": stats["total_count"],
                "success_count": stats["success_count"],
                "success_rate": (stats["success_count"] / stats["total_count"] * 100) if stats["total_count"] > 0 else 0,
                "total_prompt_tokens": stats["total_prompt_tokens"],
                "total_completion_tokens": stats["total_completion_tokens"],
                "total_tokens": stats["total_tokens"],
                "total_cost": stats["total_cost"],
                "avg_time": stats["total_time"] / stats["total_count"] if stats["total_count"] > 0 else 0,
                "models_used": list(stats["models_used"])
            })

        # Format model results
        model_results = []
        for model, stats in model_stats.items():
            model_results.append({
                "model": stats["model"],
                "total_operations": stats["total_operations"],
                "total_tokens": stats["total_tokens"],
                "total_cost": stats["total_cost"],
                "avg_time": stats["total_time"] / stats["total_operations"] if stats["total_operations"] > 0 else 0
            })

        # Calculate totals across all operations
        total_operations = sum(op["total_count"] for op in operation_results)
        total_success = sum(op["success_count"] for op in operation_results)
        total_prompt_tokens = sum(op["total_prompt_tokens"] for op in operation_results)
        total_completion_tokens = sum(op["total_completion_tokens"] for op in operation_results)
        total_tokens = sum(op["total_tokens"] for op in operation_results)
        total_cost = sum(op["total_cost"] for op in operation_results)

        logger.info(f"Usage summary for {user_email}: {total_operations} operations, ${total_cost:.4f}")

        return {
            "period_days": days,
            "start_date": start_date,
            "end_date": datetime.utcnow().isoformat(),
            "user_email": user_email,
            "operations": operation_results,
            "models": model_results,
            "totals": {
                "total_operations": total_operations,
                "total_success": total_success,
                "success_rate": (total_success / total_operations * 100) if total_operations > 0 else 0,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "total_cost": total_cost
            }
        }

    except Exception as e:
        logger.error(f"Error getting usage summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage summary: {str(e)}"
        )


@router.get("/cost-savings")
async def get_cost_savings(
    user_email: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Calculate potential cost savings if secondary model was used for all expensive model operations.
    Now analyzes all expensive models (gpt-4, gpt-4.1, gpt-4o) using new data format.

    Args:
        user_email: Email address of the user
        days: Number of days to analyze (1-365)

    Returns:
        Cost savings analysis with per-operation recommendations
    """
    try:
        # Set container
        container_name = "model_usage"
        cosmos.set_container(container_name)

        # Calculate start date
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Get all expensive model usage records using NEW data format
        # Use LIKE to match model names with version suffixes (e.g., gpt-4.1-2025-04-14)
        query = """
        SELECT c.operation, c.total_tokens, c.estimated_cost, c.model
        FROM c
        WHERE c.type = 'model_usage'
          AND c.api_type = 'completion'
          AND c.user_email = @email
          AND (STARTSWITH(c.model, 'gpt-4.1') OR STARTSWITH(c.model, 'gpt-4o') OR c.model = 'gpt-4')
          AND c.timestamp >= @start_date
        """

        params = [
            {"name": "@email", "value": user_email},
            {"name": "@start_date", "value": start_date}
        ]

        records = await cosmos.parameterized_query(query, params)

        # Aggregate in Python
        total_tokens = sum(r.get("total_tokens", 0) for r in records)
        actual_cost = sum(r.get("estimated_cost", 0.0) for r in records)
        operation_count = len(records)

        # Aggregate by operation for detailed breakdown
        operation_breakdown = {}
        for record in records:
            operation = record.get("operation", "unknown")
            if operation not in operation_breakdown:
                operation_breakdown[operation] = {
                    "operation": operation,
                    "count": 0,
                    "tokens": 0,
                    "actual_cost": 0.0
                }
            operation_breakdown[operation]["count"] += 1
            operation_breakdown[operation]["tokens"] += record.get("total_tokens", 0)
            operation_breakdown[operation]["actual_cost"] += record.get("estimated_cost", 0.0)

        if operation_count > 0 and total_tokens > 0:
            # Calculate what it would cost with secondary model (gpt-4.1-mini or gpt-4-mini)
            # Pricing: prompt $0.10/1M, completion $0.20/1M (average ~$0.15/1M)
            secondary_rate = 0.000015  # $15 per 1M tokens (average)
            potential_cost = total_tokens * secondary_rate
            savings = actual_cost - potential_cost
            savings_pct = (savings / actual_cost) * 100 if actual_cost > 0 else 0

            # Calculate savings per operation
            operation_savings = []
            for operation, stats in operation_breakdown.items():
                op_potential_cost = stats["tokens"] * secondary_rate
                op_savings = stats["actual_cost"] - op_potential_cost
                op_savings_pct = (op_savings / stats["actual_cost"] * 100) if stats["actual_cost"] > 0 else 0

                operation_savings.append({
                    "operation": operation,
                    "count": stats["count"],
                    "tokens": stats["tokens"],
                    "actual_cost": stats["actual_cost"],
                    "potential_cost": op_potential_cost,
                    "savings": op_savings,
                    "savings_percentage": op_savings_pct
                })

            # Sort by highest savings
            operation_savings.sort(key=lambda x: x["savings"], reverse=True)

            # Generate recommendation based on savings percentage
            if savings_pct > 30 and operation_savings:
                recommendation = f"Significant savings potential! Consider using GPT-4-mini for {operation_savings[0]['operation']} operations (${operation_savings[0]['savings']:.2f} savings)."
            elif savings_pct > 20:
                recommendation = "Moderate savings available. Review operation breakdown to identify candidates for cheaper models."
            elif savings_pct > 10:
                recommendation = "Some savings possible. Consider GPT-4-mini for low-complexity operations."
            else:
                recommendation = "Current usage is well-optimized. Continue current model selection."

            logger.info(f"Cost savings for {user_email}: ${savings:.4f} ({savings_pct:.1f}%)")

            return {
                "period_days": days,
                "user_email": user_email,
                "primary_model_usage": {
                    "operations": operation_count,
                    "tokens": total_tokens,
                    "actual_cost": actual_cost
                },
                "if_using_secondary": {
                    "potential_cost": potential_cost,
                    "savings": savings,
                    "savings_percentage": savings_pct
                },
                "operation_breakdown": operation_savings,
                "recommendation": recommendation
            }
        else:
            # No primary model usage found
            return {
                "period_days": days,
                "user_email": user_email,
                "primary_model_usage": {
                    "operations": 0,
                    "tokens": 0,
                    "actual_cost": 0
                },
                "if_using_secondary": {
                    "potential_cost": 0,
                    "savings": 0,
                    "savings_percentage": 0
                },
                "operation_breakdown": [],
                "recommendation": "No expensive model usage data available for this period."
            }

    except Exception as e:
        logger.error(f"Error calculating cost savings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate cost savings: {str(e)}"
        )


@router.get("/usage-timeline")
async def get_usage_timeline(
    user_email: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Get daily usage timeline for charting.
    Shows one row per day per model for simplified visualization.

    Args:
        user_email: Email address of the user
        days: Number of days to include (1-365)

    Returns:
        Daily usage breakdown by date and model for visualization
    """
    try:
        # Set container
        container_name = "model_usage"
        cosmos.set_container(container_name)

        # Calculate start date
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Query for all completion records using NEW data format
        query = """
        SELECT c.timestamp, c.model, c.total_tokens, c.estimated_cost
        FROM c
        WHERE c.type = 'model_usage'
          AND c.api_type = 'completion'
          AND c.user_email = @email
          AND c.timestamp >= @start_date
        """

        params = [
            {"name": "@email", "value": user_email},
            {"name": "@start_date", "value": start_date}
        ]

        records = await cosmos.parameterized_query(query, params)

        # Group by (date, model) only - one row per day per model
        timeline_stats = {}
        for record in records:
            # Extract date (YYYY-MM-DD) from ISO timestamp
            timestamp = record.get("timestamp", "")
            date = timestamp[:10] if len(timestamp) >= 10 else "unknown"
            model = record.get("model", "unknown")
            key = (date, model)

            if key not in timeline_stats:
                timeline_stats[key] = {
                    "date": date,
                    "model": model,
                    "operations": 0,
                    "tokens": 0,
                    "cost": 0.0
                }

            timeline_stats[key]["operations"] += 1
            timeline_stats[key]["tokens"] += record.get("total_tokens", 0)
            timeline_stats[key]["cost"] += record.get("estimated_cost", 0.0)

        # Convert to list and sort by date then model
        results = sorted(timeline_stats.values(), key=lambda x: (x["date"], x["model"]))

        logger.info(f"Retrieved {len(results)} daily usage records for {user_email}")

        return {
            "period_days": days,
            "start_date": start_date,
            "end_date": datetime.utcnow().isoformat(),
            "user_email": user_email,
            "timeline": results
        }

    except Exception as e:
        logger.error(f"Error getting usage timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage timeline: {str(e)}"
        )


@router.get("/operation-breakdown")
async def get_operation_breakdown(
    user_email: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Get detailed breakdown of LLM usage by operation type.

    Args:
        user_email: Email address of the user
        days: Number of days to analyze (1-365)

    Returns:
        Operation breakdown with per-operation statistics including:
        - Total operations per type
        - Token usage (prompt + completion)
        - Average response time
        - Estimated costs
        - Success rates
    """
    try:
        # Set container
        container_name = "model_usage"
        cosmos.set_container(container_name)

        # Calculate start date
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Query for all completion records (exclude embeddings for token ratio analysis)
        query = """
        SELECT c.operation, c.model, c.prompt_tokens, c.completion_tokens,
               c.total_tokens, c.elapsed_time, c.estimated_cost, c.success
        FROM c
        WHERE c.type = 'model_usage'
          AND c.api_type = 'completion'
          AND c.user_email = @email
          AND c.timestamp >= @start_date
        """

        params = [
            {"name": "@email", "value": user_email},
            {"name": "@start_date", "value": start_date}
        ]

        records = await cosmos.parameterized_query(query, params)

        # Aggregate by operation in Python
        operation_stats = {}
        for record in records:
            operation = record.get("operation", "unknown")
            if operation not in operation_stats:
                operation_stats[operation] = {
                    "operation": operation,
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_time": 0.0,
                    "models_used": set()
                }

            stats = operation_stats[operation]
            stats["total_operations"] += 1
            stats["successful_operations"] += 1 if record.get("success", True) else 0
            stats["failed_operations"] += 0 if record.get("success", True) else 1
            stats["total_prompt_tokens"] += record.get("prompt_tokens", 0)
            stats["total_completion_tokens"] += record.get("completion_tokens", 0)
            stats["total_tokens"] += record.get("total_tokens", 0)
            stats["total_cost"] += record.get("estimated_cost", 0.0)
            stats["total_time"] += record.get("elapsed_time", 0.0)
            stats["models_used"].add(record.get("model", "unknown"))

        # Format results with calculated metrics
        results = []
        for operation, stats in operation_stats.items():
            total_ops = stats["total_operations"]
            results.append({
                "operation": stats["operation"],
                "total_operations": total_ops,
                "successful_operations": stats["successful_operations"],
                "failed_operations": stats["failed_operations"],
                "success_rate": (stats["successful_operations"] / total_ops * 100) if total_ops > 0 else 0,
                "total_prompt_tokens": stats["total_prompt_tokens"],
                "total_completion_tokens": stats["total_completion_tokens"],
                "total_tokens": stats["total_tokens"],
                "avg_prompt_tokens": stats["total_prompt_tokens"] / total_ops if total_ops > 0 else 0,
                "avg_completion_tokens": stats["total_completion_tokens"] / total_ops if total_ops > 0 else 0,
                "avg_total_tokens": stats["total_tokens"] / total_ops if total_ops > 0 else 0,
                "total_cost": stats["total_cost"],
                "avg_cost_per_operation": stats["total_cost"] / total_ops if total_ops > 0 else 0,
                "total_time": stats["total_time"],
                "avg_time": stats["total_time"] / total_ops if total_ops > 0 else 0,
                "models_used": sorted(list(stats["models_used"]))
            })

        # Sort by total operations (most used first)
        results.sort(key=lambda x: x["total_operations"], reverse=True)

        # Calculate totals across all operations
        totals = {
            "total_operations": sum(r["total_operations"] for r in results),
            "successful_operations": sum(r["successful_operations"] for r in results),
            "failed_operations": sum(r["failed_operations"] for r in results),
            "total_tokens": sum(r["total_tokens"] for r in results),
            "total_cost": sum(r["total_cost"] for r in results),
            "total_time": sum(r["total_time"] for r in results)
        }
        totals["overall_success_rate"] = (
            (totals["successful_operations"] / totals["total_operations"] * 100)
            if totals["total_operations"] > 0 else 0
        )

        logger.info(f"Operation breakdown for {user_email}: {len(results)} operation types, {totals['total_operations']} total operations")

        return {
            "period_days": days,
            "start_date": start_date,
            "end_date": datetime.utcnow().isoformat(),
            "user_email": user_email,
            "operations": results,
            "totals": totals
        }

    except Exception as e:
        logger.error(f"Error getting operation breakdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get operation breakdown: {str(e)}"
        )


@router.get("/token-efficiency")
async def get_token_efficiency(
    user_email: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    operation_filter: Optional[str] = Query(None, description="Filter by specific operation type"),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Analyze token efficiency - prompt vs completion token ratios.

    Helps identify operations that may have inefficient prompts or
    could benefit from prompt optimization.

    Args:
        user_email: Email address of the user
        days: Number of days to analyze (1-365)
        operation_filter: Optional filter for specific operation type

    Returns:
        Token efficiency analysis with:
        - Prompt/completion token ratios
        - Inefficiency indicators
        - Optimization recommendations
    """
    try:
        # Set container
        container_name = "model_usage"
        cosmos.set_container(container_name)

        # Calculate start date
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Build query with optional operation filter
        query = """
        SELECT c.operation, c.model, c.prompt_tokens, c.completion_tokens,
               c.total_tokens, c.estimated_cost
        FROM c
        WHERE c.type = 'model_usage'
          AND c.api_type = 'completion'
          AND c.user_email = @email
          AND c.timestamp >= @start_date
        """

        params = [
            {"name": "@email", "value": user_email},
            {"name": "@start_date", "value": start_date}
        ]

        if operation_filter:
            query += " AND c.operation = @operation"
            params.append({"name": "@operation", "value": operation_filter})

        records = await cosmos.parameterized_query(query, params)

        # Aggregate by operation
        operation_efficiency = {}
        for record in records:
            operation = record.get("operation", "unknown")
            if operation not in operation_efficiency:
                operation_efficiency[operation] = {
                    "operation": operation,
                    "total_calls": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_cost": 0.0
                }

            stats = operation_efficiency[operation]
            stats["total_calls"] += 1
            stats["total_prompt_tokens"] += record.get("prompt_tokens", 0)
            stats["total_completion_tokens"] += record.get("completion_tokens", 0)
            stats["total_cost"] += record.get("estimated_cost", 0.0)

        # Calculate efficiency metrics and recommendations
        results = []
        for operation, stats in operation_efficiency.items():
            total_calls = stats["total_calls"]
            prompt_tokens = stats["total_prompt_tokens"]
            completion_tokens = stats["total_completion_tokens"]
            total_tokens = prompt_tokens + completion_tokens

            # Calculate ratios
            avg_prompt = prompt_tokens / total_calls if total_calls > 0 else 0
            avg_completion = completion_tokens / total_calls if total_calls > 0 else 0
            prompt_ratio = (prompt_tokens / total_tokens * 100) if total_tokens > 0 else 0
            completion_ratio = (completion_tokens / total_tokens * 100) if total_tokens > 0 else 0

            # Generate efficiency assessment
            if prompt_ratio > 80:
                efficiency_status = "Poor - High prompt overhead"
                recommendation = "Consider prompt optimization: reduce context, use caching, or summarize inputs"
            elif prompt_ratio > 60:
                efficiency_status = "Moderate - Room for improvement"
                recommendation = "Review prompt structure for potential optimizations"
            else:
                efficiency_status = "Good - Balanced token usage"
                recommendation = "Current token distribution is efficient"

            results.append({
                "operation": operation,
                "total_calls": total_calls,
                "avg_prompt_tokens": avg_prompt,
                "avg_completion_tokens": avg_completion,
                "prompt_percentage": prompt_ratio,
                "completion_percentage": completion_ratio,
                "efficiency_status": efficiency_status,
                "recommendation": recommendation,
                "total_cost": stats["total_cost"],
                "avg_cost_per_call": stats["total_cost"] / total_calls if total_calls > 0 else 0
            })

        # Sort by prompt ratio (highest first - most opportunity for optimization)
        results.sort(key=lambda x: x["prompt_percentage"], reverse=True)

        # Calculate overall summary
        total_prompt = sum(r["avg_prompt_tokens"] * r["total_calls"] for r in results)
        total_completion = sum(r["avg_completion_tokens"] * r["total_calls"] for r in results)
        total_all = total_prompt + total_completion

        summary = {
            "total_operations": sum(r["total_calls"] for r in results),
            "avg_prompt_tokens": total_prompt / len(results) if results else 0,
            "avg_completion_tokens": total_completion / len(results) if results else 0,
            "overall_prompt_percentage": (total_prompt / total_all * 100) if total_all > 0 else 0,
            "overall_completion_percentage": (total_completion / total_all * 100) if total_all > 0 else 0,
            "total_cost": sum(r["total_cost"] for r in results)
        }

        logger.info(f"Token efficiency for {user_email}: {len(results)} operations analyzed")

        return {
            "period_days": days,
            "user_email": user_email,
            "operation_filter": operation_filter,
            "summary": summary,
            "data": results
        }

    except Exception as e:
        logger.error(f"Error analyzing token efficiency: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze token efficiency: {str(e)}"
        )


@router.get("/error-analysis")
async def get_error_analysis(
    user_email: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Analyze LLM call success rates and error patterns.

    Args:
        user_email: Email address of the user
        days: Number of days to analyze (1-365)

    Returns:
        Error analysis with:
        - Success/failure rates per operation
        - Common error patterns
        - Reliability metrics
    """
    try:
        # Set container
        container_name = "model_usage"
        cosmos.set_container(container_name)

        # Calculate start date
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Query for all records including success/failure info
        query = """
        SELECT c.operation, c.model, c.success, c.error_message, c.timestamp
        FROM c
        WHERE c.type = 'model_usage'
          AND c.user_email = @email
          AND c.timestamp >= @start_date
        """

        params = [
            {"name": "@email", "value": user_email},
            {"name": "@start_date", "value": start_date}
        ]

        records = await cosmos.parameterized_query(query, params)

        # Aggregate by operation
        operation_reliability = {}
        error_patterns = {}

        for record in records:
            operation = record.get("operation", "unknown")
            success = record.get("success", True)
            error_msg = record.get("error_message", "")

            # Track operation stats
            if operation not in operation_reliability:
                operation_reliability[operation] = {
                    "operation": operation,
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "error_messages": []
                }

            stats = operation_reliability[operation]
            stats["total_calls"] += 1
            if success:
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1
                if error_msg:
                    stats["error_messages"].append(error_msg)
                    # Track error patterns
                    error_key = error_msg[:100]  # First 100 chars as key
                    error_patterns[error_key] = error_patterns.get(error_key, 0) + 1

        # Format operation results
        operation_results = []
        for operation, stats in operation_reliability.items():
            total = stats["total_calls"]
            success_rate = (stats["successful_calls"] / total * 100) if total > 0 else 0
            failure_rate = (stats["failed_calls"] / total * 100) if total > 0 else 0

            # Determine reliability status
            if success_rate >= 99:
                reliability_status = "Excellent"
            elif success_rate >= 95:
                reliability_status = "Good"
            elif success_rate >= 90:
                reliability_status = "Fair"
            else:
                reliability_status = "Poor - Needs attention"

            operation_results.append({
                "operation": operation,
                "total_calls": total,
                "successful_calls": stats["successful_calls"],
                "failed_calls": stats["failed_calls"],
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "reliability_status": reliability_status,
                "sample_errors": stats["error_messages"][:3]  # Show up to 3 sample errors
            })

        # Sort by failure rate (highest first - most problematic)
        operation_results.sort(key=lambda x: x["failure_rate"], reverse=True)

        # Find most common error patterns
        common_errors = [
            {"error_preview": error[:100], "occurrence_count": count}
            for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Calculate overall metrics
        total_calls = sum(r["total_calls"] for r in operation_results)
        total_successful = sum(r["successful_calls"] for r in operation_results)
        total_failed = sum(r["failed_calls"] for r in operation_results)

        overall = {
            "total_calls": total_calls,
            "successful_calls": total_successful,
            "failed_calls": total_failed,
            "overall_success_rate": (total_successful / total_calls * 100) if total_calls > 0 else 0,
            "overall_failure_rate": (total_failed / total_calls * 100) if total_calls > 0 else 0
        }

        logger.info(f"Error analysis for {user_email}: {total_calls} calls, {overall['overall_success_rate']:.2f}% success rate")

        return {
            "period_days": days,
            "user_email": user_email,
            "operations": operation_results,
            "common_errors": common_errors,
            "overall": overall
        }

    except Exception as e:
        logger.error(f"Error analyzing errors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze errors: {str(e)}"
        )
