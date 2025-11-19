"""
Service layer for Clause Library operations.
"""

import asyncio
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import html
from bs4 import BeautifulSoup
import re
import json
import hashlib
import time
from functools import wraps
from collections import OrderedDict

from src.models.clause_library_models import (
    Clause, ClauseCategory, SystemVariables, ClauseComparison,
    CreateClauseRequest, UpdateClauseRequest, CompareClauseRequest,
    SuggestClauseRequest, CreateCategoryRequest, CreateCustomVariableRequest,
    ClauseContent, ClauseMetadata, ClauseVersion, AuditInfo, ClauseVariable,
    CategoryTreeNode, ClauseListResponse, SearchClausesRequest,
    ComparisonResult, ComparisonDifference, RiskAnalysis, RiskItem,
    Recommendation, AIAnalysisInfo
)
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
import logging

logger = logging.getLogger(__name__)


def performance_monitor(operation_name: str):
    """Decorator to monitor performance of operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"[PERF] {operation_name} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[PERF] {operation_name} failed after {elapsed:.3f}s: {e}")
                raise
        return wrapper
    return decorator


class LRUCache:
    """Simple LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.timestamps = {}

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        if key not in self.cache:
            return None

        # Check TTL
        if time.time() - self.timestamps[key] > self.ttl_seconds:
            self.cache.pop(key)
            self.timestamps.pop(key)
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: Any):
        """Add item to cache."""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove oldest item
                oldest_key = next(iter(self.cache))
                self.cache.pop(oldest_key)
                self.timestamps.pop(oldest_key)

        self.cache[key] = value
        self.timestamps[key] = time.time()

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.timestamps.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

logger = logging.getLogger(__name__)


class ClauseLibraryService:
    """Service for managing clause library operations."""

    def __init__(
        self,
        cosmos_service: CosmosNoSQLService,
        ai_service: AiService,
        comparison_cache_size: int = 100,
        comparison_cache_ttl: int = 3600,
        embedding_cache_size: int = 200,
        embedding_cache_ttl: int = 7200
    ):
        self.cosmos = cosmos_service
        self.ai = ai_service
        self.clause_container = "clause_library"
        self.category_container = "clause_categories"

        # In-memory cache for categories (performance optimization)
        self._category_cache: Optional[Dict[str, ClauseCategory]] = None
        self._category_tree_cache: Optional[List[CategoryTreeNode]] = None

        # LRU caches for AI operations
        self._comparison_cache = LRUCache(
            max_size=comparison_cache_size,
            ttl_seconds=comparison_cache_ttl
        )
        self._embedding_cache = LRUCache(
            max_size=embedding_cache_size,
            ttl_seconds=embedding_cache_ttl
        )

        # Performance metrics
        self._metrics = {
            "comparisons_total": 0,
            "comparisons_cached": 0,
            "embeddings_total": 0,
            "embeddings_cached": 0,
            "avg_comparison_time": 0.0,
            "avg_embedding_time": 0.0
        }

    async def initialize(self):
        """Initialize the service and load caches."""
        logger.info("Initializing ClauseLibraryService...")
        await self._load_category_cache()
        logger.info("ClauseLibraryService initialized successfully")

    # ========== Clause CRUD Operations ==========

    async def create_clause(
        self,
        request: CreateClauseRequest,
        user_email: str
    ) -> Clause:
        """Create a new clause in the library."""
        logger.info(f"Creating new clause: {request.name}")

        # Get category information
        category = await self.get_category(request.category_id)
        if not category:
            raise ValueError(f"Category not found: {request.category_id}")

        # Generate embedding for content (using optimized method)
        plain_text = self._html_to_plain_text(request.content_html)
        embedding = await self._generate_embedding_optimized(plain_text)

        # Extract variables from content
        variables = self._extract_variables_from_html(request.content_html)

        # Create clause document
        clause_id = str(uuid.uuid4())
        now = datetime.utcnow()

        clause = Clause(
            id=clause_id,
            type="clause",
            name=request.name,
            description=request.description,
            category_id=request.category_id,
            category_path=category.path,
            category_path_display=category.display_path,
            content=ClauseContent(
                html=request.content_html,
                plain_text=plain_text
            ),
            variables=variables,
            metadata=ClauseMetadata(
                tags=request.tags,
                contract_types=request.contract_types,
                jurisdictions=request.jurisdictions,
                risk_level=request.risk_level,
                complexity=request.complexity
            ),
            version=ClauseVersion(
                version_number=1,
                version_label="v1.0",
                is_current=True,
                created_by=user_email,
                created_date=now
            ),
            embedding=embedding,
            audit=AuditInfo(
                created_by=user_email,
                created_date=now
            )
        )

        # Save to CosmosDB
        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(
            clause.model_dump(mode='json', exclude_none=True)
        )

        # Update category clause count
        await self._increment_category_count(request.category_id)

        logger.info(f"Clause created successfully: {clause_id}")
        return clause

    async def get_clause(self, clause_id: str) -> Optional[Clause]:
        """Get a clause by ID."""
        self.cosmos.set_container(self.clause_container)
        query = f"SELECT * FROM c WHERE c.id = '{clause_id}' AND c.type = 'clause'"
        results = await self.cosmos.query_items(query, cross_partition=False, pk="clause")

        if results and len(results) > 0:
            return Clause(**results[0])
        return None

    async def update_clause(
        self,
        clause_id: str,
        request: UpdateClauseRequest,
        user_email: str
    ) -> Clause:
        """Update an existing clause."""
        logger.info(f"Updating clause: {clause_id}")

        # Get existing clause
        existing = await self.get_clause(clause_id)
        if not existing:
            raise ValueError(f"Clause not found: {clause_id}")

        # Update fields
        update_data = request.model_dump(exclude_none=True)

        if "content_html" in update_data:
            plain_text = self._html_to_plain_text(update_data["content_html"])
            embedding = await self._generate_embedding_optimized(plain_text)
            variables = self._extract_variables_from_html(update_data["content_html"])

            existing.content.html = update_data["content_html"]
            existing.content.plain_text = plain_text
            existing.embedding = embedding
            existing.variables = variables

        if "name" in update_data:
            existing.name = update_data["name"]
        if "description" in update_data:
            existing.description = update_data["description"]
        if "category_id" in update_data:
            category = await self.get_category(update_data["category_id"])
            if category:
                # Update old category count
                await self._decrement_category_count(existing.category_id)

                existing.category_id = update_data["category_id"]
                existing.category_path = category.path
                existing.category_path_display = category.display_path

                # Update new category count
                await self._increment_category_count(update_data["category_id"])

        # Update metadata
        for field in ["tags", "contract_types", "jurisdictions", "risk_level", "complexity"]:
            if field in update_data:
                setattr(existing.metadata, field, update_data[field])

        # Update audit info
        existing.audit.modified_by = user_email
        existing.audit.modified_date = datetime.utcnow()

        # Save to CosmosDB
        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(
            existing.model_dump(mode='json', exclude_none=True)
        )

        logger.info(f"Clause updated successfully: {clause_id}")
        return existing

    async def delete_clause(self, clause_id: str) -> bool:
        """Delete a clause (soft delete by setting status)."""
        logger.info(f"Deleting clause: {clause_id}")

        clause = await self.get_clause(clause_id)
        if not clause:
            return False

        clause.status = "deleted"

        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(
            clause.model_dump(mode='json', exclude_none=True)
        )

        # Update category count
        await self._decrement_category_count(clause.category_id)

        logger.info(f"Clause deleted successfully: {clause_id}")
        return True

    async def create_clause_version(
        self,
        clause_id: str,
        change_notes: Optional[str],
        user_email: str
    ) -> Clause:
        """Create a new version of an existing clause."""
        logger.info(f"Creating new version for clause: {clause_id}")

        # Get existing clause
        existing = await self.get_clause(clause_id)
        if not existing:
            raise ValueError(f"Clause not found: {clause_id}")

        # Mark existing as not current
        existing.version.is_current = False
        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(
            existing.model_dump(mode='json', exclude_none=True)
        )

        # Create new version
        new_clause = existing.model_copy(deep=True)
        new_clause.id = str(uuid.uuid4())
        new_clause.version.version_number = existing.version.version_number + 1
        new_clause.version.version_label = f"v{new_clause.version.version_number}.0"
        new_clause.version.is_current = True
        new_clause.version.parent_version_id = clause_id
        new_clause.version.created_by = user_email
        new_clause.version.created_date = datetime.utcnow()
        new_clause.version.change_notes = change_notes

        # Save new version
        await self.cosmos.upsert_item(
            new_clause.model_dump(mode='json', exclude_none=True)
        )

        logger.info(f"New clause version created: {new_clause.id}")
        return new_clause

    async def get_version_history(
        self,
        clause_id: str
    ) -> List[Clause]:
        """Get all versions of a clause, ordered by version number descending."""
        logger.info(f"Getting version history for clause: {clause_id}")

        # Get the clause to find its parent_version_id chain
        clause = await self.get_clause(clause_id)
        if not clause:
            raise ValueError(f"Clause not found: {clause_id}")

        # Build query to find all versions in the version chain
        # This includes the current clause and all versions that share the same parent chain
        self.cosmos.set_container(self.clause_container)

        # Find all clauses with the same parent_version_id or where this clause is a parent
        # Strategy: Find all versions in the same version chain
        # - If clause has no parent: find all where parent_version_id = clause_id, plus the clause itself
        # - If clause has a parent: find all siblings (same parent_version_id) plus the parent itself

        if clause.version.parent_version_id:
            # This clause has a parent - find all siblings and the parent
            query = """
            SELECT * FROM c
            WHERE c.type = 'clause'
            AND (
                c.version.parent_version_id = @parent_id
                OR c.id = @parent_id
                OR c.id = @clause_id
            )
            ORDER BY c.version.version_number DESC
            """
            parameters = [
                {"name": "@clause_id", "value": clause_id},
                {"name": "@parent_id", "value": clause.version.parent_version_id}
            ]
        else:
            # This clause is the root - find all children and itself
            query = """
            SELECT * FROM c
            WHERE c.type = 'clause'
            AND (
                c.version.parent_version_id = @clause_id
                OR c.id = @clause_id
            )
            ORDER BY c.version.version_number DESC
            """
            parameters = [
                {"name": "@clause_id", "value": clause_id}
            ]

        results = await self.cosmos.parameterized_query(
            query,
            parameters,
            cross_partition=True
        )

        versions = [Clause(**doc) for doc in results]

        logger.info(f"Found {len(versions)} versions for clause {clause_id}")
        return versions

    async def search_clauses(
        self,
        request: SearchClausesRequest
    ) -> ClauseListResponse:
        """Search clauses with filters and pagination."""
        logger.info(f"Searching clauses with query: {request.query}")

        # Build query
        query = "SELECT * FROM c WHERE c.type = 'clause' AND c.status = 'active'"
        parameters = []

        if request.category_id:
            query += " AND c.category_id = @category_id"
            parameters.append({"name": "@category_id", "value": request.category_id})

        if request.tags:
            query += " AND ARRAY_LENGTH(SetIntersect(c.metadata.tags, @tags)) > 0"
            parameters.append({"name": "@tags", "value": request.tags})

        if request.contract_types:
            query += " AND ARRAY_LENGTH(SetIntersect(c.metadata.contract_types, @contract_types)) > 0"
            parameters.append({"name": "@contract_types", "value": request.contract_types})

        if request.risk_level:
            query += " AND c.metadata.risk_level = @risk_level"
            parameters.append({"name": "@risk_level", "value": request.risk_level})

        if request.query:
            # Text search in name, description, and plain_text
            query += " AND (CONTAINS(c.name, @search_query) OR CONTAINS(c.description, @search_query) OR CONTAINS(c.content.plain_text, @search_query))"
            parameters.append({"name": "@search_query", "value": request.query})

        query += " ORDER BY c.name"

        # Execute query
        self.cosmos.set_container(self.clause_container)
        results = await self.cosmos.parameterized_query(
            query,
            parameters,
            cross_partition=True
        )

        clauses = [Clause(**doc) for doc in results]

        # Apply pagination
        total_count = len(clauses)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_clauses = clauses[start_idx:end_idx]

        return ClauseListResponse(
            clauses=paginated_clauses,
            total_count=total_count,
            page=request.page,
            page_size=request.page_size
        )

    # ========== Category Management ==========

    async def get_category(self, category_id: str) -> Optional[ClauseCategory]:
        """Get a category by ID."""
        if self._category_cache and category_id in self._category_cache:
            return self._category_cache[category_id]

        # Query across all partitions
        self.cosmos.set_container(self.category_container)
        query = "SELECT * FROM c WHERE c.id = @id AND c.type = 'category'"
        params = [{"name": "@id", "value": category_id}]

        results = await self.cosmos.parameterized_query(
            query,
            params,
            cross_partition=True
        )

        if results and len(results) > 0:
            return ClauseCategory(**results[0])
        return None

    async def get_all_categories(self) -> List[ClauseCategory]:
        """Get all active categories as a flat list."""
        # Check cache first
        if self._category_cache:
            return list(self._category_cache.values())

        # Load all categories
        self.cosmos.set_container(self.category_container)
        query = "SELECT * FROM c WHERE c.type = 'category' AND c.status = 'active' ORDER BY c.path_display"
        results = await self.cosmos.query_items(query, cross_partition=True)

        categories = [ClauseCategory(**doc) for doc in results]

        # Update cache
        if not self._category_cache:
            self._category_cache = {}
        for category in categories:
            self._category_cache[category.id] = category

        return categories

    async def get_category_tree(self) -> List[CategoryTreeNode]:
        """Get the complete category hierarchy as a tree."""
        if self._category_tree_cache:
            return self._category_tree_cache

        # Load all categories
        self.cosmos.set_container(self.category_container)
        query = "SELECT * FROM c WHERE c.status = 'active' ORDER BY c.level, c.order"
        results = await self.cosmos.query_items(query, cross_partition=True)

        categories = [ClauseCategory(**doc) for doc in results]

        # Build tree structure
        tree = self._build_category_tree(categories)
        self._category_tree_cache = tree

        return tree

    async def create_category(
        self,
        request: CreateCategoryRequest,
        user_email: str
    ) -> ClauseCategory:
        """Create a new category."""
        logger.info(f"Creating new category: {request.name}")

        # Determine level and path
        if request.parent_id:
            parent = await self.get_category(request.parent_id)
            if not parent:
                raise ValueError(f"Parent category not found: {request.parent_id}")

            if parent.level >= 3:
                raise ValueError("Maximum category depth is 3 levels")

            level = parent.level + 1
            path = parent.path + [self._sanitize_id(request.name)]
            display_path = f"{parent.display_path} > {request.name}"
        else:
            level = 1
            path = [self._sanitize_id(request.name)]
            display_path = request.name

        # Get next order number
        query = "SELECT VALUE MAX(c.order) FROM c WHERE c.parent_id = @parent_id"
        params = [{"name": "@parent_id", "value": request.parent_id if request.parent_id else "null"}]
        self.cosmos.set_container(self.category_container)
        results = await self.cosmos.parameterized_query(
            query,
            params,
            cross_partition=True
        )
        max_order = results[0] if results and results[0] else 0

        # Create category
        category = ClauseCategory(
            id=path[-1],
            type="category",
            level=level,
            name=request.name,
            description=request.description,
            parent_id=request.parent_id,
            path=path,
            display_path=display_path,
            order=max_order + 1,
            icon=request.icon,
            is_predefined=False,
            clause_count=0,
            audit=AuditInfo(
                created_by=user_email,
                created_date=datetime.utcnow()
            )
        )

        # Save to CosmosDB
        self.cosmos.set_container(self.category_container)
        await self.cosmos.upsert_item(category.model_dump(mode='json', exclude_none=True))

        # Invalidate cache
        self._category_cache = None
        self._category_tree_cache = None

        logger.info(f"Category created successfully: {category.id}")
        return category

    # ========== Variable Management ==========

    async def get_system_variables(self) -> SystemVariables:
        """Get system variables configuration."""
        query = "SELECT * FROM c WHERE c.id = 'system_variables'"
        self.cosmos.set_container(self.clause_container)
        results = await self.cosmos.query_items(query, cross_partition=False, pk="system_variables")

        if results:
            return SystemVariables(**results[0])

        # Return empty if not found
        return SystemVariables(
            variables=[],
            custom_variables=[],
            audit=AuditInfo(
                created_by="system",
                created_date=datetime.utcnow()
            )
        )

    async def create_custom_variable(
        self,
        request: CreateCustomVariableRequest,
        user_email: str
    ) -> ClauseVariable:
        """Create a new custom variable."""
        logger.info(f"Creating custom variable: {request.name}")

        # Get current system variables
        sys_vars = await self.get_system_variables()

        # Check if variable already exists
        all_vars = sys_vars.variables + sys_vars.custom_variables
        if any(v.name == request.name for v in all_vars):
            raise ValueError(f"Variable already exists: {request.name}")

        # Create new custom variable
        custom_var = ClauseVariable(
            name=request.name,
            type="custom",
            display_name=request.display_name,
            description=request.description,
            data_type=request.data_type,
            default_value=f"[{request.display_name}]"
        )

        sys_vars.custom_variables.append(custom_var)
        sys_vars.audit.modified_by = user_email
        sys_vars.audit.modified_date = datetime.utcnow()

        # Save to CosmosDB
        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(sys_vars.model_dump(mode='json', exclude_none=True))

        logger.info(f"Custom variable created: {request.name}")
        return custom_var

    # ========== Comparison & AI Operations ==========

    @performance_monitor("compare_clause")
    async def compare_clause(
        self,
        request: CompareClauseRequest,
        user_email: str,
        use_cache: bool = True,
        model_selection: str = "primary"
    ) -> ClauseComparison:
        """
        Compare contract text with a clause from the library using AI.

        Args:
            request: Comparison request with clause_id and contract_text
            user_email: Email of user performing comparison
            use_cache: Whether to use cached comparison results (default: True)
            model_selection: Which model to use - "primary" or "secondary" (default: "primary")

        Returns:
            ClauseComparison with detailed analysis
        """
        start_time = time.time()
        self._metrics["comparisons_total"] += 1

        logger.info(f"Comparing clause: {request.clause_id} with model: {model_selection}")

        # Get clause from library
        clause = await self.get_clause(request.clause_id)
        if not clause:
            raise ValueError(f"Clause not found: {request.clause_id}")

        # Select the appropriate AI client and model
        if model_selection == "secondary":
            if not self.ai.aoai_client_secondary:
                raise ValueError("Secondary model not configured. Please set CAIG_AZURE_OPENAI_*_SECONDARY environment variables.")
            client = self.ai.aoai_client_secondary
            deployment = self.ai.completions_deployment_secondary
        else:
            client = self.ai.aoai_client
            deployment = self.ai.completions_deployment

        # Generate cache key (include model selection to cache separately per model)
        cache_key = self._generate_comparison_cache_key(
            request.clause_id,
            request.contract_text
        ) + f":{model_selection}"
        logger.debug(f"Cache key: {cache_key[:32]}...")

        # Check cache
        if use_cache:
            cached_result = self._comparison_cache.get(cache_key)
            if cached_result:
                self._metrics["comparisons_cached"] += 1
                elapsed = time.time() - start_time
                logger.info(f"[CACHE HIT] Comparison retrieved from cache in {elapsed:.3f}s")
                return cached_result
            else:
                logger.debug(f"[CACHE MISS] No cached result found, will process with AI")

        # Build AI prompt for comparison
        prompt = self._build_comparison_prompt(
            clause.content.plain_text,
            request.contract_text,
            clause.name
        )

        # Call Azure OpenAI for analysis
        logger.info(f"Using model: {deployment} ({model_selection})")
        try:
            completion = client.chat.completions.create(
                model=deployment,
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response = {
                "choices": [
                    {
                        "message": {
                            "content": completion.choices[0].message.content
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                    "completion_tokens": completion.usage.completion_tokens if completion.usage else 0
                }
            }
        except Exception as e:
            logger.error(f"Error calling Azure OpenAI: {e}")
            raise

        # Parse AI response to extract comparison, risks, and recommendations
        comparison_result = self._parse_ai_comparison_response(response)

        # Create comparison document
        comparison_id = str(uuid.uuid4())
        now = datetime.utcnow()

        comparison = ClauseComparison(
            id=comparison_id,
            type="comparison_result",
            clause_library_id=request.clause_id,
            contract_id=request.contract_id,
            contract_text=request.contract_text,
            clause_library_text=clause.content.plain_text,
            comparison=comparison_result["comparison"],
            risk_analysis=comparison_result["risk_analysis"],
            recommendations=comparison_result["recommendations"],
            ai_analysis=AIAnalysisInfo(
                model=deployment,
                completion_tokens=response.get("usage", {}).get("completion_tokens", 0),
                analysis_date=now
            ),
            audit=AuditInfo(
                created_by=user_email,
                created_date=now
            )
        )

        # Save comparison result
        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(comparison.model_dump(mode='json', exclude_none=True))

        # Update clause usage stats
        clause.usage_stats.times_used += 1
        clause.usage_stats.last_used_date = now
        if clause.usage_stats.average_comparison_score:
            clause.usage_stats.average_comparison_score = (
                clause.usage_stats.average_comparison_score * 0.9 +
                comparison.comparison.similarity_score * 0.1
            )
        else:
            clause.usage_stats.average_comparison_score = comparison.comparison.similarity_score

        self.cosmos.set_container(self.clause_container)
        await self.cosmos.upsert_item(clause.model_dump(mode='json', exclude_none=True))

        # Always cache the comparison result for future use
        # (even if current request didn't want cache, future requests might)
        self._comparison_cache.put(cache_key, comparison)
        logger.debug(f"[CACHE STORE] Comparison result cached with key: {cache_key[:32]}...")

        # Update performance metrics
        elapsed = time.time() - start_time
        self._metrics["avg_comparison_time"] = (
            (self._metrics["avg_comparison_time"] * (self._metrics["comparisons_total"] - 1) + elapsed) /
            self._metrics["comparisons_total"]
        )

        logger.info(f"Comparison completed: {comparison_id} in {elapsed:.3f}s (tokens: {response.get('usage', {}).get('completion_tokens', 0)})")

        # Track model usage for analytics
        if self.ai.llm_tracker:
            asyncio.create_task(
                self.ai.llm_tracker.track_completion(
                    user_email=user_email,
                    operation="clause_comparison",
                    model=completion.model,
                    prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=response.get("usage", {}).get("completion_tokens", 0),
                    elapsed_time=elapsed,
                    operation_details={
                        "clause_id": request.clause_id,
                        "model_selection": model_selection,
                        "from_cache": False
                    },
                    success=True
                )
            )

        return comparison

    @performance_monitor("suggest_clause")
    async def suggest_clause(
        self,
        request: SuggestClauseRequest
    ) -> List[Tuple[Clause, float]]:
        """
        Use AI to suggest the best matching clauses for given text.

        Uses optimized embedding generation with caching and legal text preprocessing.
        """
        logger.info("Suggesting clauses using AI vector search")

        # Generate embedding for contract text (using optimized method)
        embedding = await self._generate_embedding_optimized(request.contract_text)

        if not embedding:
            raise ValueError("Failed to generate embedding for contract text")

        logger.debug(f"Generated embedding with {len(embedding)} dimensions")

        # Set container for query
        self.cosmos.set_container(self.clause_container)

        # Build vector search query
        # Note: CosmosDB vector search requires embedding to be embedded directly in SQL,
        # not as a parameter. This is the supported pattern.
        embedding_str = str(embedding)  # Convert list to string representation

        # Build base query with vector distance
        query_parts = []
        query_parts.append(f"SELECT TOP {request.top_k}")
        query_parts.append(f"c.id, c.name, c.category_id, c.category_path_display,")
        query_parts.append(f"VectorDistance(c.embedding, {embedding_str}) AS similarity")
        query_parts.append(f"FROM c")
        query_parts.append(f"WHERE c.type = 'clause' AND c.status = 'active'")

        if request.category_id:
            query_parts.append(f"AND c.category_id = '{request.category_id}'")

        query_parts.append(f"ORDER BY VectorDistance(c.embedding, {embedding_str})")

        query = " ".join(query_parts)
        logger.debug(f"Vector search query: {query[:200]}...")

        try:
            # Execute query without parameters (embedding is embedded in SQL)
            results = await self.cosmos.query_items(
                query,
                cross_partition=True
            )

            # Now fetch full clause documents using the IDs
            suggestions = []
            for result in results:
                clause_id = result.get('id')
                similarity_score = 1.0 - result.get('similarity', 0)  # Convert distance to similarity

                # Fetch full clause document
                clause = await self.get_clause(clause_id)
                if clause:
                    suggestions.append((clause, similarity_score))
                else:
                    logger.warning(f"Could not fetch clause {clause_id}")

            logger.info(f"Found {len(suggestions)} clause suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Vector search query failed: {e}")
            logger.error(f"Query: {query[:500]}")
            logger.error(f"Embedding dimension: {len(embedding)}")
            raise

    # ========== Cache Management Methods ==========

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and performance metrics."""
        return {
            "comparison_cache": {
                "size": self._comparison_cache.size(),
                "max_size": self._comparison_cache.max_size,
                "ttl_seconds": self._comparison_cache.ttl_seconds
            },
            "embedding_cache": {
                "size": self._embedding_cache.size(),
                "max_size": self._embedding_cache.max_size,
                "ttl_seconds": self._embedding_cache.ttl_seconds
            },
            "metrics": self._metrics
        }

    def clear_caches(self):
        """Clear all caches."""
        self._comparison_cache.clear()
        self._embedding_cache.clear()
        self._category_cache = None
        self._category_tree_cache = None
        logger.info("All caches cleared")

    # ========== Optimized Embedding Generation ==========

    async def _generate_embedding_optimized(
        self,
        text: str,
        use_cache: bool = True
    ) -> Optional[List[float]]:
        """
        Generate embedding with caching and optimization for legal text.

        Optimizations:
        - Caching to avoid redundant API calls
        - Text preprocessing specific to legal content
        - Chunking for very large texts
        - Performance monitoring
        """
        start_time = time.time()
        self._metrics["embeddings_total"] += 1

        # Preprocess text for legal content
        preprocessed_text = self._preprocess_legal_text(text)

        # Generate cache key
        cache_key = self._generate_text_hash(preprocessed_text)

        # Check cache
        if use_cache:
            cached_embedding = self._embedding_cache.get(cache_key)
            if cached_embedding:
                self._metrics["embeddings_cached"] += 1
                elapsed = time.time() - start_time
                logger.debug(f"[CACHE HIT] Embedding retrieved from cache in {elapsed:.3f}s")
                return cached_embedding

        # Handle very large texts (>8000 tokens ≈ 32000 chars)
        if len(preprocessed_text) > 32000:
            logger.warning(f"Text too large ({len(preprocessed_text)} chars), chunking for embedding")
            preprocessed_text = preprocessed_text[:32000]

        try:
            # Generate embedding
            embedding_response = self.ai.generate_embeddings(preprocessed_text)
            embedding = embedding_response.data[0].embedding if embedding_response else None

            # Always cache the embedding for future use
            if embedding:
                self._embedding_cache.put(cache_key, embedding)

            # Update metrics
            elapsed = time.time() - start_time
            self._metrics["avg_embedding_time"] = (
                (self._metrics["avg_embedding_time"] * (self._metrics["embeddings_total"] - 1) + elapsed) /
                self._metrics["embeddings_total"]
            )

            logger.debug(f"[PERF] Embedding generated in {elapsed:.3f}s")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def _preprocess_legal_text(self, text: str) -> str:
        """
        Preprocess legal text for better embedding quality.

        Optimizations for legal content:
        - Normalize whitespace
        - Remove excessive formatting
        - Preserve legal terminology
        - Maintain clause structure
        """
        # Remove HTML artifacts if present
        text = re.sub(r'<[^>]+>', ' ', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove extra punctuation but preserve legal references
        text = re.sub(r'([^\w\s\(\)\[\]\{\}§¶])\1+', r'\1', text)

        # Trim and clean
        text = text.strip()

        return text

    def _generate_text_hash(self, text: str) -> str:
        """Generate a hash key for text caching."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _generate_comparison_cache_key(
        self,
        clause_id: str,
        contract_text: str
    ) -> str:
        """Generate cache key for comparison results."""
        text_hash = self._generate_text_hash(contract_text)
        return f"comparison:{clause_id}:{text_hash}"

    # ========== Helper Methods ==========

    async def _load_category_cache(self):
        """Load categories into memory cache."""
        # Set container before querying
        self.cosmos.set_container(self.category_container)

        query = "SELECT * FROM c WHERE c.status = 'active'"
        results = await self.cosmos.query_items(query, cross_partition=True)

        self._category_cache = {
            doc["id"]: ClauseCategory(**doc)
            for doc in results
        }

        logger.info(f"Loaded {len(self._category_cache)} categories into cache")

    def _build_category_tree(
        self,
        categories: List[ClauseCategory],
        parent_id: Optional[str] = None
    ) -> List[CategoryTreeNode]:
        """Recursively build category tree."""
        tree = []

        for category in categories:
            if category.parent_id == parent_id:
                node = CategoryTreeNode(
                    category=category,
                    children=self._build_category_tree(categories, category.id),
                    clause_count=category.clause_count
                )
                tree.append(node)

        return tree

    def _html_to_plain_text(self, html_content: str) -> str:
        """Convert HTML to plain text."""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)

    def _extract_variables_from_html(self, html_content: str) -> List[ClauseVariable]:
        """Extract variable placeholders from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        variables = []

        # Find all spans with class "variable"
        var_spans = soup.find_all('span', class_='variable')

        for span in var_spans:
            var_name = span.get('data-var')
            if var_name:
                variables.append(ClauseVariable(
                    name=var_name,
                    type="custom",  # Will be updated based on system variables
                    default_value=span.get_text(),
                    description=f"Variable: {var_name}"
                ))

        return variables

    def _sanitize_id(self, name: str) -> str:
        """Sanitize category name to create ID."""
        sanitized = name.lower()
        sanitized = re.sub(r'[^\w\s-]', '', sanitized)
        sanitized = re.sub(r'[\s_-]+', '_', sanitized)
        return sanitized.strip('_')

    async def _increment_category_count(self, category_id: str):
        """Increment clause count for a category and all parent categories."""
        category = await self.get_category(category_id)
        if category:
            category.clause_count += 1
            self.cosmos.set_container(self.category_container)
            await self.cosmos.upsert_item(category.model_dump(mode='json', exclude_none=True))

            # Recursively update parent categories
            if category.parent_id:
                await self._increment_category_count(category.parent_id)
            else:
                # Only invalidate cache once at the root level to improve performance
                self._category_cache = None
                self._category_tree_cache = None

    async def _decrement_category_count(self, category_id: str):
        """Decrement clause count for a category and all parent categories."""
        category = await self.get_category(category_id)
        if category:
            category.clause_count = max(0, category.clause_count - 1)
            self.cosmos.set_container(self.category_container)
            await self.cosmos.upsert_item(category.model_dump(mode='json', exclude_none=True))

            # Recursively update parent categories
            if category.parent_id:
                await self._decrement_category_count(category.parent_id)
            else:
                # Only invalidate cache once at the root level to improve performance
                self._category_cache = None
                self._category_tree_cache = None

    async def recalculate_category_counts(self) -> Dict[str, int]:
        """
        Recalculate clause counts for all categories from scratch.
        Returns a dictionary mapping category_id to the corrected count.

        This is useful for fixing incorrect counts that may have accumulated
        due to bugs or data inconsistencies.
        """
        logger.info("Recalculating category clause counts...")

        # Get all active clauses grouped by category
        self.cosmos.set_container(self.clause_container)
        query = """
        SELECT c.category_id, COUNT(1) as clause_count
        FROM c
        WHERE c.type = 'clause' AND c.status = 'active'
        GROUP BY c.category_id
        """
        results = await self.cosmos.query_items(query, cross_partition=True)

        # Build a map of category_id -> direct clause count
        direct_counts = {result['category_id']: result['clause_count'] for result in results}

        # Get all categories
        categories = await self.get_all_categories()
        category_map = {cat.id: cat for cat in categories}

        # Calculate total counts (including child categories)
        total_counts = {}

        def calculate_total_count(category_id: str) -> int:
            """Recursively calculate total count for a category including all children."""
            if category_id in total_counts:
                return total_counts[category_id]

            # Start with direct clause count
            count = direct_counts.get(category_id, 0)

            # Add counts from all child categories
            for cat in categories:
                if cat.parent_id == category_id:
                    count += calculate_total_count(cat.id)

            total_counts[category_id] = count
            return count

        # Calculate counts for all categories
        for category in categories:
            calculate_total_count(category.id)

        # Update all categories with corrected counts
        self.cosmos.set_container(self.category_container)
        updated_count = 0

        for category_id, new_count in total_counts.items():
            category = category_map.get(category_id)
            if category and category.clause_count != new_count:
                category.clause_count = new_count
                await self.cosmos.upsert_item(category.model_dump(mode='json', exclude_none=True))
                updated_count += 1
                logger.info(f"Updated category '{category.name}': {category.clause_count} -> {new_count}")

        # Invalidate caches
        self._category_cache = None
        self._category_tree_cache = None

        logger.info(f"Category count recalculation complete. Updated {updated_count} categories.")
        return total_counts

    def _build_comparison_prompt(
        self,
        library_text: str,
        contract_text: str,
        clause_name: str
    ) -> str:
        """Build AI prompt for clause comparison."""
        return f"""You are a legal contract analysis expert. Compare the following two clause texts and provide a detailed analysis.

**Standard Clause from Library** ("{clause_name}"):
{library_text}

**Clause from Contract**:
{contract_text}

Please analyze and provide:

1. **Similarity Score**: A number between 0 and 1 indicating how similar the texts are (1 = identical, 0 = completely different)

2. **Differences**: Identify all significant differences between the two texts. For each difference, specify:
   - Type: "missing" (in library but not contract), "different" (different wording), or "extra" (in contract but not library)
   - Location: Which paragraph or section
   - Library text vs Contract text
   - Severity: "low", "medium", or "high"

3. **Risk Analysis**: Analyze potential legal risks with:
   - Overall risk level: "low", "medium", or "high"
   - Risk score: 0 to 1
   - List of specific risks with category, description, severity, impact, and location

4. **Recommendations**: Provide specific actionable recommendations:
   - Type: "replacement", "addition", "deletion", or "modification"
   - Priority: "low", "medium", or "high"
   - Description and rationale
   - Original text and suggested text

Return your analysis in the following JSON format:
{{
  "similarity_score": 0.85,
  "differences": [
    {{
      "type": "missing",
      "location": "paragraph 2",
      "library_text": "text from library",
      "contract_text": null,
      "severity": "high"
    }}
  ],
  "risk_analysis": {{
    "overall_risk": "medium",
    "risk_score": 0.65,
    "risks": [
      {{
        "category": "liability",
        "description": "description",
        "severity": "high",
        "impact": "impact description",
        "location": "location in text"
      }}
    ]
  }},
  "recommendations": [
    {{
      "type": "replacement",
      "priority": "high",
      "description": "what to do",
      "original_text": "original text",
      "suggested_text": "suggested text",
      "location": "where to apply",
      "rationale": "why this is recommended"
    }}
  ]
}}"""

    def _parse_ai_comparison_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response into structured comparison result."""
        # Extract content from response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse JSON from content
        try:
            # Try to find JSON block in response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                parsed = json.loads(json_str)

                # Convert to Pydantic models
                return {
                    "comparison": ComparisonResult(
                        similarity_score=parsed.get("similarity_score", 0.0),
                        differences=[
                            ComparisonDifference(**diff)
                            for diff in parsed.get("differences", [])
                        ]
                    ),
                    "risk_analysis": RiskAnalysis(
                        overall_risk=parsed["risk_analysis"].get("overall_risk", "medium"),
                        risk_score=parsed["risk_analysis"].get("risk_score", 0.5),
                        risks=[
                            RiskItem(**risk)
                            for risk in parsed["risk_analysis"].get("risks", [])
                        ]
                    ),
                    "recommendations": [
                        Recommendation(**rec)
                        for rec in parsed.get("recommendations", [])
                    ]
                }
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            logger.error(f"Response content: {content}")

        # Fallback to empty result
        return {
            "comparison": ComparisonResult(
                similarity_score=0.0,
                differences=[]
            ),
            "risk_analysis": RiskAnalysis(
                overall_risk="medium",
                risk_score=0.5,
                risks=[]
            ),
            "recommendations": []
        }

