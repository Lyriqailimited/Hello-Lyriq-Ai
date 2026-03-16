"""
Tests for analytics API endpoints.

Tests all analytics endpoints including:
  - Objection analytics
  - Performance metrics
  - Dealer-specific performance
  - Compliance violation reports
  - Outcome distribution
  - Daily trends
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from database.models import CallRecord


class TestObjectionAnalyticsEndpoints:
    """Test objection analytics endpoints."""

    def test_get_objection_analytics(self, client, db_session):
        """Test GET /api/analytics/objections endpoint."""
        # Create test calls with objections
        now = datetime.now()
        objections = ["FINANCIAL_HARDSHIP", "DISPUTE_DEBT", "PAYMENT_PLAN"]

        for i, objection in enumerate(objections):
            call = CallRecord(
                dealer_id=f"DLR-{i}",
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
                objection_confidence=0.7,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/objections?days=7")

        assert response.status_code == 200
        data = response.json()

        assert data["total_calls_with_objections"] == 3
        assert data["time_period_days"] == 7
        assert len(data["top_objections"]) > 0

    def test_get_objection_analytics_custom_days(self, client, db_session):
        """Test objection analytics with custom day range."""
        response = client.get("/api/analytics/objections?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["time_period_days"] == 30

    def test_get_objection_details(self, client, db_session):
        """Test GET /api/analytics/objections/{category} endpoint."""
        # Create test calls with specific objection
        now = datetime.now()

        for i in range(3):
            call = CallRecord(
                dealer_id=f"DLR-DISPUTE-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test dispute",
                sentiment_score=0.3,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="EVASIVE",
                confidence=0.8,
                next_action="ESCALATE",
                decision_rationale="Disputed",
                fulfillment_probability=0.2,
                primary_objection="DISPUTE_DEBT",
                objection_confidence=0.85,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/objections/DISPUTE_DEBT?days=30")

        assert response.status_code == 200
        data = response.json()

        assert data["category"] == "DISPUTE_DEBT"
        assert data["total_calls"] == 3
        assert "metrics" in data
        assert "calls" in data
        assert len(data["calls"]) == 3

    def test_get_objection_details_nonexistent(self, client, db_session):
        """Test objection details for category with no calls."""
        response = client.get("/api/analytics/objections/BANKRUPTCY?days=30")

        assert response.status_code == 200
        data = response.json()

        assert data["category"] == "BANKRUPTCY"
        assert data["total_calls"] == 0
        assert data["calls"] == []


class TestPerformanceAnalyticsEndpoints:
    """Test performance analytics endpoints."""

    def test_get_performance_metrics(self, client, db_session):
        """Test GET /api/analytics/performance endpoint."""
        now = datetime.now()

        # Create diverse test calls
        intents = ["COMMITTED", "COMMITTED", "CONDITIONAL", "EVASIVE"]
        compliance_statuses = ["PASS", "PASS", "PASS", "FAIL"]

        for i, (intent, comp) in enumerate(zip(intents, compliance_statuses)):
            call = CallRecord(
                dealer_id=f"DLR-PERF-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.7 if intent == "COMMITTED" else 0.4,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=500.0,
                compliance_status=comp,
                promise_coverage_ratio=0.5,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class=intent,
                confidence=0.8,
                next_action="SCHEDULE_FOLLOWUP" if intent == "COMMITTED" else "WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.7 if intent == "COMMITTED" else 0.3,
                primary_objection="FINANCIAL_HARDSHIP" if intent == "EVASIVE" else None,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/performance?days=7")

        assert response.status_code == 200
        data = response.json()

        assert data["total_calls"] == 4
        assert "metrics" in data
        assert "anomalies" in data

        metrics = data["metrics"]
        assert "success_rate" in metrics
        assert "compliance_pass_rate" in metrics
        assert "avg_sentiment" in metrics

        # 2 COMMITTED out of 4 = 50% success rate
        assert metrics["success_rate"] == 50.0
        # 3 PASS out of 4 = 75% compliance rate
        assert metrics["compliance_pass_rate"] == 75.0

    def test_get_performance_metrics_with_anomalies(self, client, db_session):
        """Test performance metrics with anomalous data triggering alerts."""
        now = datetime.now()

        # Create calls that should trigger anomalies (all FAIL compliance)
        for i in range(5):
            call = CallRecord(
                dealer_id=f"DLR-ANOM-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.2,  # Very low
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="FAIL",  # All failures
                compliance_violations="TCPA_HOURS",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=0.5,  # Very short
                time_of_day_category="EVENING",
                intent_class="EVASIVE",
                confidence=0.7,
                next_action="ESCALATE",
                decision_rationale="Compliance fail",
                fulfillment_probability=0.1,
                primary_objection="REFUSES_CONTACT",
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/performance?days=7")

        assert response.status_code == 200
        data = response.json()

        # Should have anomalies due to low compliance, low sentiment, etc.
        assert len(data["anomalies"]) > 0

        # Check for specific anomaly types
        anomaly_types = [a["type"] for a in data["anomalies"]]
        assert "LOW_COMPLIANCE" in anomaly_types

    def test_get_dealer_performance(self, client, db_session):
        """Test GET /api/analytics/performance/dealer/{dealer_id} endpoint."""
        dealer_id = "DLR-SPECIFIC-001"
        now = datetime.now()

        # Create calls for specific dealer
        for i in range(3):
            call = CallRecord(
                dealer_id=dealer_id,
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.8,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=500.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.5,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class="COMMITTED",
                confidence=0.9,
                next_action="SCHEDULE_FOLLOWUP",
                decision_rationale="High confidence",
                fulfillment_probability=0.85,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get(f"/api/analytics/performance/dealer/{dealer_id}?days=30")

        assert response.status_code == 200
        data = response.json()

        assert data["dealer_id"] == dealer_id
        assert data["total_calls"] == 3
        assert data["time_period_days"] == 30
        assert data["success_rate"] == 100.0  # All COMMITTED
        assert "most_recent_call" in data

    def test_get_dealer_performance_no_data(self, client):
        """Test dealer performance for dealer with no calls."""
        response = client.get("/api/analytics/performance/dealer/DLR-NONEXISTENT?days=30")

        assert response.status_code == 200
        data = response.json()

        assert data["dealer_id"] == "DLR-NONEXISTENT"
        assert data["total_calls"] == 0
        assert "message" in data


class TestComplianceViolationEndpoints:
    """Test compliance violation analytics endpoints."""

    def test_get_compliance_violations(self, client, db_session):
        """Test GET /api/analytics/compliance/violations endpoint."""
        now = datetime.now()

        # Create calls with various violations
        violations = [
            "TCPA_HOURS",
            "TCPA_HOURS,FDCPA_SUNDAY",
            "MISSING_TCPA_CONSENT",
            "CALL_TOO_SHORT",
        ]

        for i, viol in enumerate(violations):
            call = CallRecord(
                dealer_id=f"DLR-VIOL-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="FAIL",
                compliance_violations=viol,
                compliance_details=f"Violations: {viol}",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=2.0,
                time_of_day_category="EVENING",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Compliance issue",
                fulfillment_probability=0.4,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/compliance/violations?days=7&limit=50")

        assert response.status_code == 200
        data = response.json()

        assert data["total_violations"] == 4
        assert data["time_period_days"] == 7
        assert "violation_distribution" in data
        assert "violations" in data

        # TCPA_HOURS should appear twice in distribution
        assert data["violation_distribution"]["TCPA_HOURS"] == 2

    def test_get_compliance_violations_limit(self, client, db_session):
        """Test compliance violations with result limiting."""
        now = datetime.now()

        # Create more violations than the limit
        for i in range(10):
            call = CallRecord(
                dealer_id=f"DLR-LIMIT-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.5,
                call_outcome="COMPLETED",
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=0.0,
                compliance_status="FAIL",
                compliance_violations="TCPA_HOURS",
                compliance_details="Violation",
                promise_coverage_ratio=0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=2.0,
                time_of_day_category="EVENING",
                intent_class="CONDITIONAL",
                confidence=0.6,
                next_action="WAIT_AND_MONITOR",
                decision_rationale="Test",
                fulfillment_probability=0.4,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/compliance/violations?days=30&limit=5")

        assert response.status_code == 200
        data = response.json()

        # Should return max 5 violations
        assert len(data["violations"]) <= 5


class TestOutcomeDistributionEndpoints:
    """Test outcome distribution endpoints."""

    def test_get_outcome_distribution(self, client, db_session):
        """Test GET /api/analytics/outcomes endpoint."""
        now = datetime.now()

        # Create calls with various outcomes
        data_points = [
            ("COMMITTED", "SCHEDULE_FOLLOWUP", "PROMISE_MADE"),
            ("COMMITTED", "SCHEDULE_FOLLOWUP", "PROMISE_MADE"),
            ("CONDITIONAL", "WAIT_AND_MONITOR", "UNCERTAIN"),
            ("EVASIVE", "ESCALATE", "HUNG_UP"),
        ]

        for i, (intent, action, outcome) in enumerate(data_points):
            call = CallRecord(
                dealer_id=f"DLR-OUTCOME-{i}",
                call_timestamp=now - timedelta(days=i),
                transcript_summary="Test",
                sentiment_score=0.6,
                call_outcome=outcome,
                days_past_due=30,
                debt_balance=1000.0,
                promise_amount=500.0 if intent == "COMMITTED" else 0.0,
                compliance_status="PASS",
                promise_coverage_ratio=0.5 if intent == "COMMITTED" else 0.0,
                delta_aging_bucket="1-30",
                call_duration_minutes=5.0,
                time_of_day_category="AFTERNOON",
                intent_class=intent,
                confidence=0.7,
                next_action=action,
                decision_rationale="Test",
                fulfillment_probability=0.7 if intent == "COMMITTED" else 0.3,
            )
            db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/outcomes?days=7")

        assert response.status_code == 200
        data = response.json()

        assert data["total_calls"] == 4
        assert data["time_period_days"] == 7
        assert "intent_distribution" in data
        assert "next_action_distribution" in data
        assert "call_outcome_distribution" in data

        # Check intent distribution
        intent_dist = data["intent_distribution"]
        assert "COMMITTED" in intent_dist
        assert intent_dist["COMMITTED"]["count"] == 2
        assert intent_dist["COMMITTED"]["percentage"] == 50.0


class TestDailyTrendsEndpoints:
    """Test daily trends endpoints."""

    def test_get_daily_trends(self, client, db_session):
        """Test GET /api/analytics/trends/daily endpoint."""
        now = datetime.now()

        # Create calls across multiple days
        for day in range(7):
            for i in range(2):  # 2 calls per day
                call = CallRecord(
                    dealer_id=f"DLR-TREND-{day}-{i}",
                    call_timestamp=now - timedelta(days=day, hours=i),
                    transcript_summary="Test",
                    sentiment_score=0.6 + (day * 0.05),  # Increasing sentiment
                    call_outcome="COMPLETED",
                    days_past_due=30,
                    debt_balance=1000.0,
                    promise_amount=500.0 if i == 0 else 0.0,
                    compliance_status="PASS" if i == 0 else "FAIL",
                    promise_coverage_ratio=0.5 if i == 0 else 0.0,
                    delta_aging_bucket="1-30",
                    call_duration_minutes=5.0,
                    time_of_day_category="AFTERNOON",
                    intent_class="COMMITTED" if i == 0 else "CONDITIONAL",
                    confidence=0.7,
                    next_action="SCHEDULE_FOLLOWUP" if i == 0 else "WAIT_AND_MONITOR",
                    decision_rationale="Test",
                    fulfillment_probability=0.7 if i == 0 else 0.4,
                )
                db_session.add(call)
        db_session.commit()

        response = client.get("/api/analytics/trends/daily?days=14")

        assert response.status_code == 200
        data = response.json()

        assert data["time_period_days"] == 14
        assert "trends" in data
        assert len(data["trends"]) > 0

        # Each trend point should have required fields
        for trend in data["trends"]:
            assert "date" in trend
            assert "total_calls" in trend
            assert "avg_sentiment" in trend
            assert "avg_fulfillment_probability" in trend
            assert "success_rate" in trend
            assert "compliance_rate" in trend

    def test_get_daily_trends_custom_range(self, client, db_session):
        """Test daily trends with custom day range."""
        response = client.get("/api/analytics/trends/daily?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["time_period_days"] == 30


class TestAnalyticsEdgeCases:
    """Test edge cases and validation."""

    def test_invalid_days_parameter(self, client):
        """Test analytics endpoints with invalid days parameter."""
        # Days too large
        response = client.get("/api/analytics/objections?days=500")
        assert response.status_code == 422  # Validation error

        # Days too small
        response = client.get("/api/analytics/objections?days=0")
        assert response.status_code == 422

    def test_analytics_with_no_data(self, client, db_session):
        """Test analytics endpoints when database is empty."""
        # All analytics endpoints should handle empty data gracefully

        response = client.get("/api/analytics/objections?days=7")
        assert response.status_code == 200
        assert response.json()["total_calls_with_objections"] == 0

        response = client.get("/api/analytics/performance?days=7")
        assert response.status_code == 200
        assert response.json()["total_calls"] == 0

        response = client.get("/api/analytics/outcomes?days=7")
        assert response.status_code == 200
        assert response.json()["total_calls"] == 1  # Minimum to avoid division by zero
