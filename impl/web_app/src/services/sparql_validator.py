"""
SPARQL Validator

Validates SPARQL queries for syntax correctness and security.
Ensures queries conform to SPARQL 1.1 syntax and use correct ontology.
"""

import re
import logging
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)


class SPARQLValidator:
    """
    Validates SPARQL queries before execution.

    Checks for:
    - Valid SPARQL 1.1 syntax
    - Proper PREFIX declarations
    - Correct ontology namespace usage
    - SPARQL injection prevention
    """

    # Required prefixes for contract ontology
    REQUIRED_PREFIXES = {
        'caig': 'http://cosmosdb.com/caig#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
    }

    # Allowed SPARQL keywords
    ALLOWED_KEYWORDS = {
        'SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE', 'WHERE',
        'OPTIONAL', 'FILTER', 'UNION', 'DISTINCT', 'REDUCED',
        'ORDER', 'BY', 'LIMIT', 'OFFSET', 'FROM', 'GRAPH',
        'PREFIX', 'BASE', 'BOUND', 'REGEX', 'STR', 'LANG'
    }

    # Dangerous patterns (potential injection)
    DANGEROUS_PATTERNS = [
        r';.*--',  # Comment injection
        r'DROP\s+GRAPH',  # DROP attempts
        r'CLEAR\s+GRAPH',  # CLEAR attempts
        r'INSERT\s+DATA',  # INSERT attempts
        r'DELETE\s+DATA',  # DELETE attempts
        r'LOAD\s+<',  # LOAD attempts
    ]

    def __init__(self):
        """Initialize SPARQL validator."""
        pass

    def validate(self, sparql_query: str) -> Tuple[bool, str]:
        """
        Validate SPARQL query for safety and correctness.

        Args:
            sparql_query: SPARQL query string to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not sparql_query or not sparql_query.strip():
            return False, "Empty SPARQL query"

        # Normalize whitespace
        sparql_normalized = ' '.join(sparql_query.split())

        # Check 1: Detect dangerous patterns (injection attempts)
        is_safe, safety_msg = self._check_injection_patterns(sparql_normalized)
        if not is_safe:
            return False, safety_msg

        # Check 2: Validate PREFIX declarations
        is_valid_prefix, prefix_msg = self._check_prefixes(sparql_query)
        if not is_valid_prefix:
            return False, prefix_msg

        # Check 3: Validate basic SPARQL syntax
        is_valid_syntax, syntax_msg = self._check_syntax_structure(sparql_normalized)
        if not is_valid_syntax:
            return False, syntax_msg

        # Check 4: Validate ontology namespace usage
        is_valid_namespace, ns_msg = self._check_namespace_usage(sparql_query)
        if not is_valid_namespace:
            return False, ns_msg

        # Check 5: Validate triple patterns
        is_valid_triples, triple_msg = self._check_triple_patterns(sparql_query)
        if not is_valid_triples:
            return False, triple_msg

        logger.info(f"SPARQL validation passed: {sparql_normalized[:100]}...")
        return True, "Valid"

    def _check_injection_patterns(self, sparql_query: str) -> Tuple[bool, str]:
        """Check for SPARQL injection patterns."""
        sparql_upper = sparql_query.upper()

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sparql_upper, re.IGNORECASE):
                return False, f"Potential SPARQL injection detected: pattern '{pattern}'"

        # Check for update operations (we only allow SELECT queries)
        if any(keyword in sparql_upper for keyword in ['INSERT', 'DELETE', 'MODIFY', 'DROP', 'CLEAR', 'LOAD', 'CREATE']):
            return False, "Update operations not allowed (read-only queries only)"

        return True, "Safe"

    def _check_prefixes(self, sparql_query: str) -> Tuple[bool, str]:
        """Validate PREFIX declarations."""
        # Extract PREFIX declarations
        prefix_lines = re.findall(r'PREFIX\s+(\w+):\s*<([^>]+)>', sparql_query, re.IGNORECASE)

        if not prefix_lines:
            return False, "Missing PREFIX declarations (at least 'caig:' required)"

        prefixes = {name: uri for name, uri in prefix_lines}

        # Check for required caig prefix
        if 'caig' not in prefixes:
            return False, "Missing required PREFIX declaration: caig: <http://cosmosdb.com/caig#>"

        # Validate caig prefix URI
        if prefixes['caig'] != self.REQUIRED_PREFIXES['caig']:
            return False, f"Incorrect caig prefix URI: expected '{self.REQUIRED_PREFIXES['caig']}', got '{prefixes['caig']}'"

        return True, "Valid PREFIX declarations"

    def _check_syntax_structure(self, sparql_query: str) -> Tuple[bool, str]:
        """Validate basic SPARQL syntax structure."""
        sparql_upper = sparql_query.upper()

        # Must have SELECT, CONSTRUCT, ASK, or DESCRIBE
        if not any(keyword in sparql_upper for keyword in ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']):
            return False, "Query must include SELECT, CONSTRUCT, ASK, or DESCRIBE"

        # Must have WHERE clause (except for ASK/DESCRIBE without WHERE)
        if 'SELECT' in sparql_upper and 'WHERE' not in sparql_upper:
            return False, "SELECT query must include WHERE clause"

        # Check for balanced braces
        if sparql_query.count('{') != sparql_query.count('}'):
            return False, "Unbalanced braces in WHERE clause"

        # Check for balanced parentheses
        if sparql_query.count('(') != sparql_query.count(')'):
            return False, "Unbalanced parentheses"

        return True, "Valid SPARQL syntax structure"

    def _check_namespace_usage(self, sparql_query: str) -> Tuple[bool, str]:
        """Validate ontology namespace usage."""
        # Find all prefixed terms (e.g., caig:Contract, caig:is_governed_by)
        prefixed_terms = re.findall(r'(\w+):(\w+)', sparql_query)

        if not prefixed_terms:
            return False, "No ontology terms found in query"

        for prefix, term in prefixed_terms:
            # Skip PREFIX declarations themselves
            if 'PREFIX' in sparql_query[max(0, sparql_query.find(f'{prefix}:{term}') - 10):sparql_query.find(f'{prefix}:{term}')].upper():
                continue

            # Validate prefix is declared
            if prefix not in ['caig', 'rdf', 'rdfs', 'xsd', 'owl']:
                logger.warning(f"Unknown prefix used: {prefix}")

        return True, "Valid namespace usage"

    def _check_triple_patterns(self, sparql_query: str) -> Tuple[bool, str]:
        """Validate triple patterns in WHERE clause."""
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s*\{([^}]+)\}', sparql_query, re.IGNORECASE | re.DOTALL)

        if not where_match:
            # WHERE clause is optional for some query types
            return True, "No WHERE clause (acceptable for some queries)"

        where_clause = where_match.group(1)

        # Check for at least one triple pattern (subject predicate object)
        # Triple pattern: ?var or URI, followed by predicate, followed by ?var or URI or literal
        triple_pattern = r'(\?[\w]+|<[^>]+>|\w+:\w+)\s+(\?[\w]+|<[^>]+>|\w+:\w+)\s+(\?[\w]+|<[^>]+>|"[^"]*"|\w+:\w+)'

        triples = re.findall(triple_pattern, where_clause)

        if not triples:
            return False, "No valid triple patterns found in WHERE clause"

        # Validate that subject-predicate-object makes sense
        for subj, pred, obj in triples:
            # Subject must be variable or URI (not literal)
            if subj.startswith('"'):
                return False, f"Invalid triple: subject cannot be literal: {subj}"

            # Predicate must be URI or prefixed term (not variable in basic queries)
            if pred.startswith('?'):
                logger.warning(f"Variable predicate used: {pred} (advanced usage)")

        return True, "Valid triple patterns"

    def sanitize_literal(self, literal: str) -> str:
        """
        Sanitize a literal value for safe use in SPARQL query.

        Args:
            literal: Raw literal value to sanitize

        Returns:
            Sanitized literal safe for SPARQL
        """
        # Escape double quotes
        sanitized = literal.replace('"', '\\"')

        # Escape backslashes
        sanitized = sanitized.replace('\\', '\\\\')

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        return sanitized

    def validate_variable_name(self, var_name: str) -> bool:
        """
        Validate SPARQL variable name.

        Args:
            var_name: Variable name to validate (without ?)

        Returns:
            True if variable name is valid
        """
        # Variable names must start with letter or underscore
        # Can contain letters, digits, underscores
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, var_name))
