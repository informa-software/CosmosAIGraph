# LLM Usage Tracking Implementation Plan

## Executive Summary

This document outlines the plan to implement comprehensive LLM usage tracking across the entire application, categorizing calls by functionality type, and integrating tracking data into the utilization dashboard.

## Current State Analysis

### Existing Tracking Implementation

**Location**: `web_app/src/services/clause_library_service.py` (lines 1244-1286)

**Current Tracking Method**:
```python
async def _track_model_usage(
    user_email: str,
    model: str,
    operation: str,  # Currently only "clause_comparison"
    tokens: int,     # Only completion_tokens tracked
    elapsed_time: float
)
```

**Current Storage**: CosmosDB `model_usage` container
```json
{
  "id": "uuid",
  "type": "model_usage",
  "user_email": "user@example.com",
  "model": "gpt-4.1",
  "operation": "clause_comparison",
  "tokens": 1500,
  "elapsed_time": 2.34,
  "timestamp": "2025-01-15T10:30:00",
  "estimated_cost": 0.045
}
```

**Current Dashboard**: `web_app/routers/analytics_router.py`
- `/api/analytics/usage-summary` - Per-model aggregation
- `/api/analytics/cost-savings` - Cost optimization analysis
- `/api/analytics/usage-timeline` - Daily usage breakdown

### Currently Tracked LLM Calls

✅ **Tracked**:
1. **Clause Comparison** (`clause_library_service.py:730`)
   - Operation: `clause_comparison`
   - Tokens: completion_tokens only

### Untracked LLM Calls

❌ **Not Tracked**:

1. **SPARQL Generation** (`ai_service.py:171`)
   - Function: `generate_sparql_from_user_prompt()`
   - Purpose: Natural language → SPARQL query conversion
   - Model: Primary completions model

2. **Generic Completions** (`ai_service.py:383`)
   - Function: `get_completion()`
   - Purpose: General AI completions
   - Model: Primary completions model

3. **Contract Comparison** (`ai_service.py:418`)
   - Function: `compare_contracts_with_azure_openai()`
   - Purpose: Compare two contracts for differences
   - Model: Primary or secondary (user-selected)

4. **Compliance Rule Evaluation** (`ai_service.py:518`)
   - Function: `evaluate_compliance_rules_batch()`
   - Purpose: Evaluate contract against compliance rules
   - Model: Primary completions model

5. **Compliance Recommendations** (`ai_service.py:624`)
   - Function: `generate_compliance_recommendation()`
   - Purpose: Generate fix recommendations for failed rules
   - Model: Primary completions model

6. **LLM Query Planning** (`llm_query_planner.py:512`)
   - Function: `plan_and_execute()`
   - Purpose: Convert NL query → execution strategy
   - Model: Primary completions model

7. **Embeddings Generation** (Multiple locations)
   - `ai_service.py:243` - `generate_embeddings()`
   - `clause_library_service.py:966` - Clause embeddings
   - `rag_data_service.py:329` - RAG embeddings
   - Purpose: Vector embeddings for semantic search
   - Model: Embeddings model

## Implementation Plan

### Phase 1: Create Centralized Tracking Service

**Goal**: Extract tracking functionality into a reusable service

**New File**: `web_app/src/services/llm_usage_tracker.py`

```python
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)

class LLMUsageTracker:
    """Centralized service for tracking LLM API usage."""

    def __init__(self, cosmos_service):
        self.cosmos = cosmos_service
        self.container = "model_usage"

        # Token pricing per 1M tokens (update with actual Azure pricing)
        self.PRICING = {
            "gpt-4.1": {
                "prompt": 0.00003,      # $30 per 1M
                "completion": 0.00006   # $60 per 1M
            },
            "gpt-4.1-mini": {
                "prompt": 0.00001,      # $10 per 1M
                "completion": 0.00002   # $20 per 1M
            },
            "text-embedding-ada-002": {
                "embedding": 0.0001     # $0.10 per 1M
            }
        }

    async def track_completion(
        self,
        user_email: str,
        operation: str,
        operation_details: Optional[Dict[str, Any]],
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        elapsed_time: float,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Track a completion API call.

        Args:
            user_email: User making the request
            operation: Operation type (see OPERATION_TYPES below)
            operation_details: Additional context (rule_set_id, contract_id, etc.)
            model: Model name
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            elapsed_time: Time in seconds
            success: Whether the call succeeded
            error_message: Error details if failed
        """
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
                f"{total_tokens} tokens, ${estimated_cost:.4f}"
            )

        except Exception as e:
            logger.error(f"Error tracking completion usage: {e}", exc_info=True)

    async def track_embedding(
        self,
        user_email: str,
        operation: str,
        operation_details: Optional[Dict[str, Any]],
        model: str,
        tokens: int,
        elapsed_time: float,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Track an embedding API call.

        Args:
            user_email: User making the request
            operation: Operation type
            operation_details: Additional context
            model: Model name
            tokens: Number of tokens processed
            elapsed_time: Time in seconds
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
                f"{tokens} tokens, ${estimated_cost:.4f}"
            )

        except Exception as e:
            logger.error(f"Error tracking embedding usage: {e}", exc_info=True)

    def _estimate_completion_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Estimate cost for completion call."""
        pricing = self.PRICING.get(model, self.PRICING["gpt-4.1"])
        prompt_cost = prompt_tokens * pricing.get("prompt", 0.00003)
        completion_cost = completion_tokens * pricing.get("completion", 0.00006)
        return prompt_cost + completion_cost

    def _estimate_embedding_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for embedding call."""
        pricing = self.PRICING.get(model, {"embedding": 0.0001})
        return tokens * pricing["embedding"]


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
```

### Phase 2: Integrate Tracking into All Services

**Goal**: Add tracking to every LLM API call

#### 2.1 Update `ai_service.py`

**Location 1**: `generate_sparql_from_user_prompt()` (line 171)
```python
# After completion call
completion = self.aoai_client.chat.completions.create(...)

# Add tracking
await llm_tracker.track_completion(
    user_email=user_email,  # Pass from router
    operation="sparql_generation",
    operation_details={
        "user_query": user_text[:100],  # First 100 chars
        "schema_source": schema_source
    },
    model=completion.model,
    prompt_tokens=completion.usage.prompt_tokens,
    completion_tokens=completion.usage.completion_tokens,
    elapsed_time=t2 - t1,
    success=True
)
```

**Location 2**: `compare_contracts_with_azure_openai()` (line 418)
```python
completion = client.chat.completions.create(...)

await llm_tracker.track_completion(
    user_email=user_email,
    operation="contract_comparison",
    operation_details={
        "num_contracts": len(contract_texts),
        "model_selection": "secondary" if use_secondary_model else "primary"
    },
    model=completion.model,
    prompt_tokens=completion.usage.prompt_tokens,
    completion_tokens=completion.usage.completion_tokens,
    elapsed_time=elapsed,
    success=True
)
```

**Location 3**: `evaluate_compliance_rules_batch()` (line 518)
```python
completion = self.aoai_client.chat.completions.create(...)

await llm_tracker.track_completion(
    user_email=user_email,
    operation="compliance_evaluation",
    operation_details={
        "contract_id": contract_id,
        "rule_set_id": rule_set_id,
        "num_rules": len(rules)
    },
    model=completion.model,
    prompt_tokens=completion.usage.prompt_tokens,
    completion_tokens=completion.usage.completion_tokens,
    elapsed_time=elapsed,
    success=True
)
```

**Location 4**: `generate_compliance_recommendation()` (line 624)
```python
completion = self.aoai_client.chat.completions.create(...)

await llm_tracker.track_completion(
    user_email=user_email,
    operation="compliance_recommendation",
    operation_details={
        "rule_id": rule_id,
        "rule_name": rule_name,
        "evaluation_result": evaluation_result
    },
    model=completion.model,
    prompt_tokens=completion.usage.prompt_tokens,
    completion_tokens=completion.usage.completion_tokens,
    elapsed_time=elapsed,
    success=True
)
```

**Location 5**: `generate_embeddings()` (line 243)
```python
response = self.aoai_client.embeddings.create(...)

await llm_tracker.track_embedding(
    user_email=user_email,
    operation="rag_embedding",
    operation_details={"text_length": len(text)},
    model=self.embeddings_deployment,
    tokens=response.usage.total_tokens,
    elapsed_time=elapsed,
    success=True
)
```

#### 2.2 Update `clause_library_service.py`

**Replace existing** `_track_model_usage()` calls with new tracker:
```python
await llm_tracker.track_completion(
    user_email=user_email,
    operation="clause_comparison",
    operation_details={
        "clause_id": clause_id,
        "contract_id": contract_id,
        "model_selection": model_selection
    },
    model=deployment,
    prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
    completion_tokens=response.get("usage", {}).get("completion_tokens", 0),
    elapsed_time=elapsed,
    success=True
)
```

#### 2.3 Update `llm_query_planner.py`

```python
response = self.client.chat.completions.create(...)

await llm_tracker.track_completion(
    user_email=user_email,
    operation="query_planning",
    operation_details={
        "user_query": user_query[:100],
        "strategy": detected_strategy
    },
    model=response.model,
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    elapsed_time=elapsed,
    success=True
)
```

#### 2.4 Update `word_addin_service.py`

```python
# For contract evaluation
await llm_tracker.track_completion(
    user_email=user_email,
    operation="word_addin_evaluation",
    operation_details={
        "rule_set_id": rule_set_id,
        "num_rules": num_rules,
        "track_changes_mode": compliance_mode
    },
    model=model,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    elapsed_time=elapsed,
    success=True
)
```

### Phase 3: Enhance CosmosDB Schema

**Goal**: Support richer analytics and querying

**Index Policy**: Update `model_usage` container index policy
```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {
      "path": "/*"
    }
  ],
  "excludedPaths": [
    {
      "path": "/\"_etag\"/?"
    }
  ],
  "compositeIndexes": [
    [
      {"path": "/user_email", "order": "ascending"},
      {"path": "/timestamp", "order": "descending"}
    ],
    [
      {"path": "/operation", "order": "ascending"},
      {"path": "/timestamp", "order": "descending"}
    ],
    [
      {"path": "/model", "order": "ascending"},
      {"path": "/timestamp", "order": "descending"}
    ]
  ]
}
```

**Partition Key**: Keep as `user_email` for efficient user-scoped queries

### Phase 4: Enhance Analytics Dashboard

**Goal**: Add operation-type breakdown and enhanced visualizations

#### 4.1 New Endpoint: Operation Breakdown

**File**: `web_app/routers/analytics_router.py`

```python
@router.get("/operation-breakdown")
async def get_operation_breakdown(
    user_email: str,
    days: int = Query(30, ge=1, le=365),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Get usage breakdown by operation type.

    Returns statistics for each operation category:
    - SPARQL Generation
    - Contract Comparison
    - Compliance Evaluation
    - Clause Comparison
    - etc.
    """
    cosmos.set_container("model_usage")
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    query = """
    SELECT c.operation, c.model, c.api_type,
           c.prompt_tokens, c.completion_tokens,
           c.tokens, c.estimated_cost, c.elapsed_time
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

    # Aggregate by operation in Python
    operation_stats = {}
    for record in records:
        operation = record.get("operation", "unknown")
        if operation not in operation_stats:
            operation_stats[operation] = {
                "operation": operation,
                "api_type": record.get("api_type"),
                "total_calls": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_time": 0.0,
                "models_used": set()
            }

        stats = operation_stats[operation]
        stats["total_calls"] += 1
        stats["total_prompt_tokens"] += record.get("prompt_tokens", 0)
        stats["total_completion_tokens"] += record.get("completion_tokens", 0)
        stats["total_tokens"] += record.get("tokens", 0)
        stats["total_cost"] += record.get("estimated_cost", 0.0)
        stats["total_time"] += record.get("elapsed_time", 0.0)
        stats["models_used"].add(record.get("model"))

    # Convert sets to lists and calculate averages
    results = []
    for operation, stats in operation_stats.items():
        results.append({
            "operation": stats["operation"],
            "api_type": stats["api_type"],
            "total_calls": stats["total_calls"],
            "total_prompt_tokens": stats["total_prompt_tokens"],
            "total_completion_tokens": stats["total_completion_tokens"],
            "total_tokens": stats["total_tokens"],
            "total_cost": stats["total_cost"],
            "avg_time": stats["total_time"] / stats["total_calls"],
            "avg_tokens_per_call": stats["total_tokens"] / stats["total_calls"],
            "models_used": list(stats["models_used"])
        })

    # Sort by cost (highest first)
    results.sort(key=lambda x: x["total_cost"], reverse=True)

    return {
        "period_days": days,
        "start_date": start_date,
        "end_date": datetime.utcnow().isoformat(),
        "user_email": user_email,
        "operations": results,
        "totals": {
            "total_calls": sum(r["total_calls"] for r in results),
            "total_cost": sum(r["total_cost"] for r in results),
            "total_tokens": sum(r["total_tokens"] for r in results)
        }
    }
```

#### 4.2 New Endpoint: Token Efficiency Analysis

```python
@router.get("/token-efficiency")
async def get_token_efficiency(
    user_email: str,
    operation: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Analyze token efficiency - ratio of prompt to completion tokens.

    Helps identify operations that might benefit from prompt optimization.
    """
    cosmos.set_container("model_usage")
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    query = """
    SELECT c.operation, c.prompt_tokens, c.completion_tokens,
           c.estimated_cost, c.timestamp
    FROM c
    WHERE c.type = 'model_usage'
      AND c.api_type = 'completion'
      AND c.user_email = @email
      AND c.timestamp >= @start_date
    """ + (f" AND c.operation = @operation" if operation else "")

    params = [
        {"name": "@email", "value": user_email},
        {"name": "@start_date", "value": start_date}
    ]
    if operation:
        params.append({"name": "@operation", "value": operation})

    records = await cosmos.parameterized_query(query, params)

    # Calculate efficiency metrics
    efficiency_data = []
    for record in records:
        prompt = record.get("prompt_tokens", 0)
        completion = record.get("completion_tokens", 0)
        total = prompt + completion

        if total > 0:
            efficiency_data.append({
                "operation": record.get("operation"),
                "timestamp": record.get("timestamp"),
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
                "prompt_ratio": prompt / total,
                "completion_ratio": completion / total,
                "cost": record.get("estimated_cost", 0.0)
            })

    # Aggregate statistics
    if efficiency_data:
        avg_prompt_ratio = sum(d["prompt_ratio"] for d in efficiency_data) / len(efficiency_data)
        avg_completion_ratio = sum(d["completion_ratio"] for d in efficiency_data) / len(efficiency_data)

        return {
            "period_days": days,
            "user_email": user_email,
            "operation_filter": operation,
            "summary": {
                "total_calls": len(efficiency_data),
                "avg_prompt_ratio": avg_prompt_ratio,
                "avg_completion_ratio": avg_completion_ratio,
                "recommendation": _get_efficiency_recommendation(avg_prompt_ratio)
            },
            "data": efficiency_data
        }
    else:
        return {
            "period_days": days,
            "user_email": user_email,
            "operation_filter": operation,
            "summary": {
                "total_calls": 0,
                "message": "No data available for the specified period"
            },
            "data": []
        }


def _get_efficiency_recommendation(avg_prompt_ratio: float) -> str:
    """Generate recommendation based on prompt/completion ratio."""
    if avg_prompt_ratio > 0.8:
        return "High prompt ratio detected. Consider optimizing prompts to reduce token usage."
    elif avg_prompt_ratio > 0.6:
        return "Moderate prompt ratio. Review prompts for potential optimizations."
    else:
        return "Prompt efficiency looks good. Continue monitoring for changes."
```

#### 4.3 New Endpoint: Error Rate Analysis

```python
@router.get("/error-analysis")
async def get_error_analysis(
    user_email: str,
    days: int = Query(30, ge=1, le=365),
    cosmos: CosmosNoSQLService = Depends(get_cosmos_service)
):
    """
    Analyze LLM call failure rates by operation type.

    Helps identify operations with reliability issues.
    """
    cosmos.set_container("model_usage")
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

    query = """
    SELECT c.operation, c.success, c.error_message, c.model
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
    operation_stats = {}
    for record in records:
        operation = record.get("operation", "unknown")
        if operation not in operation_stats:
            operation_stats[operation] = {
                "operation": operation,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "errors": []
            }

        stats = operation_stats[operation]
        stats["total_calls"] += 1

        if record.get("success", True):
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
            error_msg = record.get("error_message", "Unknown error")
            stats["errors"].append({
                "model": record.get("model"),
                "error": error_msg
            })

    # Calculate error rates
    results = []
    for operation, stats in operation_stats.items():
        error_rate = (stats["failed_calls"] / stats["total_calls"] * 100)
            if stats["total_calls"] > 0 else 0

        results.append({
            "operation": stats["operation"],
            "total_calls": stats["total_calls"],
            "successful_calls": stats["successful_calls"],
            "failed_calls": stats["failed_calls"],
            "error_rate": error_rate,
            "recent_errors": stats["errors"][:5]  # Last 5 errors
        })

    # Sort by error rate (highest first)
    results.sort(key=lambda x: x["error_rate"], reverse=True)

    return {
        "period_days": days,
        "user_email": user_email,
        "operations": results,
        "overall": {
            "total_calls": sum(r["total_calls"] for r in results),
            "total_failures": sum(r["failed_calls"] for r in results),
            "overall_error_rate": (
                sum(r["failed_calls"] for r in results) /
                sum(r["total_calls"] for r in results) * 100
            ) if sum(r["total_calls"] for r in results) > 0 else 0
        }
    }
```

### Phase 5: Frontend Dashboard Enhancements

**Goal**: Create comprehensive utilization dashboard

#### 5.1 New Dashboard Page Structure

```
/analytics
  ├── /overview          # Summary cards and key metrics
  ├── /by-operation      # Breakdown by operation type
  ├── /by-model          # Breakdown by model
  ├── /cost-analysis     # Cost tracking and optimization
  ├── /efficiency        # Token efficiency analysis
  └── /reliability       # Error rates and success metrics
```

#### 5.2 Dashboard Components

**Overview Cards**:
- Total API Calls (30 days)
- Total Cost (30 days)
- Total Tokens (30 days)
- Average Response Time
- Error Rate %
- Cost Trend (vs. previous period)

**Operation Breakdown Chart** (Bar chart):
- X-axis: Operation types
- Y-axis: Cost or Token count
- Grouped by model

**Timeline Chart** (Line chart):
- X-axis: Date
- Y-axis: Cost
- Multiple lines for different operations

**Token Efficiency Chart** (Scatter plot):
- X-axis: Prompt tokens
- Y-axis: Completion tokens
- Color: Operation type
- Size: Cost

**Cost Savings Recommendations**:
- Identify operations using primary model that could use secondary
- Estimate potential savings
- Show model selection distribution

### Phase 6: User Context Propagation

**Goal**: Pass user_email through all service calls

**Changes Required**:
1. Update all router endpoints to extract user from authentication
2. Pass user_email to all service methods
3. Include in async job context

**Example**:
```python
# Router
@router.post("/api/compliance/evaluate/contract/{contract_id}")
async def evaluate_contract(
    contract_id: str,
    request: EvaluateContractRequest,
    current_user: str = Depends(get_current_user),  # Add auth
    services: dict = Depends(get_services)
):
    result = await services["evaluation"].evaluate_contract(
        contract_id=contract_id,
        contract_text=request.contract_text,
        rules=rules,
        create_job=request.async_mode,
        user_email=current_user  # Pass through
    )
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Create `LLMUsageTracker` service
- [ ] Update CosmosDB schema and index policy
- [ ] Create setup script for `model_usage` container

### Week 2: Service Integration
- [ ] Add tracking to `ai_service.py` (5 locations)
- [ ] Update `clause_library_service.py` tracking
- [ ] Add tracking to `llm_query_planner.py`
- [ ] Add tracking to `word_addin_service.py`

### Week 3: Analytics Backend
- [ ] Implement `/operation-breakdown` endpoint
- [ ] Implement `/token-efficiency` endpoint
- [ ] Implement `/error-analysis` endpoint
- [ ] Update existing endpoints for new schema

### Week 4: Frontend Dashboard
- [ ] Create dashboard page structure
- [ ] Implement overview cards
- [ ] Create operation breakdown chart
- [ ] Create timeline visualization
- [ ] Create efficiency analysis view

### Week 5: Testing & Deployment
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] User acceptance testing
- [ ] Production deployment
- [ ] Documentation

## Success Metrics

1. **Coverage**: 100% of LLM API calls tracked
2. **Data Quality**: <1% tracking failures
3. **Performance**: <10ms tracking overhead per call
4. **Dashboard Usage**: 80% of users access dashboard monthly
5. **Cost Optimization**: 20% reduction in token usage through insights

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tracking failures break requests | High | Wrap tracking in try-catch, log errors |
| Performance overhead | Medium | Async tracking, optimize CosmosDB writes |
| Storage costs increase | Medium | Set TTL policy on old records (90 days) |
| User context not available | High | Implement authentication layer first |
| Schema changes break existing | Medium | Version tracking schema, support both |

## Future Enhancements

1. **Real-time Monitoring**: WebSocket-based live dashboard
2. **Anomaly Detection**: ML-based cost spike detection
3. **Budget Alerts**: Configurable cost thresholds with notifications
4. **Comparative Analytics**: Compare usage across users/teams
5. **Prompt Library**: Track performance of different prompt templates
6. **A/B Testing**: Compare effectiveness of different models/prompts
