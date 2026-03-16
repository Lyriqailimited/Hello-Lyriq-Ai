"""
Rule-based fulfillment prediction using weighted scoring system.

Features used:
  - intent_class (COMMITTED, CONDITIONAL, EVASIVE)
  - sentiment_score (0.0 - 1.0)
  - days_past_due (number of days)
  - promise_coverage_ratio (0.0 - 1.0+)
  - call_duration_minutes (minutes)
  - dispute_flag (boolean)

Scoring methodology:
  - Intent weight: COMMITTED=0.40, CONDITIONAL=0.20, EVASIVE=0.0
  - Sentiment: Linear scale 0-1 × 0.25
  - Days past due: Tiered scoring (0-30=0.20, 31-60=0.15, 61-90=0.10, 90+=0.05)
  - Promise coverage: Linear scale 0-1 × 0.30
  - Call duration: Tiered scoring (<2min=0.0, 2-5min=0.05, 5+min=0.10)
  - Dispute penalty: -0.30 if dispute_flag is True
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Intent scoring weights
_INTENT_WEIGHTS = {
    "COMMITTED": 0.40,
    "CONDITIONAL": 0.20,
    "EVASIVE": 0.0
}

# Days past due tiers (days, score)
_DAYS_PAST_DUE_TIERS = [
    (30, 0.20),
    (60, 0.15),
    (90, 0.10),
    (float('inf'), 0.05)
]

# Call duration tiers (minutes, score)
_CALL_DURATION_TIERS = [
    (2, 0.0),
    (5, 0.05),
    (float('inf'), 0.10)
]

# Component weights
_SENTIMENT_WEIGHT = 0.25
_COVERAGE_WEIGHT = 0.30
_DISPUTE_PENALTY = 0.30


def _get_intent_score(intent_class: str) -> float:
    """Return the weighted score for the given intent class."""
    return _INTENT_WEIGHTS.get(intent_class, _INTENT_WEIGHTS["CONDITIONAL"])


def _get_days_past_due_score(days: int) -> float:
    """Return tiered score based on days past due."""
    for threshold, score in _DAYS_PAST_DUE_TIERS:
        if days <= threshold:
            return score
    return 0.05


def _get_call_duration_score(minutes: float) -> float:
    """Return tiered score based on call duration."""
    for threshold, score in _CALL_DURATION_TIERS:
        if minutes < threshold:
            return score
    return 0.10


def predict_fulfillment(record: dict[str, Any]) -> float:
    """
    Calculate fulfillment probability [0, 1] using rule-based weighted scoring.

    Args:
        record: Dictionary containing call record fields

    Returns:
        Fulfillment probability between 0.0 and 1.0
    """
    # Extract features
    intent_class = record.get("intent_class", "CONDITIONAL")
    sentiment = record.get("sentiment_score", 0.0)
    days_past_due = record.get("days_past_due", 0)
    coverage_ratio = record.get("promise_coverage_ratio", 0.0)
    call_duration = record.get("call_duration_minutes", 0.0)
    dispute_flag = record.get("dispute_flag", False)

    # Calculate component scores
    intent_score = _get_intent_score(intent_class)
    sentiment_score = sentiment * _SENTIMENT_WEIGHT
    days_score = _get_days_past_due_score(days_past_due)
    coverage_score = min(coverage_ratio, 1.0) * _COVERAGE_WEIGHT
    duration_score = _get_call_duration_score(call_duration)

    # Sum all components
    total_score = (
        intent_score +
        sentiment_score +
        days_score +
        coverage_score +
        duration_score
    )

    # Apply dispute penalty
    if dispute_flag:
        total_score -= _DISPUTE_PENALTY
        logger.debug("Dispute flag detected — applying penalty of -%.2f", _DISPUTE_PENALTY)

    # Clamp to [0, 1] range
    probability = max(0.0, min(1.0, total_score))

    logger.debug(
        "Fulfillment prediction: %.4f (intent=%.2f, sentiment=%.2f, days=%.2f, "
        "coverage=%.2f, duration=%.2f, dispute=%s)",
        probability, intent_score, sentiment_score, days_score,
        coverage_score, duration_score, dispute_flag
    )

    return round(probability, 4)
