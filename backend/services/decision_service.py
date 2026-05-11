"""
Decision engine – maps the 9 call outcomes to a recommended next action.

Next actions:
  SCHEDULE_FOLLOWUP  — debtor committed or requested callback
  ESCALATE           — dispute, compliance failure, or active dispute flag
  SEND_INVOICE       — debtor requested invoice copy
  SEND_PAYMENT_LINK  — debtor requested payment link
  MARK_PAID          — debtor claims already paid (verify)
  CLOSE              — debtor refused, no outcome, or reminder only
  WAIT_AND_MONITOR   — default fallback

Returns {"next_action": str, "decision_rationale": str, "fulfillment_probability": float}.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_OUTCOME_MAP = {
    "Promise to Pay":                        ("Schedule Follow-Up Call",       0.80),
    "Call Reschedule or Callback Requested": ("Schedule Follow-Up Call",       0.55),
    "Invoice Dispute":                       ("Escalate to Supervisor",        0.10),
    "Refused to Pay":                        ("Escalate to Supervisor",        0.05),
    "Already Paid (Claimed)":                ("Verify Payment in System",      0.50),
    "No Outcome / Unavailable":              ("Close — No Action Required",    0.15),
    "Requested Invoice Copy":                ("Send Invoice Copy to Debtor",   0.45),
    "Requested Payment Link":                ("Send Payment Portal Link",      0.60),
    "Reminder Delivered":                    ("Close — Reminder Delivered",    0.20),
}


def make_decision(enriched: dict[str, Any]) -> dict[str, Any]:
    dispute = enriched.get("dispute_flag", False)
    intent = enriched.get("intent_class", "No Outcome / Unavailable")
    sentiment = enriched.get("sentiment_score", 0.0)
    compliance = enriched.get("compliance_status", "")

    # Active dispute flag always escalates
    if dispute:
        logger.info("Decision: Escalate to Supervisor — active dispute flag")
        return {
            "next_action": "Escalate to Supervisor",
            "decision_rationale": "Active dispute flag detected; escalating to supervisor for manual review.",
            "fulfillment_probability": 0.0,
        }

    # Compliance failure escalates (unless it's a send-document action)
    if compliance == "FAIL" and intent not in ("Requested Invoice Copy", "Requested Payment Link"):
        base_action, base_prob = _OUTCOME_MAP.get(intent, ("Escalate to Supervisor", 0.10))
        if not any(x in base_action for x in ("Escalate", "Close", "Verify")):
            logger.info("Decision: Escalate to Supervisor — compliance FAIL overrides %s", base_action)
            return {
                "next_action": "Escalate to Supervisor",
                "decision_rationale": (
                    f"Outcome='{intent}' but compliance check failed; escalating for manual review."
                ),
                "fulfillment_probability": round(base_prob * 0.3, 4),
            }

    action, base_prob = _OUTCOME_MAP.get(intent, ("WAIT_AND_MONITOR", 0.30))

    # Sentiment-adjust fulfillment probability (±20%)
    sentiment_adj = round(base_prob * (0.8 + sentiment * 0.4), 4)
    fulfillment_prob = round(max(0.0, min(1.0, sentiment_adj)), 4)

    rationale = _build_rationale(intent, action, sentiment, compliance, fulfillment_prob)
    logger.info("Decision: %s — outcome=%r prob=%.4f", action, intent, fulfillment_prob)

    return {
        "next_action": action,
        "decision_rationale": rationale,
        "fulfillment_probability": fulfillment_prob,
    }


def _build_rationale(intent, action, sentiment, compliance, prob) -> str:
    if "Schedule Follow-Up" in action:
        return f"Debtor outcome='{intent}'; a follow-up call should be scheduled (sentiment={sentiment:.2f}, fulfillment prob={prob:.2f})."
    if "Escalate" in action:
        return f"Outcome='{intent}'; routing to supervisor for manual review (compliance={compliance}, prob={prob:.2f})."
    if "Send Invoice" in action:
        return f"Debtor requested a copy of the invoice; send documentation to debtor (prob={prob:.2f})."
    if "Send Payment" in action:
        return f"Debtor requested a payment link; share the online payment portal (prob={prob:.2f})."
    if "Verify Payment" in action:
        return f"Debtor claims the invoice was already paid; verify payment records before closing (prob={prob:.2f})."
    if "Close" in action:
        return f"Outcome='{intent}'; no further action required at this time (prob={prob:.2f})."
    return f"Outcome='{intent}', recommended action: {action} (prob={prob:.2f})."
