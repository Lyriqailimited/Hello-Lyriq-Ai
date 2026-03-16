"""
Decision engine – determines the recommended next action for a call record.

Decision logic (in priority order):
  1. dispute_flag is True                          → ESCALATE
  2. COMMITTED intent & sentiment > 0.5            → SCHEDULE_FOLLOWUP
  3. EVASIVE intent or compliance FAIL             → ESCALATE
  4. Otherwise (CONDITIONAL / unknown)             → WAIT_AND_MONITOR

Returns {"next_action": str, "decision_rationale": str, "fulfillment_probability": float}.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def make_decision(enriched: dict[str, Any]) -> dict[str, Any]:
    """Produce a decision dict based on enriched record fields."""
    dispute = enriched.get("dispute_flag", False)
    intent = enriched.get("intent_class", "")
    sentiment = enriched.get("sentiment_score", 0.0)
    compliance = enriched.get("compliance_status", "")

    # Priority 1 – active dispute
    if dispute:
        logger.info("Decision: ESCALATE — active dispute flag")
        return {
            "next_action": "ESCALATE",
            "decision_rationale": "Active dispute flag detected; escalating to supervisor.",
            "fulfillment_probability": 0.0,
        }

    # Priority 2 – committed debtor with positive sentiment
    if intent == "COMMITTED" and sentiment > 0.5:
        prob = round(min(sentiment * 1.1, 1.0), 4)
        logger.info("Decision: SCHEDULE_FOLLOWUP — committed+positive (prob=%.4f)", prob)
        return {
            "next_action": "SCHEDULE_FOLLOWUP",
            "decision_rationale": (
                f"Debtor intent={intent} with sentiment={sentiment:.2f}; "
                f"high confidence (prob={prob:.4f}), scheduling follow-up."
            ),
            "fulfillment_probability": prob,
        }

    # Priority 3 – evasive intent or compliance failure → ESCALATE
    if intent == "EVASIVE" or compliance == "FAIL":
        prob = round(sentiment * 0.3, 4)
        logger.info("Decision: ESCALATE — evasive/compliance (prob=%.4f)", prob)
        return {
            "next_action": "ESCALATE",
            "decision_rationale": (
                f"Intent={intent}, compliance={compliance}, sentiment={sentiment:.2f}; "
                f"escalating for manual review (prob={prob:.4f})."
            ),
            "fulfillment_probability": prob,
        }

    # Default – conditional or unknown intent → WAIT_AND_MONITOR
    probability = round(sentiment * 0.6, 4)
    logger.info("Decision: WAIT_AND_MONITOR — default (prob=%.4f)", probability)
    return {
        "next_action": "WAIT_AND_MONITOR",
        "decision_rationale": (
            f"Conditional intent={intent}, sentiment={sentiment:.2f}; "
            f"monitoring recommended (prob={probability:.4f})."
        ),
        "fulfillment_probability": probability,
    }
