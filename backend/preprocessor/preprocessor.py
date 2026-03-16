"""
Preprocessor – first stage of the ingestion pipeline.

run_pipeline(raw) → cleaned, validated dict ready for service enrichment.

Internal steps:
  1. Parse raw JSON fields
  2. Strip PII via token_map, regex phone/account numbers
  3. Validate PII has been scrubbed (validation gate)
  4. Compute keyword-based sentiment score (if no raw sentiment provided)
  5. Generate a template-based transcript summary
  6. Extract metadata (amounts, dates)
  7. Validate and return a clean dict
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from preprocessor.token_map import TOKEN_MAP, anonymise

logger = logging.getLogger(__name__)

# Keyword lists for sentiment scoring
_POSITIVE_KEYWORDS = [
    "will pay", "agree", "committed", "promise", "cooperate",
    "arrangement", "payment plan", "thank", "appreciate", "yes",
]
_NEGATIVE_KEYWORDS = [
    "refuse", "cannot", "won't", "dispute", "no money", "not able",
    "hung up", "disconnected", "angry", "upset", "complain",
]

# Phone number pattern: 10-digit US numbers with optional separators
_PHONE_RE = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
# Account-like sequences: 8-16 digit numbers
_ACCOUNT_RE = re.compile(r"\b\d{8,16}\b")


def _strip_phone_numbers(text: str) -> str:
    """Remove phone numbers from text."""
    return _PHONE_RE.sub("[REDACTED]", text)


def _strip_account_numbers(text: str) -> str:
    """Remove account-like number sequences."""
    return _ACCOUNT_RE.sub("[ACCT]", text)


def _validate_pii_scrubbed(text: str) -> bool:
    """Check that no known PII names or raw phone/account numbers remain."""
    for original_name in TOKEN_MAP:
        if original_name in text:
            logger.warning("PII validation FAIL — found unscrubbed name: %s", original_name)
            return False
    if _PHONE_RE.search(text):
        logger.warning("PII validation FAIL — phone number pattern still present")
        return False
    return True


def _compute_sentiment(transcript: str, raw_sentiment: Any) -> float:
    """
    Compute sentiment score. Uses raw_sentiment if provided,
    otherwise falls back to keyword-based scoring.
    """
    if raw_sentiment is not None and raw_sentiment != "":
        try:
            return float(raw_sentiment)
        except (ValueError, TypeError):
            pass

    text_lower = transcript.lower()
    pos_count = sum(1 for kw in _POSITIVE_KEYWORDS if kw in text_lower)
    neg_count = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return 0.5  # neutral default
    return round(pos_count / total, 4)


def _generate_summary(transcript: str) -> str:
    """
    Template-based summary: extract key phrases and compose a structured summary.
    Looks for payment mentions, dispute flags, and outcome indicators.
    """
    text_lower = transcript.lower()
    phrases = []

    # Payment-related phrases
    if any(kw in text_lower for kw in ["will pay", "promise to pay", "payment plan", "agreed"]):
        phrases.append("Debtor indicated willingness to pay")
    if any(kw in text_lower for kw in ["refuse", "won't", "cannot pay", "not able"]):
        phrases.append("Debtor expressed inability or refusal to pay")
    if any(kw in text_lower for kw in ["dispute", "disputed", "already paid"]):
        phrases.append("Debtor disputed the balance")
    if any(kw in text_lower for kw in ["hung up", "disconnected", "ended call"]):
        phrases.append("Call ended prematurely")
    if any(kw in text_lower for kw in ["maybe", "possibly", "might", "consider", "depends"]):
        phrases.append("Debtor expressed conditional intent")
    if any(kw in text_lower for kw in ["hardship", "job loss", "unemployed"]):
        phrases.append("Debtor reported financial hardship")

    # Extract dollar amounts mentioned
    amounts = re.findall(r"\$[\d,]+(?:\.\d{2})?", transcript)
    if amounts:
        phrases.append(f"Amount(s) mentioned: {', '.join(amounts)}")

    if phrases:
        summary = ". ".join(phrases) + "."
    else:
        # Fallback: truncate transcript
        cleaned = transcript.strip()
        if len(cleaned) > 200:
            summary = cleaned[:200].rsplit(" ", 1)[0] + "..."
        else:
            summary = cleaned

    # Cap at 200 chars
    if len(summary) > 200:
        summary = summary[:200].rsplit(" ", 1)[0] + "..."
    return summary


def _extract_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Pull structured fields from the raw input."""
    return {
        "dealer_id": raw.get("dealer_id", raw.get("call_id", "")),
        "call_outcome": raw.get("call_outcome", "UNKNOWN"),
        "days_past_due": int(raw.get("past_due", raw.get("days_past_due", 0))),
        "debt_balance": float(
            raw.get("outstanding_amount", raw.get("original_balance", raw.get("debt_balance", 0.0)))
        ),
        "promise_amount": float(raw.get("promise_amount", 0.0)),
        "promise_coverage_ratio": 0.0,  # computed below
        "call_timestamp": raw.get("timestamp", raw.get("call_timestamp", datetime.now(timezone.utc).isoformat())),
        "call_duration_sec": float(raw.get("duration", raw.get("call_duration_sec", 0))),
        "compliance_flags": raw.get("compliance_flags", ""),
        "dispute_flag": bool(raw.get("dispute_flag", False)),
    }


def run_pipeline(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Main entry point – accepts raw JSON dict, returns a cleaned + enriched dict
    ready for downstream services.
    """
    transcript = raw.get("transcript", "")

    # PII scrubbing
    transcript = anonymise(transcript)
    transcript = _strip_phone_numbers(transcript)
    transcript = _strip_account_numbers(transcript)

    pii_redactions = sum(
        1 for token in ["[REDACTED]", "[ACCT]", "CRT-"] if token in transcript
    )
    logger.info("PII redaction complete — %d redaction type(s) applied", pii_redactions)

    # PII validation gate
    if not _validate_pii_scrubbed(transcript):
        logger.error("PII validation gate failed — transcript may still contain PII")

    # Keyword-based sentiment scoring
    raw_sentiment = raw.get("sentiment_raw", raw.get("sentiment_score"))
    sentiment = _compute_sentiment(transcript, raw_sentiment)

    summary = _generate_summary(transcript)
    logger.info("Transcript summarised — %d chars", len(summary))

    meta = _extract_metadata(raw)
    meta["sentiment_score"] = sentiment

    # Compute promise coverage ratio
    debt = meta["debt_balance"]
    promise = meta["promise_amount"]
    meta["promise_coverage_ratio"] = round(promise / debt, 4) if debt > 0 else 0.0

    meta["transcript_summary"] = summary
    meta["_cleaned_transcript"] = transcript  # full cleaned text for intent classification

    return meta
