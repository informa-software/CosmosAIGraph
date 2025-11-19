"""
Analysis Results Service

Manages storage and retrieval of analysis results for PDF generation
and historical tracking. Supports both comparison and query results.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.models.analysis_results_models import (
    AnalysisResult,
    AnalysisMetadata,
    ComparisonData,
    QueryData,
    ContractQueried,
    SaveComparisonRequest,
    SaveQueryRequest
)
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)


class AnalysisResultsService:
    """Service for managing analysis results storage"""

    def __init__(self, cosmos_service: CosmosNoSQLService):
        self.cosmos_service = cosmos_service
        self.container_name = "analysis_results"

    async def save_comparison_result(
        self,
        request: SaveComparisonRequest
    ) -> str:
        """
        Store comparison results and return result_id

        Args:
            request: Comparison result data to store

        Returns:
            result_id: Unique identifier for the stored result
        """
        # Generate unique result ID
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        result_id = f"result_{timestamp}_{uuid4().hex[:8]}"

        logger.info(f"Saving comparison result: {result_id}")
        logger.info(f"  - Standard contract: {request.standard_contract_id}")
        logger.info(f"  - Compare contracts: {request.compare_contract_ids}")
        logger.info(f"  - Mode: {request.comparison_mode}")

        # Create metadata if not provided
        if not request.metadata:
            title = f"Comparison: {request.standard_contract_id} vs {len(request.compare_contract_ids)} contract(s)"
            request.metadata = AnalysisMetadata(
                title=title,
                description=f"{request.comparison_mode} comparison"
            )

        # Create comparison data
        comparison_data = ComparisonData(
            standard_contract_id=request.standard_contract_id,
            compare_contract_ids=request.compare_contract_ids,
            comparison_mode=request.comparison_mode,
            selected_clauses=request.selected_clauses,
            results=request.results
        )

        # Create result document
        result = AnalysisResult(
            id=result_id,
            result_id=result_id,
            result_type="comparison",
            user_id=request.user_id,
            created_at=datetime.utcnow(),
            status="completed",
            metadata=request.metadata,
            comparison_data=comparison_data
        )

        # Store in CosmosDB
        self.cosmos_service.set_container(self.container_name)
        result_dict = result.model_dump(mode='json')

        await self.cosmos_service.upsert_item(result_dict)

        logger.info(f"Comparison result saved successfully: {result_id}")
        return result_id

    async def save_query_result(
        self,
        request: SaveQueryRequest
    ) -> str:
        """
        Store query results and return result_id

        Args:
            request: Query result data to store

        Returns:
            result_id: Unique identifier for the stored result
        """
        # Generate unique result ID
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        result_id = f"result_{timestamp}_{uuid4().hex[:8]}"

        logger.info(f"Saving query result: {result_id}")
        logger.info(f"  - Query: {request.query_text[:100]}...")
        logger.info(f"  - Contracts queried: {len(request.contracts_queried)}")

        # Create metadata if not provided
        if not request.metadata:
            title = f"Query: {request.query_text[:50]}..."
            request.metadata = AnalysisMetadata(
                title=title,
                description=f"Analyzed {len(request.contracts_queried)} contracts"
            )

        # Create query data
        query_data = QueryData(
            query_text=request.query_text,
            query_type=request.query_type,
            contracts_queried=request.contracts_queried,
            results=request.results
        )

        # Create result document
        result = AnalysisResult(
            id=result_id,
            result_id=result_id,
            result_type="query",
            user_id=request.user_id,
            created_at=datetime.utcnow(),
            status="completed",
            metadata=request.metadata,
            query_data=query_data
        )

        # Store in CosmosDB
        self.cosmos_service.set_container(self.container_name)
        result_dict = result.model_dump(mode='json')

        await self.cosmos_service.upsert_item(result_dict)

        logger.info(f"Query result saved successfully: {result_id}")
        return result_id

    async def get_result(
        self,
        result_id: str,
        user_id: str
    ) -> Optional[AnalysisResult]:
        """
        Retrieve a result by ID

        Args:
            result_id: Result identifier
            user_id: User identifier (for security/partition key)

        Returns:
            AnalysisResult or None if not found
        """
        self.cosmos_service.set_container(self.container_name)

        try:
            item = await self.cosmos_service.point_read(
                id=result_id,
                pk=user_id
            )

            if item:
                return AnalysisResult(**item)
            return None

        except Exception as e:
            logger.error(f"Error retrieving result {result_id}: {str(e)}")
            return None

    async def list_user_results(
        self,
        user_id: str,
        result_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AnalysisResult]:
        """
        List results for a user with optional filters

        Args:
            user_id: User identifier
            result_type: Optional filter by "comparison" or "query"
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of AnalysisResult objects
        """
        self.cosmos_service.set_container(self.container_name)

        # Build query
        query = "SELECT * FROM c WHERE c.user_id = @user_id"
        parameters = [{"name": "@user_id", "value": user_id}]

        if result_type:
            query += " AND c.result_type = @result_type"
            parameters.append({"name": "@result_type", "value": result_type})

        # Order by most recent first
        query += " ORDER BY c.created_at DESC"

        # Add pagination
        query += f" OFFSET {offset} LIMIT {limit}"

        logger.info(f"Querying results for user: {user_id}")
        if result_type:
            logger.info(f"  - Filtered by type: {result_type}")

        items = await self.cosmos_service.parameterized_query(
            sql_template=query,
            sql_parameters=parameters,
            cross_partition=False  # We're filtering by partition key (user_id)
        )

        results = [AnalysisResult(**item) for item in items]
        logger.info(f"Retrieved {len(results)} results")

        return results

    async def delete_result(
        self,
        result_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a result

        Args:
            result_id: Result identifier
            user_id: User identifier (for security/partition key)

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting result: {result_id}")

        self.cosmos_service.set_container(self.container_name)

        try:
            await self.cosmos_service.delete_item(
                id=result_id,
                pk=user_id
            )
            logger.info(f"Result deleted: {result_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting result {result_id}: {str(e)}")
            return False

    async def get_user_statistics(self, user_id: str) -> dict:
        """
        Get aggregate statistics for a user's results

        Args:
            user_id: User identifier

        Returns:
            Dictionary with statistics
        """
        self.cosmos_service.set_container(self.container_name)

        # Total results
        total_query = """
            SELECT VALUE COUNT(1)
            FROM c
            WHERE c.user_id = @user_id
        """
        total_result = await self.cosmos_service.parameterized_query(
            sql_template=total_query,
            sql_parameters=[{"name": "@user_id", "value": user_id}],
            cross_partition=False
        )
        total_results = total_result[0] if total_result else 0

        # Results by type
        type_query = """
            SELECT c.result_type, COUNT(1) as count
            FROM c
            WHERE c.user_id = @user_id
            GROUP BY c.result_type
        """
        type_results = await self.cosmos_service.parameterized_query(
            sql_template=type_query,
            sql_parameters=[{"name": "@user_id", "value": user_id}],
            cross_partition=False
        )

        # Recent results (last 30 days)
        thirty_days_ago = datetime.utcnow().timestamp() - (30 * 24 * 60 * 60)
        recent_query = """
            SELECT VALUE COUNT(1)
            FROM c
            WHERE c.user_id = @user_id
              AND c.created_at >= @since
        """
        recent_result = await self.cosmos_service.parameterized_query(
            sql_template=recent_query,
            sql_parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@since", "value": datetime.fromtimestamp(thirty_days_ago).isoformat()}
            ],
            cross_partition=False
        )
        recent_count = recent_result[0] if recent_result else 0

        return {
            "total_results": total_results,
            "by_type": {r['result_type']: r['count'] for r in type_results},
            "last_30_days": recent_count
        }
