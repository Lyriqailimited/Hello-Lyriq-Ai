"""Unit tests for intent classification (Claude API + keyword fallback)."""

import os
from unittest.mock import patch
import pytest
from services.tm_service import classify_intent, is_claude_api_available


# ============================================================================
# Claude API Tests (Mocked)
# ============================================================================


@patch('services.tm_service._classify_via_claude_api')
def test_committed_via_claude_api(mock_claude):
    """Test COMMITTED classification via Claude API (mocked)."""
    mock_claude.return_value = {"intent_class": "COMMITTED", "confidence": 0.92}

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        result = classify_intent("I will pay $500 by Friday")

    assert result["intent_class"] == "COMMITTED"
    assert result["confidence"] == 0.92
    mock_claude.assert_called_once()


@patch('services.tm_service._classify_via_claude_api')
def test_evasive_via_claude_api(mock_claude):
    """Test EVASIVE classification via Claude API (mocked)."""
    mock_claude.return_value = {"intent_class": "EVASIVE", "confidence": 0.88}

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        result = classify_intent("I refuse to pay anything")

    assert result["intent_class"] == "EVASIVE"
    assert result["confidence"] == 0.88


@patch('services.tm_service._classify_via_claude_api')
def test_conditional_via_claude_api(mock_claude):
    """Test CONDITIONAL classification via Claude API (mocked)."""
    mock_claude.return_value = {"intent_class": "CONDITIONAL", "confidence": 0.75}

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        result = classify_intent("Maybe I can pay next week")

    assert result["intent_class"] == "CONDITIONAL"
    assert result["confidence"] == 0.75


@patch('services.tm_service._classify_via_claude_api')
def test_claude_api_fallback_on_error(mock_claude):
    """Test fallback to keywords when Claude API fails."""
    mock_claude.side_effect = Exception("API timeout")

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        result = classify_intent("I will pay")

    # Should fall back to keyword-based
    assert result["intent_class"] == "COMMITTED"
    assert result["confidence"] == 0.70  # keyword confidence


# ============================================================================
# Keyword Fallback Tests (No API Key)
# ============================================================================


def test_committed_will_pay():
    """Keyword: 'will pay' → COMMITTED."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor stated they will pay $500 by end of month.")
    assert result["intent_class"] == "COMMITTED"
    assert result["confidence"] == 0.70


def test_committed_promise_to_pay():
    """Keyword: 'promise to pay' → COMMITTED."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Customer said promise to pay the full amount.")
    assert result["intent_class"] == "COMMITTED"
    assert result["confidence"] == 0.70


def test_committed_agree():
    """Keyword: 'agree' → COMMITTED."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor said they agree to the terms.")
    assert result["intent_class"] == "COMMITTED"
    assert result["confidence"] == 0.70


def test_evasive_refuse():
    """Keyword: 'refuse' → EVASIVE."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor said they refuse to make any payment.")
    assert result["intent_class"] == "EVASIVE"
    assert result["confidence"] == 0.65


def test_evasive_cannot():
    """Keyword: 'cannot' → EVASIVE."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Customer said they cannot afford any payment right now.")
    assert result["intent_class"] == "EVASIVE"
    assert result["confidence"] == 0.65


def test_evasive_no_money():
    """Keyword: 'no money' → EVASIVE."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor stated no money available at this time.")
    assert result["intent_class"] == "EVASIVE"
    assert result["confidence"] == 0.65


def test_conditional_maybe():
    """Keyword: 'maybe' → CONDITIONAL."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor said maybe they can pay next month.")
    assert result["intent_class"] == "CONDITIONAL"
    assert result["confidence"] == 0.60


def test_conditional_if():
    """Keyword: 'if' → CONDITIONAL."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Customer said if they get paid, they'll send something.")
    assert result["intent_class"] == "CONDITIONAL"
    assert result["confidence"] == 0.60


def test_conditional_possibly():
    """Keyword: 'possibly' → CONDITIONAL."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor mentioned possibly making a partial payment.")
    assert result["intent_class"] == "CONDITIONAL"
    assert result["confidence"] == 0.60


def test_default_no_keywords():
    """No matching keywords → CONDITIONAL (default)."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("The call was brief and the debtor hung up quickly.")
    assert result["intent_class"] == "CONDITIONAL"
    assert result["confidence"] == 0.50


def test_case_insensitive():
    """Keywords should match case-insensitively."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor said WILL PAY immediately.")
    assert result["intent_class"] == "COMMITTED"


def test_committed_priority_over_evasive():
    """COMMITTED keywords are checked first."""
    with patch.dict(os.environ, {}, clear=True):
        result = classify_intent("Debtor initially said cannot but then agreed they will pay.")
    assert result["intent_class"] == "COMMITTED"


# ============================================================================
# API Availability Tests
# ============================================================================


def test_is_claude_api_available_with_key():
    """is_claude_api_available returns True when API key is set."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        assert is_claude_api_available() is True


def test_is_claude_api_available_without_key():
    """is_claude_api_available returns False when no API key."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_claude_api_available() is False


# ============================================================================
# Live API Test (Skipped Without API Key)
# ============================================================================


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY for live API testing"
)
def test_live_claude_api():
    """Live test with real Claude API (only runs when key is set)."""
    result = classify_intent("I promise to pay $500 by Friday")

    # Should get a result from Claude
    assert result["intent_class"] in ["COMMITTED", "CONDITIONAL", "EVASIVE"]
    assert 0 <= result["confidence"] <= 1.0

    # With this transcript, Claude should classify as COMMITTED with high confidence
    assert result["intent_class"] == "COMMITTED"
    assert result["confidence"] > 0.7
