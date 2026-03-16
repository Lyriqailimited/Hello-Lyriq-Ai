"""
Tests for the Analytics Chatbot functionality.
"""

import pytest
from services.sql_safety import SQLValidator, SQLSafetyError, validate_sql


class TestSQLValidator:
    """Test the SQL safety validator."""

    def test_valid_select_query(self):
        """Test that valid SELECT queries pass validation."""
        queries = [
            "SELECT * FROM call_records",
            "SELECT AVG(call_duration_minutes) FROM call_records WHERE call_timestamp >= date('now', '-30 days')",
            "SELECT COUNT(*) FROM call_records WHERE compliance_status = 'FAIL'",
            "  SELECT id, dealer_id FROM call_records LIMIT 10  ",  # With whitespace
        ]

        for query in queries:
            is_safe, reason = SQLValidator.is_safe_query(query)
            assert is_safe, f"Query should be safe: {query}. Reason: {reason}"

    def test_dangerous_queries_rejected(self):
        """Test that dangerous queries are rejected."""
        dangerous_queries = [
            "DELETE FROM call_records",
            "UPDATE call_records SET dealer_id = 'X'",
            "INSERT INTO call_records (dealer_id) VALUES ('test')",
            "DROP TABLE call_records",
            "TRUNCATE TABLE call_records",
            "ALTER TABLE call_records ADD COLUMN test VARCHAR(10)",
            "CREATE TABLE test (id INT)",
            "EXEC sp_executesql",
            "GRANT ALL ON call_records TO user",
        ]

        for query in dangerous_queries:
            is_safe, reason = SQLValidator.is_safe_query(query)
            assert not is_safe, f"Query should be rejected: {query}"
            assert "forbidden" in reason.lower() or "must be a select" in reason.lower()

    def test_multiple_statements_rejected(self):
        """Test that multiple SQL statements are rejected."""
        # Test with multiple SELECT statements (no forbidden keywords)
        query = "SELECT * FROM call_records; SELECT * FROM call_records;"
        is_safe, reason = SQLValidator.is_safe_query(query)
        assert not is_safe
        assert "multiple statements" in reason.lower()

        # Test with forbidden keyword in second statement (will be caught by keyword check)
        query2 = "SELECT * FROM call_records; DROP TABLE call_records;"
        is_safe2, reason2 = SQLValidator.is_safe_query(query2)
        assert not is_safe2
        # Either reason is acceptable (forbidden keyword or multiple statements)

    def test_empty_query_rejected(self):
        """Test that empty queries are rejected."""
        is_safe, reason = SQLValidator.is_safe_query("")
        assert not is_safe
        assert "empty" in reason.lower()

        is_safe, reason = SQLValidator.is_safe_query("   ")
        assert not is_safe
        assert "empty" in reason.lower()

    def test_validate_and_sanitize(self):
        """Test the validate_and_sanitize method."""
        # Valid query should be returned (without trailing semicolon)
        query = "SELECT * FROM call_records;"
        result = SQLValidator.validate_and_sanitize(query)
        assert result == "SELECT * FROM call_records"

        # Invalid query should raise exception
        with pytest.raises(SQLSafetyError):
            SQLValidator.validate_and_sanitize("DELETE FROM call_records")

    def test_convenience_function(self):
        """Test the convenience validate_sql function."""
        # Should work for valid queries
        result = validate_sql("SELECT * FROM call_records")
        assert "SELECT" in result

        # Should raise for invalid queries
        with pytest.raises(SQLSafetyError):
            validate_sql("DROP TABLE call_records")

    def test_sql_with_comments(self):
        """Test that SQL comments are handled properly."""
        query_with_comment = """
        -- This is a comment
        SELECT * FROM call_records
        WHERE dealer_id = 'D-123'
        """
        is_safe, reason = SQLValidator.is_safe_query(query_with_comment)
        assert is_safe, f"Query with comment should be safe. Reason: {reason}"

        query_with_block_comment = """
        /* Multi-line
           comment */
        SELECT AVG(call_duration_minutes) FROM call_records
        """
        is_safe, reason = SQLValidator.is_safe_query(query_with_block_comment)
        assert is_safe, f"Query with block comment should be safe. Reason: {reason}"

    def test_case_insensitive_detection(self):
        """Test that keyword detection is case-insensitive."""
        queries = [
            "delete from call_records",
            "DeLeTe FrOm call_records",
            "UPDATE call_records SET x=1",
            "DrOp TaBlE call_records",
        ]

        for query in queries:
            is_safe, reason = SQLValidator.is_safe_query(query)
            assert not is_safe, f"Query should be rejected regardless of case: {query}"
