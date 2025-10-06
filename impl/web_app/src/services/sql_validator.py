"""
SQL Validator

Validates CosmosDB SQL queries for syntax correctness and security.
Prevents SQL injection and ensures queries conform to CosmosDB SQL syntax.
"""

import re
import logging
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)


class SQLValidator:
    """
    Validates CosmosDB SQL queries before execution.

    Checks for:
    - Valid CosmosDB SQL syntax
    - SQL injection attempts
    - Proper string escaping
    - Supported operators and clauses
    """

    # Allowed CosmosDB SQL keywords
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'TOP', 'AND', 'OR', 'NOT',
        'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'ORDER', 'BY',
        'ASC', 'DESC', 'OFFSET', 'LIMIT', 'DISTINCT', 'VALUE',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'AS'
    }

    # Allowed operators
    ALLOWED_OPERATORS = {'=', '!=', '<', '>', '<=', '>=', 'IN', 'NOT IN'}

    # Dangerous patterns (potential injection)
    DANGEROUS_PATTERNS = [
        r';.*--',  # SQL comment injection
        r';\s*DROP',  # DROP table attempts
        r';\s*DELETE',  # DELETE attempts
        r';\s*UPDATE',  # UPDATE attempts
        r';\s*INSERT',  # INSERT attempts
        r'EXEC\s*\(',  # Execute attempts
        r'UNION\s+SELECT',  # UNION injection
        r'/\*.*\*/',  # Block comments
    ]

    def __init__(self, schema_collections: Optional[List[str]] = None):
        """
        Initialize SQL validator.

        Args:
            schema_collections: List of valid collection names from schema
        """
        self.schema_collections = schema_collections or [
            'contracts', 'governing_law_states', 'contractor_parties',
            'contracting_parties', 'contract_types', 'contract_chunks',
            'contract_clauses'
        ]

    def validate(self, sql_query: str) -> Tuple[bool, str]:
        """
        Validate SQL query for safety and correctness.

        Args:
            sql_query: SQL query string to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not sql_query or not sql_query.strip():
            return False, "Empty SQL query"

        # Normalize whitespace
        sql_normalized = ' '.join(sql_query.split())

        # Check 1: Detect dangerous patterns (injection attempts)
        is_safe, safety_msg = self._check_injection_patterns(sql_normalized)
        if not is_safe:
            return False, safety_msg

        # Check 2: Validate basic syntax structure
        is_valid_syntax, syntax_msg = self._check_syntax_structure(sql_normalized)
        if not is_valid_syntax:
            return False, syntax_msg

        # Check 3: Validate collection references
        is_valid_collection, coll_msg = self._check_collection_references(sql_normalized)
        if not is_valid_collection:
            return False, coll_msg

        # Check 4: Validate string escaping
        is_valid_strings, string_msg = self._check_string_escaping(sql_query)
        if not is_valid_strings:
            return False, string_msg

        logger.info(f"SQL validation passed: {sql_normalized[:100]}...")
        return True, "Valid"

    def _check_injection_patterns(self, sql_query: str) -> Tuple[bool, str]:
        """Check for SQL injection patterns."""
        sql_upper = sql_query.upper()

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return False, f"Potential SQL injection detected: pattern '{pattern}'"

        return True, "Safe"

    def _check_syntax_structure(self, sql_query: str) -> Tuple[bool, str]:
        """Validate basic SQL syntax structure."""
        sql_upper = sql_query.upper()

        # Must start with SELECT
        if not sql_upper.strip().startswith('SELECT'):
            return False, "Query must start with SELECT"

        # Must have FROM clause
        if 'FROM' not in sql_upper:
            return False, "Query must include FROM clause"

        # Check for balanced parentheses
        if sql_query.count('(') != sql_query.count(')'):
            return False, "Unbalanced parentheses"

        # Check for balanced quotes
        single_quotes = sql_query.count("'")
        if single_quotes % 2 != 0:
            return False, "Unbalanced single quotes"

        return True, "Valid syntax structure"

    def _check_collection_references(self, sql_query: str) -> Tuple[bool, str]:
        """Validate collection references in FROM clause."""
        # Extract FROM clause
        from_match = re.search(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)

        if not from_match:
            return False, "Could not parse FROM clause"

        collection_alias = from_match.group(1)

        # CosmosDB uses alias 'c' for collection reference
        if collection_alias.lower() not in ['c', 'contracts', 'governing_law_states',
                                             'contractor_parties', 'contracting_parties',
                                             'contract_types', 'contract_chunks', 'contract_clauses']:
            logger.warning(f"Non-standard collection alias: {collection_alias}")

        return True, "Valid collection reference"

    def _check_string_escaping(self, sql_query: str) -> Tuple[bool, str]:
        """Validate string literal escaping."""
        # Find all string literals
        string_literals = re.findall(r"'([^']*)'", sql_query)

        for literal in string_literals:
            # Check for unescaped single quotes within strings
            if "'" in literal and "\\'" not in literal:
                return False, f"Unescaped single quote in string literal: '{literal}'"

            # Check for suspicious escape sequences
            if '\\x' in literal or '\\u' in literal:
                return False, f"Suspicious escape sequence in string literal: '{literal}'"

        return True, "Valid string escaping"

    def sanitize_value(self, value: str) -> str:
        """
        Sanitize a value for safe use in SQL query.

        Args:
            value: Raw value to sanitize

        Returns:
            Sanitized value safe for SQL
        """
        # Escape single quotes
        sanitized = value.replace("'", "''")

        # Remove any null bytes
        sanitized = sanitized.replace('\x00', '')

        return sanitized

    def validate_operator(self, operator: str) -> bool:
        """
        Validate that operator is allowed.

        Args:
            operator: SQL operator to validate

        Returns:
            True if operator is allowed
        """
        return operator.upper() in self.ALLOWED_OPERATORS
