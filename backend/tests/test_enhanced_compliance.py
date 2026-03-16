"""
Comprehensive tests for the enhanced compliance service.

Tests all FDCPA and TCPA rules including:
  - Calling hours (8 AM - 9 PM)
  - Sunday restrictions (no calls before 1 PM)
  - Account age validation
  - Statute of limitations
  - TCPA consent verification
  - Call duration limits
  - Debt balance validation
  - Contact frequency (3 calls per 7 days)
"""

import pytest
from datetime import datetime, timedelta
from services.compliance_service import check_compliance, get_violation_description
from database.models import CallRecord
from database.database import Base


class TestComplianceRules:
    """Test individual compliance rules."""

    def test_tcpa_hours_pass(self):
        """Test TCPA calling hours - valid hours (8 AM - 9 PM)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 30),  # 2:30 PM - valid
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "PASS"
        assert len(result["compliance_violations"]) == 0

    def test_tcpa_hours_fail_early(self):
        """Test TCPA calling hours - too early (before 8 AM)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 7, 30),  # 7:30 AM - too early
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "TCPA_HOURS" in result["compliance_violations"]

    def test_tcpa_hours_fail_late(self):
        """Test TCPA calling hours - too late (after 9 PM)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 21, 30),  # 9:30 PM - too late
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "TCPA_HOURS" in result["compliance_violations"]

    def test_fdcpa_sunday_restriction_pass(self):
        """Test FDCPA Sunday restriction - call after 1 PM is OK."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 17, 13, 0),  # Sunday 1 PM - OK
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "PASS"
        assert "FDCPA_SUNDAY" not in result["compliance_violations"]

    def test_fdcpa_sunday_restriction_fail(self):
        """Test FDCPA Sunday restriction - call before 1 PM fails."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 17, 12, 0),  # Sunday 12 PM - too early
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "FDCPA_SUNDAY" in result["compliance_violations"]

    def test_account_age_valid(self):
        """Test account age validation - valid range."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 90,  # Valid: 0-179
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "PASS"
        assert "INVALID_ACCOUNT_AGE" not in result["compliance_violations"]

    def test_account_age_invalid_too_old(self):
        """Test account age validation - too old (>= 180 days)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 200,  # Invalid: >= 180
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "INVALID_ACCOUNT_AGE" in result["compliance_violations"]

    def test_account_age_negative(self):
        """Test account age validation - negative days."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": -10,  # Invalid: negative
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "NEGATIVE_DAYS" in result["compliance_violations"]

    def test_statute_of_limitations_pass(self):
        """Test statute of limitations - debt under 7 years."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 2000,  # ~5.5 years - OK
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        # Will fail on INVALID_ACCOUNT_AGE but not STATUTE_EXPIRED
        assert "STATUTE_EXPIRED" not in result["compliance_violations"]

    def test_statute_of_limitations_fail(self):
        """Test statute of limitations - debt over 7 years."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 2600,  # > 7 years
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "STATUTE_EXPIRED" in result["compliance_violations"]

    def test_tcpa_consent_present(self):
        """Test TCPA consent flag - present."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK,OTHER_FLAG",
        }
        result = check_compliance(record)
        assert "MISSING_TCPA_CONSENT" not in result["compliance_violations"]

    def test_tcpa_consent_missing(self):
        """Test TCPA consent flag - missing."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "OTHER_FLAG",  # No TCPA_OK
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "MISSING_TCPA_CONSENT" in result["compliance_violations"]

    def test_call_duration_valid(self):
        """Test call duration - valid range (0.5 - 60 min)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,  # Valid
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert "CALL_TOO_SHORT" not in result["compliance_violations"]
        assert "CALL_TOO_LONG" not in result["compliance_violations"]

    def test_call_duration_too_short(self):
        """Test call duration - too short (< 30 seconds)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 0.3,  # 18 seconds - too short
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "CALL_TOO_SHORT" in result["compliance_violations"]

    def test_call_duration_too_long(self):
        """Test call duration - too long (> 60 min)."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 75.0,  # Too long
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "CALL_TOO_LONG" in result["compliance_violations"]

    def test_debt_balance_positive(self):
        """Test debt balance - positive value is valid."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 1000.0,  # Valid
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert "INVALID_BALANCE" not in result["compliance_violations"]

    def test_debt_balance_zero(self):
        """Test debt balance - zero is invalid."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": 0.0,  # Invalid
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "INVALID_BALANCE" in result["compliance_violations"]

    def test_debt_balance_negative(self):
        """Test debt balance - negative is invalid."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 15, 14, 0),
            "days_past_due": 30,
            "debt_balance": -100.0,  # Invalid
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        assert "INVALID_BALANCE" in result["compliance_violations"]


class TestContactFrequency:
    """Test contact frequency limits (3 calls per 7 days)."""

    def test_contact_frequency_within_limit(self, db_session):
        """Test contact frequency - within limit (< 3 calls in 7 days)."""
        dealer_id = "DLR-FREQ-001"
        now = datetime.now()

        # Create 2 existing calls in the past 7 days
        for i in range(2):
            call = CallRecord(
                dealer_id=dealer_id,
                call_timestamp=now - timedelta(days=i + 1),
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.5,
            )
            db_session.add(call)
        db_session.commit()

        # New call (would be 3rd - within limit)
        record = {
            "dealer_id": dealer_id,
            "call_timestamp": now,
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record, db_session)
        assert "EXCESSIVE_CONTACT" not in result["compliance_violations"]

    def test_contact_frequency_exceeds_limit(self, db_session):
        """Test contact frequency - exceeds limit (>= 3 calls in 7 days)."""
        dealer_id = "DLR-FREQ-002"
        now = datetime.now()

        # Create 3 existing calls in the past 7 days
        for i in range(3):
            call = CallRecord(
                dealer_id=dealer_id,
                call_timestamp=now - timedelta(days=i + 1),
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.5,
            )
            db_session.add(call)
        db_session.commit()

        # New call (would be 4th - exceeds limit)
        record = {
            "dealer_id": dealer_id,
            "call_timestamp": now,
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record, db_session)
        assert result["compliance_status"] == "FAIL"
        assert "EXCESSIVE_CONTACT" in result["compliance_violations"]

    def test_contact_frequency_old_calls_excluded(self, db_session):
        """Test contact frequency - calls older than 7 days are excluded."""
        dealer_id = "DLR-FREQ-003"
        # Use a fixed time during valid hours (2 PM)
        now = datetime(2024, 3, 15, 14, 0, 0)

        # Create 5 calls, ALL older than 7 days (8, 9, 10, 11, 12 days ago)
        for i in range(5):
            call = CallRecord(
                dealer_id=dealer_id,
                call_timestamp=now - timedelta(days=i + 8),  # 8, 9, 10, 11, 12 days ago
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.5,
            )
            db_session.add(call)
        db_session.commit()

        # New call - should pass because 0 calls in past 7 days (all old calls excluded)
        record = {
            "dealer_id": dealer_id,
            "call_timestamp": now,
            "days_past_due": 30,
            "debt_balance": 1000.0,
            "call_duration_minutes": 5.0,
            "compliance_flags": "TCPA_OK",
        }
        result = check_compliance(record, db_session)
        assert "EXCESSIVE_CONTACT" not in result["compliance_violations"]


class TestMultipleViolations:
    """Test scenarios with multiple compliance violations."""

    def test_multiple_violations(self):
        """Test record with multiple violations."""
        record = {
            "dealer_id": "DLR-001",
            "call_timestamp": datetime(2024, 3, 17, 7, 0),  # Sunday 7 AM - 2 violations
            "days_past_due": -10,  # Negative
            "debt_balance": 0.0,  # Zero
            "call_duration_minutes": 0.2,  # Too short
            "compliance_flags": "OTHER",  # No TCPA_OK
        }
        result = check_compliance(record)
        assert result["compliance_status"] == "FAIL"
        violations = result["compliance_violations"]
        assert "TCPA_HOURS" in violations
        assert "FDCPA_SUNDAY" in violations
        assert "NEGATIVE_DAYS" in violations
        assert "INVALID_BALANCE" in violations
        assert "CALL_TOO_SHORT" in violations
        assert "MISSING_TCPA_CONSENT" in violations
        assert len(violations) >= 6


class TestViolationDescriptions:
    """Test violation description helper."""

    def test_get_violation_descriptions(self):
        """Test that all violation codes have descriptions."""
        from services.compliance_service import VIOLATION_CODES

        for code in VIOLATION_CODES.keys():
            desc = get_violation_description(code)
            assert desc is not None
            assert len(desc) > 0
            assert desc != "Unknown violation"

    def test_unknown_violation_code(self):
        """Test handling of unknown violation code."""
        desc = get_violation_description("UNKNOWN_CODE")
        assert desc == "Unknown violation"
