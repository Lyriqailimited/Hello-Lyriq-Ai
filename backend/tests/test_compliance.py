"""Unit tests for the compliance service."""

from services.compliance_service import check_compliance


def test_pass_valid_call():
    record = {
        "call_timestamp": "2026-03-12T14:30:00",
        "days_past_due": 45,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
        "dealer_id": "DLR-001",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "PASS"
    assert len(result["compliance_violations"]) == 0


def test_fail_outside_calling_hours_early():
    record = {
        "call_timestamp": "2026-03-12T03:00:00",
        "days_past_due": 10,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "TCPA_HOURS" in result["compliance_violations"]


def test_fail_outside_calling_hours_late():
    record = {
        "call_timestamp": "2026-03-12T21:30:00",
        "days_past_due": 10,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "TCPA_HOURS" in result["compliance_violations"]


def test_pass_boundary_8am():
    record = {
        "call_timestamp": "2026-03-12T08:00:00",
        "days_past_due": 0,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "PASS"
    assert len(result["compliance_violations"]) == 0


def test_fail_boundary_9pm():
    """Hour 21 is outside the window (8 <= hour < 21)."""
    record = {
        "call_timestamp": "2026-03-12T21:00:00",
        "days_past_due": 0,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "TCPA_HOURS" in result["compliance_violations"]


def test_pass_boundary_just_before_9pm():
    record = {
        "call_timestamp": "2026-03-12T20:59:00",
        "days_past_due": 0,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "PASS"
    assert len(result["compliance_violations"]) == 0


def test_fail_negative_days_past_due():
    record = {
        "call_timestamp": "2026-03-12T10:00:00",
        "days_past_due": -5,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "NEGATIVE_DAYS" in result["compliance_violations"]


def test_fail_days_past_due_at_180():
    """Accounts at 180+ days are out of valid collection range."""
    record = {
        "call_timestamp": "2026-03-12T10:00:00",
        "days_past_due": 180,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "INVALID_ACCOUNT_AGE" in result["compliance_violations"]


def test_fail_days_past_due_over_180():
    record = {
        "call_timestamp": "2026-03-12T10:00:00",
        "days_past_due": 250,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "INVALID_ACCOUNT_AGE" in result["compliance_violations"]


def test_pass_days_past_due_just_under_180():
    record = {
        "call_timestamp": "2026-03-12T10:00:00",
        "days_past_due": 179,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "TCPA_OK",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "PASS"
    assert len(result["compliance_violations"]) == 0


def test_fail_missing_tcpa_ok():
    record = {
        "call_timestamp": "2026-03-12T10:00:00",
        "days_past_due": 30,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
        "compliance_flags": "",
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "MISSING_TCPA_CONSENT" in result["compliance_violations"]


def test_fail_no_compliance_flags_key():
    record = {
        "call_timestamp": "2026-03-12T10:00:00",
        "days_past_due": 30,
        "debt_balance": 1000.0,
        "call_duration_minutes": 5.0,
    }
    result = check_compliance(record)
    assert result["compliance_status"] == "FAIL"
    assert "MISSING_TCPA_CONSENT" in result["compliance_violations"]
