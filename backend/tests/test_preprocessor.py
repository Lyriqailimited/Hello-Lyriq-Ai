"""Unit tests for the preprocessor pipeline."""

from preprocessor.preprocessor import (
    _strip_phone_numbers,
    _strip_account_numbers,
    _generate_summary,
    _compute_sentiment,
    _validate_pii_scrubbed,
    run_pipeline,
)
from preprocessor.token_map import anonymise, TOKEN_MAP


def test_anonymise_known_name():
    assert "CRT-8972p" in anonymise("Hello Jane Smith")
    assert "Jane Smith" not in anonymise("Hello Jane Smith")


def test_anonymise_all_five_debtors():
    """All 5 sample debtors should be in the token map."""
    assert len(TOKEN_MAP) == 5
    for name in ["Jane Smith", "John Doe", "Maria Garcia", "Robert Chen", "Aisha Patel"]:
        assert name in TOKEN_MAP
        assert name not in anonymise(f"Contact {name} regarding account")


def test_anonymise_unknown_name_unchanged():
    text = "Hello Bob Johnson"
    assert anonymise(text) == text


def test_strip_phone_numbers():
    assert _strip_phone_numbers("Call 555-867-5309 now") == "Call [REDACTED] now"
    assert _strip_phone_numbers("Call 5558675309 now") == "Call [REDACTED] now"
    assert _strip_phone_numbers("Call 555.867.5309 now") == "Call [REDACTED] now"


def test_strip_account_numbers():
    assert _strip_account_numbers("Account 12345678 info") == "Account [ACCT] info"
    assert _strip_account_numbers("Short 1234 stays") == "Short 1234 stays"


# --- Sentiment scoring ---


def test_sentiment_uses_raw_when_provided():
    assert _compute_sentiment("some transcript", "0.72") == 0.72


def test_sentiment_keyword_positive():
    text = "Debtor will pay and agrees to the arrangement"
    score = _compute_sentiment(text, None)
    assert score > 0.5


def test_sentiment_keyword_negative():
    text = "Debtor refuse to pay and cannot make any arrangement"
    score = _compute_sentiment(text, None)
    assert score < 0.5


def test_sentiment_keyword_neutral_default():
    text = "Agent called the debtor"
    score = _compute_sentiment(text, None)
    assert score == 0.5


# --- Template summary ---


def test_summary_payment_intent():
    text = "Debtor stated they will pay $500 by end of month"
    summary = _generate_summary(text)
    assert "willingness to pay" in summary.lower()
    assert "$500" in summary


def test_summary_dispute():
    text = "Debtor disputed the balance claiming they already paid"
    summary = _generate_summary(text)
    assert "disputed" in summary.lower()


def test_summary_fallback_for_plain_text():
    text = "Agent greeted the customer and discussed the account status."
    summary = _generate_summary(text)
    assert len(summary) <= 200


def test_summary_long_text_capped():
    text = "Debtor will pay. " * 50  # much longer than 200
    summary = _generate_summary(text)
    assert len(summary) <= 203  # 200 + "..."


# --- PII validation gate ---


def test_pii_validation_passes_clean_text():
    assert _validate_pii_scrubbed("Agent called CRT-8972p about the account.") is True


def test_pii_validation_fails_with_name():
    assert _validate_pii_scrubbed("Agent called Jane Smith about the account.") is False


def test_pii_validation_fails_with_phone():
    assert _validate_pii_scrubbed("Call 555-867-5309 for details.") is False


# --- Full pipeline ---


def test_run_pipeline_full(sample_raw_call):
    result = run_pipeline(sample_raw_call)

    assert result["dealer_id"] == "DLR-00421"
    assert result["sentiment_score"] == 0.72
    assert result["days_past_due"] == 45
    assert result["debt_balance"] == 4200.00
    assert result["promise_amount"] == 500.00
    assert result["dispute_flag"] is False
    # PII should be redacted
    assert "Jane Smith" not in result["transcript_summary"]
    assert "555-867-5309" not in result["transcript_summary"]
    # Promise coverage ratio computed
    assert result["promise_coverage_ratio"] == round(500 / 4200, 4)


def test_run_pipeline_missing_optional_fields():
    """Pipeline should handle minimal input without crashing."""
    raw = {
        "dealer_id": "DLR-001",
        "transcript": "Short call with no details.",
        "timestamp": "2026-03-12T10:00:00",
    }
    result = run_pipeline(raw)
    assert result["dealer_id"] == "DLR-001"
    assert result["days_past_due"] == 0
    assert result["promise_amount"] == 0.0
    assert result["promise_coverage_ratio"] == 0.0
    # No raw sentiment → keyword-based (neutral)
    assert result["sentiment_score"] == 0.5


def test_run_pipeline_sentiment_from_keywords():
    """When no sentiment_raw is provided, sentiment is computed from keywords."""
    raw = {
        "dealer_id": "DLR-002",
        "transcript": "Debtor refuse to pay and cannot make any arrangement. Debtor hung up.",
        "timestamp": "2026-03-12T10:00:00",
    }
    result = run_pipeline(raw)
    assert result["sentiment_score"] < 0.5
