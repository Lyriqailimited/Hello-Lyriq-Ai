"""
Tests for objection extraction and analysis service.

Tests extraction of common debtor objections including:
  - Financial hardship
  - Debt disputes
  - Validation requests
  - Payment plan requests
  - Insufficient funds
  - Medical emergencies
  - Attorney representation
  - Bankruptcy
  - Refusal to be contacted
"""

import pytest
from services.objection_service import (
    extract_objections,
    get_objection_description,
    analyze_objection_trends,
)
from database.models import CallRecord
from datetime import datetime, timedelta


class TestObjectionExtraction:
    """Test objection extraction from transcripts."""

    def test_financial_hardship_detection(self):
        """Test detection of financial hardship objections."""
        transcript = "I lost my job last month and can't afford to pay right now. I'm on unemployment."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "FINANCIAL_HARDSHIP"
        assert "FINANCIAL_HARDSHIP" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_dispute_debt_detection(self):
        """Test detection of debt dispute objections."""
        transcript = "I don't owe this debt. This is not my account. I already paid this off last year."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "DISPUTE_DEBT"
        assert "DISPUTE_DEBT" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_validation_request_detection(self):
        """Test detection of validation request objections."""
        transcript = "I need you to prove this debt. Send me written proof and validation documentation."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "REQUEST_VALIDATION"
        assert "REQUEST_VALIDATION" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_payment_plan_request_detection(self):
        """Test detection of payment plan requests."""
        transcript = "Can we set up a payment plan? I can pay $100 monthly. Let's negotiate a settlement."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "PAYMENT_PLAN"
        assert "PAYMENT_PLAN" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_insufficient_funds_detection(self):
        """Test detection of insufficient funds objections."""
        transcript = "I don't have money right now. I'm waiting for my paycheck next week."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "INSUFFICIENT_FUNDS"
        assert "INSUFFICIENT_FUNDS" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_medical_emergency_detection(self):
        """Test detection of medical emergency objections."""
        transcript = "I had a medical emergency and have huge hospital bills from my surgery."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "MEDICAL_EMERGENCY"
        assert "MEDICAL_EMERGENCY" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_attorney_representation_detection(self):
        """Test detection of attorney representation objections."""
        transcript = "I have an attorney. Please talk to my lawyer. I'm legally represented."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "ATTORNEY_REPRESENTATION"
        assert "ATTORNEY_REPRESENTATION" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_bankruptcy_detection(self):
        """Test detection of bankruptcy objections."""
        transcript = "I filed for Chapter 7 bankruptcy last month. This debt was discharged."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "BANKRUPTCY"
        assert "BANKRUPTCY" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_refuses_contact_detection(self):
        """Test detection of cease and desist objections."""
        transcript = "Stop calling me. This is harassment. Do not contact me again. Cease and desist."
        result = extract_objections(transcript)

        assert result["primary_objection"] == "REFUSES_CONTACT"
        assert "REFUSES_CONTACT" in result["all_objections"]
        assert result["objection_confidence"] > 0.0

    def test_no_objections(self):
        """Test transcript with no objections."""
        transcript = "I will pay the full amount today. Thank you for calling."
        result = extract_objections(transcript)

        assert result["primary_objection"] is None
        assert len(result["all_objections"]) == 0
        assert result["objection_confidence"] == 0.0
        assert result["objection_details"] == "No objections detected"

    def test_multiple_objections(self):
        """Test transcript with multiple objection types."""
        transcript = """
        I lost my job and can't afford this. I also dispute the amount - it's not correct.
        I need you to send me validation of this debt. I might file bankruptcy.
        """
        result = extract_objections(transcript)

        assert result["primary_objection"] is not None
        assert len(result["all_objections"]) > 1
        # Should detect multiple: FINANCIAL_HARDSHIP, DISPUTE_DEBT, REQUEST_VALIDATION, BANKRUPTCY

    def test_objection_confidence_scoring(self):
        """Test confidence scoring with varying match counts."""
        # Strong single objection (multiple keywords)
        strong = "I lost my job, I'm unemployed, and have no income due to financial hardship."
        result_strong = extract_objections(strong)

        # Weak single mention
        weak = "I mentioned financial issues briefly."
        result_weak = extract_objections(weak)

        # Strong should have higher confidence than weak
        # (This is approximate since confidence calculation is heuristic)
        assert result_strong["objection_confidence"] >= result_weak.get("objection_confidence", 0.0)

    def test_with_transcript_summary(self):
        """Test objection extraction using both transcript and summary."""
        transcript = "Had a conversation about payment issues."
        summary = "Debtor reported job loss and requested payment plan."

        result = extract_objections(transcript, summary)

        # Should detect objections from summary even if transcript is vague
        assert result["primary_objection"] is not None
        assert len(result["all_objections"]) > 0


class TestObjectionDescriptions:
    """Test objection description helper."""

    def test_all_categories_have_descriptions(self):
        """Test that all objection categories have descriptions."""
        categories = [
            "FINANCIAL_HARDSHIP",
            "DISPUTE_DEBT",
            "REQUEST_VALIDATION",
            "PAYMENT_PLAN",
            "INSUFFICIENT_FUNDS",
            "MEDICAL_EMERGENCY",
            "ATTORNEY_REPRESENTATION",
            "BANKRUPTCY",
            "REFUSES_CONTACT",
            "OTHER",
        ]

        for category in categories:
            desc = get_objection_description(category)
            assert desc is not None
            assert len(desc) > 0
            assert desc != "Unknown objection"

    def test_unknown_category(self):
        """Test handling of unknown category."""
        desc = get_objection_description("UNKNOWN_CATEGORY")
        assert desc == "Unknown objection"


class TestObjectionTrendsAnalysis:
    """Test objection trend analysis across calls."""

    def test_analyze_trends_with_data(self, db_session):
        """Test objection trends with actual call data."""
        now = datetime.now()

        # Create test calls with various objections
        objections = [
            "FINANCIAL_HARDSHIP",
            "FINANCIAL_HARDSHIP",
            "FINANCIAL_HARDSHIP",
            "DISPUTE_DEBT",
            "DISPUTE_DEBT",
            "PAYMENT_PLAN",
            None,  # No objection
        ]

        for i, objection in enumerate(objections):
            call = CallRecord(
                dealer_id=f"DLR-OBJ-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.5,
                primary_objection=objection,
                objection_confidence=0.7 if objection else None,
            )
            db_session.add(call)
        db_session.commit()

        result = analyze_objection_trends(db_session, days=7)

        assert result["total_calls_with_objections"] == 6
        assert result["time_period_days"] == 7
        assert len(result["top_objections"]) > 0

        # FINANCIAL_HARDSHIP should be the top objection (3 occurrences)
        top_objection = result["top_objections"][0]
        assert top_objection["category"] == "FINANCIAL_HARDSHIP"
        assert top_objection["count"] == 3
        assert top_objection["percentage"] == 50.0  # 3/6 = 50%

    def test_analyze_trends_no_data(self, db_session):
        """Test objection trends with no call data."""
        result = analyze_objection_trends(db_session, days=7)

        assert result["total_calls_with_objections"] == 0
        assert result["time_period_days"] == 7
        assert len(result["top_objections"]) == 0
        assert result["objection_distribution"] == {}

    def test_analyze_trends_time_window(self, db_session):
        """Test that objection trends respect the time window."""
        now = datetime.now()

        # Create calls: some within window, some outside
        for i in range(5):
            call = CallRecord(
                dealer_id=f"DLR-TIME-{i}",
                call_timestamp=now - timedelta(days=i * 3),  # 0, 3, 6, 9, 12 days ago
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.5,
                primary_objection="DISPUTE_DEBT",
                objection_confidence=0.7,
            )
            db_session.add(call)
        db_session.commit()

        # Only calls within 7 days should be counted (0, 3, 6 days ago = 3 calls)
        result = analyze_objection_trends(db_session, days=7)

        assert result["total_calls_with_objections"] == 3
        assert result["objection_distribution"]["DISPUTE_DEBT"] == 3


class TestObjectionEdgeCases:
    """Test edge cases and special scenarios."""

    def test_case_insensitive_matching(self):
        """Test that objection detection is case-insensitive."""
        transcript_upper = "I LOST MY JOB AND CAN'T PAY"
        transcript_lower = "i lost my job and can't pay"
        transcript_mixed = "I Lost My Job and Can't Pay"

        result_upper = extract_objections(transcript_upper)
        result_lower = extract_objections(transcript_lower)
        result_mixed = extract_objections(transcript_mixed)

        assert result_upper["primary_objection"] == "FINANCIAL_HARDSHIP"
        assert result_lower["primary_objection"] == "FINANCIAL_HARDSHIP"
        assert result_mixed["primary_objection"] == "FINANCIAL_HARDSHIP"

    def test_empty_transcript(self):
        """Test handling of empty transcript."""
        result = extract_objections("")

        assert result["primary_objection"] is None
        assert len(result["all_objections"]) == 0
        assert result["objection_confidence"] == 0.0

    def test_very_long_transcript(self):
        """Test handling of very long transcripts."""
        # Create a long transcript with multiple keyword repetitions
        long_transcript = "I lost my job. " * 100 + "I'm unemployed. " * 100

        result = extract_objections(long_transcript)

        assert result["primary_objection"] == "FINANCIAL_HARDSHIP"
        # Confidence should still be reasonable (capped at 1.0)
        assert 0.0 <= result["objection_confidence"] <= 1.0
