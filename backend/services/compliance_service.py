"""
Compliance service – checks whether a call record satisfies regulatory rules.

Comprehensive FDCPA & TCPA Rules:
  1. TCPA calling-hours: 8 AM – 9 PM in debtor's local time
  2. Valid account age: days_past_due must be [0, 180)
  3. TCPA consent verification: TCPA_OK flag required
  4. FDCPA prohibited times: No calls on Sundays before 1 PM
  5. Contact frequency: Max 3 calls per debtor per 7 days
  6. Call duration limits: Min 30 seconds (no robo-dials), Max 60 minutes
  7. Account balance validation: Must be positive
  8. Statute of limitations: Debt must be < 7 years old (based on account age)

Returns:
  {
    "compliance_status": "PASS" | "FAIL",
    "compliance_violations": [list of violation codes],
    "compliance_details": "Human-readable explanation"
  }
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Violation codes for tracking
VIOLATION_CODES = {
    "TCPA_HOURS": "Call outside TCPA permitted hours (8 AM - 9 PM)",
    "FDCPA_SUNDAY": "Call on Sunday before 1 PM violates FDCPA",
    "INVALID_ACCOUNT_AGE": "Days past due outside valid range [0, 180)",
    "MISSING_TCPA_CONSENT": "TCPA_OK flag not present",
    "EXCESSIVE_CONTACT": "Exceeds maximum 3 calls per 7 days",
    "CALL_TOO_SHORT": "Call duration < 30 seconds (potential robo-dial)",
    "CALL_TOO_LONG": "Call duration > 60 minutes (unreasonable)",
    "INVALID_BALANCE": "Debt balance must be positive",
    "STATUTE_EXPIRED": "Debt exceeds statute of limitations (7 years)",
    "NEGATIVE_DAYS": "Days past due cannot be negative",
}


def check_compliance(record: dict[str, Any], db: Session = None) -> dict[str, Any]:
    """
    Run all compliance rules and return comprehensive status.

    Args:
        record: Call record dictionary with metadata
        db: Optional database session for contact frequency checks

    Returns:
        Dictionary with compliance_status, violations list, and details
    """
    violations = []

    timestamp = record.get("call_timestamp")
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    # Rule 1 – TCPA calling-hours window (8 AM – 9 PM)
    if timestamp and not (8 <= timestamp.hour < 21):
        violations.append("TCPA_HOURS")
        logger.warning(
            "TCPA violation: call at %02d:00 outside 8-21 window (dealer=%s)",
            timestamp.hour,
            record.get("dealer_id", "unknown")
        )

    # Rule 2 – FDCPA Sunday restriction (no calls before 1 PM on Sunday)
    if timestamp and timestamp.weekday() == 6 and timestamp.hour < 13:
        violations.append("FDCPA_SUNDAY")
        logger.warning(
            "FDCPA violation: Sunday call at %02d:00 before 1 PM (dealer=%s)",
            timestamp.hour,
            record.get("dealer_id", "unknown")
        )

    # Rule 3 – Days past due validation
    days = record.get("days_past_due", 0)
    if days < 0:
        violations.append("NEGATIVE_DAYS")
        logger.warning("Invalid days_past_due=%s (negative)", days)
    elif days >= 180:
        violations.append("INVALID_ACCOUNT_AGE")
        logger.warning("Account age violation: days_past_due=%s >= 180", days)

    # Rule 4 – Statute of limitations (7 years = 2555 days)
    if days >= 2555:
        violations.append("STATUTE_EXPIRED")
        logger.warning("Statute of limitations: days_past_due=%s exceeds 7 years", days)

    # Rule 5 – TCPA consent flag
    flags = record.get("compliance_flags", "")
    if "TCPA_OK" not in flags:
        violations.append("MISSING_TCPA_CONSENT")
        logger.warning("Missing TCPA_OK consent flag (dealer=%s)", record.get("dealer_id"))

    # Rule 6 – Call duration limits
    duration_minutes = record.get("call_duration_minutes", 0)
    if duration_minutes > 0:
        if duration_minutes < 0.5:  # Less than 30 seconds
            violations.append("CALL_TOO_SHORT")
            logger.warning("Suspicious short call: %.2f minutes (dealer=%s)", duration_minutes, record.get("dealer_id"))
        elif duration_minutes > 60:
            violations.append("CALL_TOO_LONG")
            logger.warning("Excessive call duration: %.2f minutes (dealer=%s)", duration_minutes, record.get("dealer_id"))

    # Rule 7 – Debt balance validation
    balance = record.get("debt_balance", 0)
    if balance <= 0:
        violations.append("INVALID_BALANCE")
        logger.warning("Invalid debt_balance=%.2f (must be positive)", balance)

    # Rule 8 – Contact frequency (if DB session provided)
    if db is not None:
        dealer_id = record.get("dealer_id")
        if dealer_id and _check_excessive_contact(db, dealer_id, timestamp):
            violations.append("EXCESSIVE_CONTACT")
            logger.warning("Excessive contact frequency for dealer=%s", dealer_id)

    # Determine final status
    if violations:
        status = "FAIL"
        lines = [f"{code} — {VIOLATION_CODES.get(code, 'Unknown violation')}" for code in violations]
        details = "\n".join(lines)
        logger.info("Compliance FAIL for dealer=%s — %d violations", record.get("dealer_id"), len(violations))
    else:
        status = "PASS"
        details = "All compliance checks passed"
        logger.info("Compliance PASS for dealer=%s", record.get("dealer_id", "unknown"))

    return {
        "compliance_status": status,
        "compliance_violations": violations,
        "compliance_details": details,
    }


def _check_excessive_contact(db: Session, dealer_id: str, current_timestamp: datetime) -> bool:
    """
    Check if this call would exceed the maximum contact frequency.

    FDCPA guideline: No more than 3 calls per 7-day period to the same debtor.

    Args:
        db: Database session
        dealer_id: Debtor identifier
        current_timestamp: Current call timestamp

    Returns:
        True if contact frequency limit exceeded, False otherwise
    """
    from database.models import CallRecord

    # Calculate 7 days ago
    seven_days_ago = current_timestamp - timedelta(days=7)

    # Count calls to this dealer in the past 7 days
    recent_call_count = (
        db.query(CallRecord)
        .filter(CallRecord.dealer_id == dealer_id)
        .filter(CallRecord.call_timestamp >= seven_days_ago)
        .filter(CallRecord.call_timestamp < current_timestamp)
        .count()
    )

    # Allow up to 3 calls per 7 days (so current call would be 4th)
    return recent_call_count >= 3


def get_violation_description(code: str) -> str:
    """Get human-readable description for a violation code."""
    return VIOLATION_CODES.get(code, "Unknown violation")
