"""
Intent classification service using OpenRouter API (OpenAI-compatible).

Classifies a call transcript into one of 9 outcome classes:
  1. Promise to Pay
  2. Call Reschedule or Callback Requested
  3. Invoice Dispute
  4. Refused to Pay
  5. Already Paid (Claimed)
  6. No Outcome / Unavailable
  7. Requested Invoice Copy
  8. Requested Payment Link
  9. Reminder Delivered

Returns {"intent_class": str, "call_outcome": str, "confidence": float}.
"""

import json
import logging
import os
import requests
from typing import Any

logger = logging.getLogger(__name__)

VALID_OUTCOMES = [
    "Promise to Pay",
    "Call Reschedule or Callback Requested",
    "Invoice Dispute",
    "Refused to Pay",
    "Already Paid (Claimed)",
    "No Outcome / Unavailable",
    "Requested Invoice Copy",
    "Requested Payment Link",
    "Reminder Delivered",
]

_KEYWORD_MAP = [
    ("Promise to Pay",                        ["will pay", "promise to pay", "i'll pay", "i will pay", "agreed to pay", "payment arrangement", "i can pay"]),
    ("Call Reschedule or Callback Requested", ["call back", "callback", "call me back", "reschedule", "call again", "better time", "try again later"]),
    ("Invoice Dispute",                       ["dispute", "disputed", "incorrect", "wrong amount", "not mine", "escalate", "manager"]),
    ("Already Paid (Claimed)",                ["already paid", "paid already", "i paid", "payment was made", "sent the payment"]),
    ("Refused to Pay",                        ["refuse", "won't pay", "will not pay", "not paying", "hung up", "disconnected", "refused"]),
    ("No Outcome / Unavailable",              ["no answer", "voicemail", "not available", "unavailable", "could not reach"]),
    ("Requested Invoice Copy",                ["invoice copy", "send invoice", "copy of invoice", "resend", "documentation"]),
    ("Requested Payment Link",                ["payment link", "pay online", "send link", "portal", "online payment"]),
    ("Reminder Delivered",                    ["reminder", "left message", "voicemail left", "message left"]),
]

_SYSTEM_PROMPT = """You are an expert at analyzing B2B debt collection / accounts-receivable call transcripts.

Classify the PRIMARY outcome of the call based on what the debtor said and did.

Choose EXACTLY one of these outcomes:
1. Promise to Pay — Debtor explicitly agreed to pay a specific amount, or committed to a payment date/plan.
2. Call Reschedule or Callback Requested — Debtor asked to be called back or requested a better time to discuss.
3. Invoice Dispute — Debtor disputed the invoice amount, claimed it is incorrect, or requested escalation to resolve a discrepancy.
4. Refused to Pay — Debtor clearly refused to pay, was uncooperative, or ended the call without any commitment.
5. Already Paid (Claimed) — Debtor claimed the invoice has already been paid.
6. No Outcome / Unavailable — Could not reach the debtor; no meaningful discussion took place.
7. Requested Invoice Copy — Debtor asked for a copy of the invoice or supporting documentation (without disputing).
8. Requested Payment Link — Debtor asked for a payment link or online payment portal.
9. Reminder Delivered — A reminder was delivered via voicemail or brief message with no substantive discussion.

Rules:
- Base your decision ONLY on the debtor's responses, not the agent's prompts.
- If the debtor said "No" to payment AND "No" to a commitment date with no other context, classify as "Refused to Pay".
- Pick the single most dominant outcome.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{"intent_class": "<one of the 9 outcomes above>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}"""


def _classify_via_claude_api(transcript: str) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "anthropic/claude-haiku-4-5",
            "max_tokens": 256,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify the outcome of this call transcript:\n\n{transcript}"},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())

    intent_class = parsed.get("intent_class", "").strip()
    if intent_class not in VALID_OUTCOMES:
        logger.warning("Claude returned invalid outcome %r, defaulting to 'No Outcome / Unavailable'", intent_class)
        intent_class = "No Outcome / Unavailable"

    confidence = round(max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))), 4)
    logger.info("Claude classified: %r (confidence=%.4f) — %s", intent_class, confidence, parsed.get("reasoning", ""))

    return {"intent_class": intent_class, "call_outcome": intent_class, "confidence": confidence}


def _classify_via_keywords(transcript: str) -> dict[str, Any]:
    text = transcript.lower()
    for outcome, keywords in _KEYWORD_MAP:
        for kw in keywords:
            if kw in text:
                logger.info("Keyword classified: %r (keyword=%r)", outcome, kw)
                return {"intent_class": outcome, "call_outcome": outcome, "confidence": 0.55}

    logger.info("No keyword match — defaulting to 'No Outcome / Unavailable'")
    return {"intent_class": "No Outcome / Unavailable", "call_outcome": "No Outcome / Unavailable", "confidence": 0.40}


def classify_intent(transcript: str) -> dict[str, Any]:
    """
    Classify call outcome from the full transcript.
    Tries Claude via OpenRouter first, falls back to keyword matching.
    """
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
        try:
            return _classify_via_claude_api(transcript)
        except Exception as e:
            logger.error("Claude API failed: %s — falling back to keywords", e)

    return _classify_via_keywords(transcript)


def is_claude_api_available() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
