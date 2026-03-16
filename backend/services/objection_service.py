"""
Objection extraction and analysis service.

Identifies and categorizes common debtor objections from call transcripts.

Objection categories:
  1. FINANCIAL_HARDSHIP - Job loss, unemployment, reduced income
  2. DISPUTE_DEBT - Claims debt is not owed, already paid, incorrect amount
  3. REQUEST_VALIDATION - Wants debt verification, documentation
  4. PAYMENT_PLAN - Requests installment arrangement, lower payment
  5. INSUFFICIENT_FUNDS - Can't pay now, waiting for paycheck
  6. MEDICAL_EMERGENCY - Medical bills, health issues
  7. ATTORNEY_REPRESENTATION - Represented by counsel
  8. BANKRUPTCY - Filed or planning to file bankruptcy
  9. REFUSES_CONTACT - Requests no further contact, cease and desist
  10. OTHER - Other objections not fitting above categories

Uses keyword/phrase matching for classification with confidence scoring.
"""

import logging
import re
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Objection patterns - (category, keywords/phrases, weight)
OBJECTION_PATTERNS = {
    "FINANCIAL_HARDSHIP": [
        "lost my job", "unemployed", "laid off", "reduced hours",
        "lost income", "can't afford", "hardship", "financial difficulty",
        "no income", "disability", "on fixed income", "social security"
    ],
    "DISPUTE_DEBT": [
        "don't owe", "already paid", "not my debt", "dispute", "wrong amount",
        "incorrect balance", "never received", "fraud", "identity theft",
        "not mine", "belongs to someone else", "disputed"
    ],
    "REQUEST_VALIDATION": [
        "prove it", "send proof", "validation", "verify", "documentation",
        "show me", "need evidence", "written proof", "debt validation",
        "validation letter", "prove i owe"
    ],
    "PAYMENT_PLAN": [
        "payment plan", "installment", "monthly payment", "smaller payments",
        "pay over time", "spread out", "can pay $", "arrange payment",
        "settlement", "negotiate", "lower amount", "reduce balance"
    ],
    "INSUFFICIENT_FUNDS": [
        "no money right now", "waiting for paycheck", "get paid on",
        "check comes", "need more time", "can't pay today", "next week",
        "waiting for", "don't have it now", "payday"
    ],
    "MEDICAL_EMERGENCY": [
        "medical bills", "hospital", "surgery", "sick", "medical emergency",
        "health problems", "doctor", "medical expenses", "medical debt",
        "treatment", "medication costs"
    ],
    "ATTORNEY_REPRESENTATION": [
        "attorney", "lawyer", "counsel", "legal representation",
        "talk to my attorney", "represented", "refer you to my lawyer",
        "my lawyer", "legal counsel"
    ],
    "BANKRUPTCY": [
        "bankruptcy", "filed bankruptcy", "filing bankruptcy", "chapter 7",
        "chapter 11", "chapter 13", "discharged", "bankruptcy attorney"
    ],
    "REFUSES_CONTACT": [
        "stop calling", "don't call", "cease and desist", "harassment",
        "remove from list", "do not contact", "stop contacting",
        "take me off", "no more calls", "harassing me"
    ],
}


def extract_objections(transcript: str, transcript_summary: str = "") -> dict[str, Any]:
    """
    Extract and categorize objections from a call transcript.

    Args:
        transcript: Full cleaned transcript text
        transcript_summary: Optional summary for additional context

    Returns:
        Dictionary containing:
        - primary_objection: Main objection category (or None)
        - all_objections: List of all detected objection categories
        - objection_details: Human-readable description
        - objection_confidence: Confidence score [0.0, 1.0]
    """
    # Combine transcript and summary for analysis
    full_text = f"{transcript} {transcript_summary}".lower()

    # Track detected objections with their match counts
    detected = {}

    for category, keywords in OBJECTION_PATTERNS.items():
        match_count = sum(1 for keyword in keywords if keyword.lower() in full_text)
        if match_count > 0:
            detected[category] = match_count

    # No objections found
    if not detected:
        logger.debug("No objections detected in transcript")
        return {
            "primary_objection": None,
            "all_objections": [],
            "objection_details": "No objections detected",
            "objection_confidence": 0.0,
        }

    # Sort by match count to find primary objection
    sorted_objections = sorted(detected.items(), key=lambda x: x[1], reverse=True)
    primary_objection = sorted_objections[0][0]
    primary_match_count = sorted_objections[0][1]

    # All detected objection categories
    all_objections = [cat for cat, _ in sorted_objections]

    # Calculate confidence based on match count and specificity
    # More matches and fewer categories = higher confidence
    confidence = min(1.0, (primary_match_count * 0.25) / len(all_objections))

    # Build details string
    if len(all_objections) == 1:
        details = f"Primary objection: {primary_objection}"
    else:
        details = f"Primary: {primary_objection}; Also detected: {', '.join(all_objections[1:])}"

    logger.info(
        "Objection extraction: primary=%s, count=%d, confidence=%.2f",
        primary_objection,
        len(all_objections),
        confidence
    )

    return {
        "primary_objection": primary_objection,
        "all_objections": all_objections,
        "objection_details": details,
        "objection_confidence": round(confidence, 4),
    }


def get_objection_description(category: str) -> str:
    """Get human-readable description for an objection category."""
    descriptions = {
        "FINANCIAL_HARDSHIP": "Job loss, unemployment, or reduced income",
        "DISPUTE_DEBT": "Claims debt is not owed or incorrect",
        "REQUEST_VALIDATION": "Requests debt verification/documentation",
        "PAYMENT_PLAN": "Requests installment arrangement",
        "INSUFFICIENT_FUNDS": "Cannot pay now, waiting for funds",
        "MEDICAL_EMERGENCY": "Medical bills or health issues",
        "ATTORNEY_REPRESENTATION": "Represented by legal counsel",
        "BANKRUPTCY": "Filed or planning bankruptcy",
        "REFUSES_CONTACT": "Requests no further contact",
        "OTHER": "Other objections",
    }
    return descriptions.get(category, "Unknown objection")


def analyze_objection_trends(db, days: int = 7) -> dict[str, Any]:
    """
    Analyze objection trends across all calls in the specified time period.

    Args:
        db: Database session
        days: Number of days to look back (default: 7)

    Returns:
        Dictionary with objection statistics and trends
    """
    from database.models import CallRecord
    from sqlalchemy import func
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    # Get all records with objections in the time period
    records = (
        db.query(CallRecord)
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .filter(CallRecord.primary_objection.isnot(None))
        .all()
    )

    if not records:
        return {
            "total_calls_with_objections": 0,
            "time_period_days": days,
            "objection_distribution": {},
            "top_objections": [],
        }

    # Count objections by category
    objection_counts = {}
    for record in records:
        category = record.primary_objection
        objection_counts[category] = objection_counts.get(category, 0) + 1

    # Sort by frequency
    sorted_objections = sorted(
        objection_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Top 5 objections with percentages
    total = len(records)
    top_objections = [
        {
            "category": cat,
            "count": count,
            "percentage": round((count / total) * 100, 2),
            "description": get_objection_description(cat)
        }
        for cat, count in sorted_objections[:5]
    ]

    logger.info(
        "Objection analysis: %d calls with objections in past %d days",
        total,
        days
    )

    return {
        "total_calls_with_objections": total,
        "time_period_days": days,
        "objection_distribution": objection_counts,
        "top_objections": top_objections,
    }
