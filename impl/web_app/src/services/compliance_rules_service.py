"""
Compliance Rules Service

Manages CRUD operations for compliance rules including category management
and tracking rule updates for stale result detection.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.models.compliance_models import (
    ComplianceRule,
    Category,
    RuleSeverity,
    get_predefined_categories,
    validate_category_name
)
from src.services.cosmos_nosql_service import CosmosNoSQLService

logger = logging.getLogger(__name__)


class ComplianceRulesService:
    """
    Service for managing compliance rules in CosmosDB.

    Provides CRUD operations, category management, and utilities
    for tracking rule updates and identifying stale evaluations.
    """

    def __init__(self, cosmos_service: CosmosNoSQLService):
        """
        Initialize the compliance rules service.

        Args:
            cosmos_service: Initialized CosmosDB service instance
        """
        self.cosmos_service = cosmos_service
        self.container_name = "compliance_rules"

    async def create_rule(self, rule_data: Dict[str, Any]) -> ComplianceRule:
        """
        Create a new compliance rule.

        Args:
            rule_data: Dictionary with rule fields (name, description, severity, category, etc.)

        Returns:
            Created ComplianceRule instance

        Raises:
            ValueError: If validation fails
            Exception: If CosmosDB operation fails
        """
        try:
            # Create rule instance (validates fields)
            rule = ComplianceRule(**rule_data)

            # Store in CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.create_item(rule.to_dict())

            logger.info(f"Created compliance rule: {rule.id} - {rule.name}")
            return ComplianceRule.from_dict(doc)

        except ValueError as e:
            logger.error(f"Validation error creating rule: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create rule: {e}")
            raise

    async def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """
        Get a compliance rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            ComplianceRule if found, None otherwise
        """
        try:
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.point_read(rule_id, rule_id)  # partition key is /id

            if doc:
                return ComplianceRule.from_dict(doc)
            return None

        except Exception as e:
            logger.error(f"Failed to get rule {rule_id}: {e}")
            raise

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> ComplianceRule:
        """
        Update a compliance rule.

        Args:
            rule_id: Rule ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated ComplianceRule instance

        Raises:
            ValueError: If rule not found or validation fails
            Exception: If CosmosDB operation fails
        """
        try:
            # Get existing rule
            existing_rule = await self.get_rule(rule_id)
            if not existing_rule:
                raise ValueError(f"Rule not found: {rule_id}")

            # Apply updates
            existing_rule.update(**updates)

            # Save to CosmosDB
            self.cosmos_service.set_container(self.container_name)
            doc = await self.cosmos_service.upsert_item(existing_rule.to_dict())

            logger.info(f"Updated compliance rule: {rule_id} - {existing_rule.name}")
            return ComplianceRule.from_dict(doc)

        except ValueError as e:
            logger.error(f"Validation error updating rule: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to update rule {rule_id}: {e}")
            raise

    async def delete_rule(self, rule_id: str) -> bool:
        """
        Delete a compliance rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if deleted, False if not found

        Note:
            This does NOT delete associated results. Results remain for historical tracking.
        """
        try:
            self.cosmos_service.set_container(self.container_name)
            await self.cosmos_service.delete_item(rule_id, rule_id)  # partition key is /id

            logger.info(f"Deleted compliance rule: {rule_id}")
            return True

        except Exception as e:
            logger.warning(f"Failed to delete rule {rule_id}: {e}")
            return False

    async def list_rules(
        self,
        active_only: bool = True,
        category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[ComplianceRule]:
        """
        List compliance rules with optional filtering.

        Args:
            active_only: If True, return only active rules
            category: Filter by category (optional)
            severity: Filter by severity (optional)

        Returns:
            List of ComplianceRule instances
        """
        try:
            self.cosmos_service.set_container(self.container_name)

            # Build query
            where_clauses = []
            if active_only:
                where_clauses.append("c.active = true")
            if category:
                where_clauses.append(f"c.category = '{category}'")
            if severity:
                where_clauses.append(f"c.severity = '{severity}'")

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            query = f"SELECT * FROM c WHERE {where_clause} ORDER BY c.created_date DESC"

            docs = await self.cosmos_service.query_items(query, cross_partition=True)

            rules = [ComplianceRule.from_dict(doc) for doc in docs]
            logger.info(f"Retrieved {len(rules)} compliance rules (active_only={active_only}, category={category}, severity={severity})")

            return rules

        except Exception as e:
            logger.error(f"Failed to list rules: {e}")
            raise

    async def get_rules_by_category(self, category: str) -> List[ComplianceRule]:
        """
        Get all active rules in a specific category.

        Args:
            category: Category name

        Returns:
            List of ComplianceRule instances
        """
        return await self.list_rules(active_only=True, category=category)

    async def get_rules_by_severity(self, severity: str) -> List[ComplianceRule]:
        """
        Get all active rules with specific severity.

        Args:
            severity: Severity level (critical, high, medium, low)

        Returns:
            List of ComplianceRule instances
        """
        return await self.list_rules(active_only=True, severity=severity)

    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        Get all categories with rule counts.

        Returns:
            List of category dictionaries with counts
        """
        try:
            # Get predefined categories
            categories_dict = {cat.name: cat for cat in get_predefined_categories()}

            # Get all rules to count by category
            all_rules = await self.list_rules(active_only=False)

            # Count rules per category
            category_counts = {}
            for rule in all_rules:
                category_counts[rule.category] = category_counts.get(rule.category, 0) + 1

                # Add to categories dict if it's a custom category
                if rule.category not in categories_dict:
                    categories_dict[rule.category] = Category(
                        name=rule.category,
                        display_name=rule.category.replace('_', ' ').title(),
                        description="User-defined category"
                    )

            # Build result with counts
            result = []
            for cat in categories_dict.values():
                result.append({
                    "name": cat.name,
                    "display_name": cat.display_name,
                    "description": cat.description,
                    "rule_count": category_counts.get(cat.name, 0)
                })

            logger.info(f"Retrieved {len(result)} categories")
            return sorted(result, key=lambda x: x["display_name"])

        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            raise

    async def create_category(self, name: str, display_name: str, description: Optional[str] = None) -> Category:
        """
        Create or update a custom category.

        Args:
            name: Category internal name (lowercase, underscores)
            display_name: Human-readable name
            description: Optional description

        Returns:
            Category instance

        Raises:
            ValueError: If name format is invalid

        Note:
            Categories are not stored separately - they're derived from rules.
            This method validates the category name and can be used for validation.
        """
        if not validate_category_name(name):
            raise ValueError(f"Invalid category name: {name}. Use lowercase letters, numbers, underscores, and hyphens only.")

        category = Category(name=name, display_name=display_name, description=description)
        logger.info(f"Validated/created category: {name}")

        return category

    async def get_stale_count_for_rule(self, rule_id: str) -> int:
        """
        Get count of stale evaluation results for a rule.

        Args:
            rule_id: Rule ID

        Returns:
            Number of stale results (evaluations older than rule's updated_date)
        """
        try:
            # Get the rule
            rule = await self.get_rule(rule_id)
            if not rule:
                return 0

            # Query compliance_results for this rule where rule_version_date < rule.updated_date
            self.cosmos_service.set_container("compliance_results")

            query = f"""
                SELECT VALUE COUNT(1)
                FROM c
                WHERE c.rule_id = '{rule_id}'
                AND c.rule_version_date < '{rule.updated_date}'
            """

            result = await self.cosmos_service.query_items(query, cross_partition=True)
            count = result[0] if result else 0

            logger.info(f"Rule {rule_id} has {count} stale evaluation results")
            return count

        except Exception as e:
            logger.error(f"Failed to get stale count for rule {rule_id}: {e}")
            return 0

    async def get_rules_with_stale_results(self) -> List[Dict[str, Any]]:
        """
        Get all rules that have stale evaluation results.

        Returns:
            List of dicts with rule info and stale count
        """
        try:
            rules = await self.list_rules(active_only=True)
            stale_rules = []

            for rule in rules:
                stale_count = await self.get_stale_count_for_rule(rule.id)
                if stale_count > 0:
                    stale_rules.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "stale_count": stale_count,
                        "updated_date": rule.updated_date
                    })

            logger.info(f"Found {len(stale_rules)} rules with stale results")
            return stale_rules

        except Exception as e:
            logger.error(f"Failed to get rules with stale results: {e}")
            raise

    async def get_rules_by_rule_set(self, rule_set_id: str, active_only: bool = True) -> List[ComplianceRule]:
        """
        Get all rules that belong to a specific rule set.

        Args:
            rule_set_id: The ID of the rule set
            active_only: Whether to return only active rules

        Returns:
            List of rules in the rule set

        Raises:
            Exception: If retrieval fails
        """
        try:
            # Set container
            self.cosmos_service.set_container(self.container_name)

            # Build query to find rules containing this rule_set_id
            query = f"SELECT * FROM c WHERE ARRAY_CONTAINS(c.rule_set_ids, '{rule_set_id}')"

            if active_only:
                query += " AND c.active = true"

            documents = await self.cosmos_service.query_items(query, cross_partition=True)
            rules = [ComplianceRule.from_dict(doc) for doc in documents]

            logger.info(f"Found {len(rules)} rules in rule set {rule_set_id}")
            return rules

        except Exception as e:
            logger.error(f"Failed to get rules for rule set {rule_set_id}: {e}")
            raise

    async def add_rule_to_rule_sets(self, rule_id: str, rule_set_ids: List[str]) -> bool:
        """
        Add a rule to one or more rule sets.

        Args:
            rule_id: The ID of the rule
            rule_set_ids: List of rule set IDs to add the rule to

        Returns:
            True if successful, False otherwise

        Raises:
            Exception: If update fails
        """
        try:
            rule = await self.get_rule(rule_id)
            if not rule:
                logger.warning(f"Rule {rule_id} not found")
                return False

            # Add new rule set IDs (avoid duplicates)
            current_sets = set(rule.rule_set_ids)
            current_sets.update(rule_set_ids)
            rule.rule_set_ids = list(current_sets)

            # Update the rule
            success = await self.update_rule(rule_id, rule_set_ids=list(current_sets))

            if success:
                logger.info(f"Added rule {rule_id} to {len(rule_set_ids)} rule sets")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to add rule {rule_id} to rule sets: {e}")
            raise

    async def remove_rule_from_rule_sets(self, rule_id: str, rule_set_ids: List[str]) -> bool:
        """
        Remove a rule from one or more rule sets.

        Args:
            rule_id: The ID of the rule
            rule_set_ids: List of rule set IDs to remove the rule from

        Returns:
            True if successful, False otherwise

        Raises:
            Exception: If update fails
        """
        try:
            rule = await self.get_rule(rule_id)
            if not rule:
                logger.warning(f"Rule {rule_id} not found")
                return False

            # Remove rule set IDs
            current_sets = set(rule.rule_set_ids)
            current_sets.difference_update(rule_set_ids)
            rule.rule_set_ids = list(current_sets)

            # Update the rule
            success = await self.update_rule(rule_id, rule_set_ids=list(current_sets))

            if success:
                logger.info(f"Removed rule {rule_id} from {len(rule_set_ids)} rule sets")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to remove rule {rule_id} from rule sets: {e}")
            raise
