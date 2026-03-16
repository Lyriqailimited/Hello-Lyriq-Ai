"""
SQL Safety Layer - Ensures only read-only queries are executed.
Prevents any destructive operations like INSERT, UPDATE, DELETE, DROP, etc.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class SQLSafetyError(Exception):
    """Raised when a potentially dangerous SQL operation is detected."""
    pass


class SQLValidator:
    """Validates SQL queries to ensure they are read-only and safe to execute."""

    # Dangerous SQL keywords that should never be allowed
    FORBIDDEN_KEYWORDS = [
        r'\bINSERT\b',
        r'\bUPDATE\b',
        r'\bDELETE\b',
        r'\bDROP\b',
        r'\bTRUNCATE\b',
        r'\bALTER\b',
        r'\bCREATE\b',
        r'\bREPLACE\b',
        r'\bEXEC\b',
        r'\bEXECUTE\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
        r'\bCOMMIT\b',
        r'\bROLLBACK\b',
        r'\bPRAGMA\b',
        r'\bATTACH\b',
        r'\bDETACH\b',
    ]

    @classmethod
    def is_safe_query(cls, sql: str) -> Tuple[bool, str]:
        """
        Check if a SQL query is safe to execute.

        Args:
            sql: The SQL query string to validate

        Returns:
            Tuple of (is_safe: bool, reason: str)
        """
        if not sql or not sql.strip():
            return False, "Empty query"

        # Remove SQL comments first (before normalization)
        sql_no_comments = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql_no_comments = re.sub(r'/\*.*?\*/', '', sql_no_comments, flags=re.DOTALL)
        sql_no_comments = sql_no_comments.strip()

        # Normalize the SQL for checking (uppercase, remove extra spaces)
        normalized_sql = ' '.join(sql_no_comments.upper().split())

        # Check for forbidden keywords
        for forbidden in cls.FORBIDDEN_KEYWORDS:
            if re.search(forbidden, normalized_sql, re.IGNORECASE):
                keyword = forbidden.replace(r'\b', '').replace('\\', '')
                return False, f"Forbidden keyword detected: {keyword}"

        # Ensure query starts with SELECT (after removing comments and whitespace)
        if not normalized_sql.startswith('SELECT'):
            return False, "Query must be a SELECT statement"

        # Additional safety: check for semicolons (multiple statements)
        if sql.count(';') > 1:
            return False, "Multiple statements not allowed"

        return True, "Query is safe"

    @classmethod
    def validate_and_sanitize(cls, sql: str) -> str:
        """
        Validate and sanitize a SQL query.

        Args:
            sql: The SQL query to validate

        Returns:
            The sanitized SQL query

        Raises:
            SQLSafetyError: If the query is not safe
        """
        is_safe, reason = cls.is_safe_query(sql)

        if not is_safe:
            logger.warning(f"Unsafe SQL query blocked: {reason}")
            raise SQLSafetyError(f"Query rejected: {reason}")

        # Remove trailing semicolon if present (for consistency)
        sql = sql.strip()
        if sql.endswith(';'):
            sql = sql[:-1]

        logger.info(f"SQL query validated successfully")
        return sql


def validate_sql(sql: str) -> str:
    """
    Convenience function to validate SQL queries.

    Args:
        sql: The SQL query to validate

    Returns:
        The validated SQL query

    Raises:
        SQLSafetyError: If the query is not safe
    """
    return SQLValidator.validate_and_sanitize(sql)
