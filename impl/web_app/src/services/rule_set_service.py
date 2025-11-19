"""
Service for managing compliance rule sets.

This service provides CRUD operations for rule sets and manages
the many-to-many relationship between rules and rule sets.

Author: Aleksey Savateyev, Microsoft, 2025
"""

import logging
from datetime import datetime
from typing import List, Optional

from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.models.rule_set_models import (
    RuleSet,
    RuleSetCreate,
    RuleSetUpdate,
    RuleSetListResponse,
    RuleSetWithRuleCount
)


class RuleSetService:
    """Service for managing compliance rule sets"""

    def __init__(self):
        self.container_name = "rule_sets"
        self.cosmos_service: Optional[CosmosNoSQLService] = None

    async def initialize(self):
        """Initialize the Cosmos DB service"""
        self.cosmos_service = CosmosNoSQLService()
        await self.cosmos_service.initialize()
        self.cosmos_service.set_container(self.container_name)

    async def close(self):
        """Close the Cosmos DB connection"""
        if self.cosmos_service:
            await self.cosmos_service.close()

    def _generate_rule_set_id(self, name: str) -> str:
        """Generate a unique rule set ID based on name"""
        # Normalize name: lowercase, replace spaces with underscores
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        # Remove special characters
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")
        # Add timestamp to ensure uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ruleset_{normalized}_{timestamp}"

    async def create_rule_set(self, rule_set_data: RuleSetCreate, created_by: str = "system") -> RuleSet:
        """
        Create a new rule set.

        Args:
            rule_set_data: Rule set creation data
            created_by: Username of the creator

        Returns:
            Created rule set

        Raises:
            Exception: If creation fails
        """
        try:
            # Generate unique ID
            rule_set_id = self._generate_rule_set_id(rule_set_data.name)

            # Get current timestamp
            now = datetime.utcnow().isoformat() + "Z"

            # Build rule set document
            rule_set_doc = {
                "id": rule_set_id,
                "doctype": "rule_set",
                "name": rule_set_data.name,
                "description": rule_set_data.description,
                "suggested_contract_types": rule_set_data.suggested_contract_types or [],
                "rule_ids": rule_set_data.rule_ids or [],
                "is_active": rule_set_data.is_active,
                "created_date": now,
                "modified_date": now,
                "created_by": created_by
            }

            # Insert into Cosmos DB
            created_doc = await self.cosmos_service.create_item(rule_set_doc)

            logging.info(f"Created rule set: {rule_set_id}")
            return RuleSet(**created_doc)

        except Exception as e:
            logging.error(f"Error creating rule set: {str(e)}")
            raise

    async def get_rule_set(self, rule_set_id: str) -> Optional[RuleSet]:
        """
        Get a rule set by ID.

        Args:
            rule_set_id: The rule set ID

        Returns:
            Rule set if found, None otherwise
        """
        try:
            doc = await self.cosmos_service.point_read(rule_set_id, rule_set_id)
            if doc:
                return RuleSet(**doc)
            return None
        except Exception as e:
            logging.error(f"Error retrieving rule set {rule_set_id}: {str(e)}")
            return None

    async def list_rule_sets(self, include_inactive: bool = False) -> RuleSetListResponse:
        """
        List all rule sets.

        Args:
            include_inactive: Whether to include inactive rule sets

        Returns:
            List of rule sets with total count
        """
        try:
            # Build query
            if include_inactive:
                query = "SELECT * FROM c WHERE c.doctype = 'rule_set'"
            else:
                query = "SELECT * FROM c WHERE c.doctype = 'rule_set' AND c.is_active = true"

            # Execute query
            results = await self.cosmos_service.query_items(query, cross_partition=True)

            rule_sets = [RuleSet(**doc) for doc in results]

            return RuleSetListResponse(
                rule_sets=rule_sets,
                total=len(rule_sets)
            )

        except Exception as e:
            logging.error(f"Error listing rule sets: {str(e)}")
            return RuleSetListResponse(rule_sets=[], total=0)

    async def update_rule_set(self, rule_set_id: str, updates: RuleSetUpdate) -> Optional[RuleSet]:
        """
        Update a rule set.

        Args:
            rule_set_id: The rule set ID
            updates: Fields to update

        Returns:
            Updated rule set if successful, None otherwise
        """
        try:
            # Get existing rule set
            existing = await self.get_rule_set(rule_set_id)
            if not existing:
                logging.warning(f"Rule set {rule_set_id} not found")
                return None

            # Build update document
            update_doc = existing.dict()

            # Apply updates (only non-None fields)
            update_dict = updates.dict(exclude_none=True)
            for key, value in update_dict.items():
                update_doc[key] = value

            # Update modified date
            update_doc["modified_date"] = datetime.utcnow().isoformat() + "Z"

            # Update in Cosmos DB
            updated_doc = await self.cosmos_service.upsert_item(update_doc)

            logging.info(f"Updated rule set: {rule_set_id}")
            return RuleSet(**updated_doc)

        except Exception as e:
            logging.error(f"Error updating rule set {rule_set_id}: {str(e)}")
            return None

    async def delete_rule_set(self, rule_set_id: str) -> bool:
        """
        Delete a rule set.

        Args:
            rule_set_id: The rule set ID

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.cosmos_service.delete_item(rule_set_id, rule_set_id)
            if result:
                logging.info(f"Deleted rule set: {rule_set_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting rule set {rule_set_id}: {str(e)}")
            return False

    async def add_rules_to_set(self, rule_set_id: str, rule_ids: List[str]) -> Optional[RuleSet]:
        """
        Add rules to a rule set.

        Args:
            rule_set_id: The rule set ID
            rule_ids: List of rule IDs to add

        Returns:
            Updated rule set if successful, None otherwise
        """
        try:
            # Get existing rule set
            existing = await self.get_rule_set(rule_set_id)
            if not existing:
                logging.warning(f"Rule set {rule_set_id} not found")
                return None

            # Add new rule IDs (avoid duplicates)
            current_rule_ids = set(existing.rule_ids)
            current_rule_ids.update(rule_ids)

            # Update the rule set
            update_doc = existing.dict()
            update_doc["rule_ids"] = list(current_rule_ids)
            update_doc["modified_date"] = datetime.utcnow().isoformat() + "Z"

            # Update in Cosmos DB
            updated_doc = await self.cosmos_service.upsert_item(update_doc)

            logging.info(f"Added {len(rule_ids)} rules to rule set {rule_set_id}")
            return RuleSet(**updated_doc)

        except Exception as e:
            logging.error(f"Error adding rules to rule set {rule_set_id}: {str(e)}")
            return None

    async def remove_rules_from_set(self, rule_set_id: str, rule_ids: List[str]) -> Optional[RuleSet]:
        """
        Remove rules from a rule set.

        Args:
            rule_set_id: The rule set ID
            rule_ids: List of rule IDs to remove

        Returns:
            Updated rule set if successful, None otherwise
        """
        try:
            # Get existing rule set
            existing = await self.get_rule_set(rule_set_id)
            if not existing:
                logging.warning(f"Rule set {rule_set_id} not found")
                return None

            # Remove rule IDs
            current_rule_ids = set(existing.rule_ids)
            current_rule_ids.difference_update(rule_ids)

            # Update the rule set
            update_doc = existing.dict()
            update_doc["rule_ids"] = list(current_rule_ids)
            update_doc["modified_date"] = datetime.utcnow().isoformat() + "Z"

            # Update in Cosmos DB
            updated_doc = await self.cosmos_service.upsert_item(update_doc)

            logging.info(f"Removed {len(rule_ids)} rules from rule set {rule_set_id}")
            return RuleSet(**updated_doc)

        except Exception as e:
            logging.error(f"Error removing rules from rule set {rule_set_id}: {str(e)}")
            return None

    async def get_rules_in_set(self, rule_set_id: str) -> List[str]:
        """
        Get all rule IDs in a rule set.

        Args:
            rule_set_id: The rule set ID

        Returns:
            List of rule IDs
        """
        try:
            rule_set = await self.get_rule_set(rule_set_id)
            if rule_set:
                return rule_set.rule_ids
            return []
        except Exception as e:
            logging.error(f"Error getting rules in set {rule_set_id}: {str(e)}")
            return []

    async def clone_rule_set(
        self,
        rule_set_id: str,
        new_name: str,
        clone_rules: bool = True,
        created_by: str = "system"
    ) -> Optional[RuleSet]:
        """
        Clone an existing rule set.

        Args:
            rule_set_id: ID of rule set to clone
            new_name: Name for the new rule set
            clone_rules: Whether to copy the rule IDs
            created_by: Username of the creator

        Returns:
            Cloned rule set if successful, None otherwise
        """
        try:
            # Get existing rule set
            existing = await self.get_rule_set(rule_set_id)
            if not existing:
                logging.warning(f"Rule set {rule_set_id} not found for cloning")
                return None

            # Create new rule set data
            clone_data = RuleSetCreate(
                name=new_name,
                description=f"Cloned from: {existing.name}. {existing.description or ''}".strip(),
                suggested_contract_types=existing.suggested_contract_types,
                is_active=existing.is_active,
                rule_ids=existing.rule_ids if clone_rules else []
            )

            # Create the cloned rule set
            cloned = await self.create_rule_set(clone_data, created_by)

            logging.info(f"Cloned rule set {rule_set_id} to {cloned.id}")
            return cloned

        except Exception as e:
            logging.error(f"Error cloning rule set {rule_set_id}: {str(e)}")
            return None

    async def get_rule_sets_with_counts(self, include_inactive: bool = False) -> List[RuleSetWithRuleCount]:
        """
        Get all rule sets with rule counts.

        Args:
            include_inactive: Whether to include inactive rule sets

        Returns:
            List of rule sets with rule counts
        """
        try:
            response = await self.list_rule_sets(include_inactive)

            rule_sets_with_counts = []
            for rule_set in response.rule_sets:
                rule_set_with_count = RuleSetWithRuleCount(
                    **rule_set.dict(),
                    rule_count=len(rule_set.rule_ids)
                )
                rule_sets_with_counts.append(rule_set_with_count)

            return rule_sets_with_counts

        except Exception as e:
            logging.error(f"Error getting rule sets with counts: {str(e)}")
            return []
