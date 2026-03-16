"""Unit tests for the decision engine."""

from services.decision_service import make_decision


def test_dispute_flag_escalates():
    enriched = {
        "dispute_flag": True,
        "intent_class": "COMMITTED",
        "sentiment_score": 0.9,
        "compliance_status": "PASS",
    }
    result = make_decision(enriched)
    assert result["next_action"] == "ESCALATE"
    assert result["fulfillment_probability"] == 0.0


def test_committed_positive_sentiment():
    enriched = {
        "dispute_flag": False,
        "intent_class": "COMMITTED",
        "sentiment_score": 0.8,
        "compliance_status": "PASS",
    }
    result = make_decision(enriched)
    assert result["next_action"] == "SCHEDULE_FOLLOWUP"
    assert result["fulfillment_probability"] == round(min(0.8 * 1.1, 1.0), 4)
    assert "intent=COMMITTED" in result["decision_rationale"]
    assert "sentiment=0.80" in result["decision_rationale"]


def test_committed_low_sentiment_falls_to_default():
    enriched = {
        "dispute_flag": False,
        "intent_class": "COMMITTED",
        "sentiment_score": 0.3,
        "compliance_status": "PASS",
    }
    result = make_decision(enriched)
    # sentiment 0.3 <= 0.5 so it doesn't match priority 2, falls to default
    assert result["next_action"] == "WAIT_AND_MONITOR"
    assert result["fulfillment_probability"] == round(0.3 * 0.6, 4)


def test_evasive_intent_escalates():
    enriched = {
        "dispute_flag": False,
        "intent_class": "EVASIVE",
        "sentiment_score": 0.4,
        "compliance_status": "PASS",
    }
    result = make_decision(enriched)
    assert result["next_action"] == "ESCALATE"
    assert result["fulfillment_probability"] == round(0.4 * 0.3, 4)
    assert "EVASIVE" in result["decision_rationale"]


def test_compliance_fail_escalates():
    enriched = {
        "dispute_flag": False,
        "intent_class": "CONDITIONAL",
        "sentiment_score": 0.6,
        "compliance_status": "FAIL",
    }
    result = make_decision(enriched)
    assert result["next_action"] == "ESCALATE"
    assert "compliance=FAIL" in result["decision_rationale"]


def test_default_conditional_wait_and_monitor():
    enriched = {
        "dispute_flag": False,
        "intent_class": "CONDITIONAL",
        "sentiment_score": 0.5,
        "compliance_status": "PASS",
    }
    result = make_decision(enriched)
    assert result["next_action"] == "WAIT_AND_MONITOR"
    assert result["fulfillment_probability"] == round(0.5 * 0.6, 4)
    assert "Conditional" in result["decision_rationale"]


def test_dispute_takes_priority_over_everything():
    """Dispute should override even evasive + compliance fail."""
    enriched = {
        "dispute_flag": True,
        "intent_class": "EVASIVE",
        "sentiment_score": 0.1,
        "compliance_status": "FAIL",
    }
    result = make_decision(enriched)
    assert result["next_action"] == "ESCALATE"


def test_rationale_includes_variable_values():
    """Rationale strings should contain actual metric values."""
    enriched = {
        "dispute_flag": False,
        "intent_class": "CONDITIONAL",
        "sentiment_score": 0.65,
        "compliance_status": "PASS",
    }
    result = make_decision(enriched)
    assert "0.65" in result["decision_rationale"]
    assert "CONDITIONAL" in result["decision_rationale"]
