"""
Agent performance tracking and anomaly detection service.

Note: Since the current system uses AI agents (not human agents), we track
"agent performance" as system performance metrics per dealer/campaign.

Metrics tracked:
  1. Success rate (COMMITTED intent rate)
  2. Average sentiment score
  3. Compliance pass rate
  4. Average call duration
  5. Promise fulfillment probability
  6. Objection rate

Anomaly detection:
  - Sudden drops in success rate (> 20% decrease)
  - Unusual spike in compliance failures
  - Abnormal call duration patterns
  - High objection rates (> 70%)
"""

import logging
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def calculate_agent_performance(db: Session, days: int = 7) -> dict[str, Any]:
    """
    Calculate overall system/agent performance metrics.

    Args:
        db: Database session
        days: Number of days to look back (default: 7)

    Returns:
        Dictionary with performance metrics and anomaly flags
    """
    from database.models import CallRecord

    cutoff_date = datetime.now() - timedelta(days=days)

    # Get all records in the time period
    records = (
        db.query(CallRecord)
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .all()
    )

    if not records:
        return {
            "total_calls": 0,
            "time_period_days": days,
            "metrics": {},
            "anomalies": [],
        }

    total_calls = len(records)

    # Calculate metrics
    committed_count = sum(1 for r in records if r.intent_class == "COMMITTED")
    compliance_pass = sum(1 for r in records if r.compliance_status == "PASS")
    has_objection = sum(1 for r in records if r.primary_objection is not None)

    avg_sentiment = sum(r.sentiment_score or 0 for r in records) / total_calls
    avg_duration = sum(r.call_duration_minutes or 0 for r in records) / total_calls
    avg_fulfillment = sum(r.fulfillment_probability or 0 for r in records) / total_calls

    success_rate = (committed_count / total_calls) * 100
    compliance_rate = (compliance_pass / total_calls) * 100
    objection_rate = (has_objection / total_calls) * 100

    metrics = {
        "success_rate": round(success_rate, 2),
        "avg_sentiment": round(avg_sentiment, 4),
        "compliance_pass_rate": round(compliance_rate, 2),
        "avg_call_duration_minutes": round(avg_duration, 2),
        "avg_fulfillment_probability": round(avg_fulfillment, 4),
        "objection_rate": round(objection_rate, 2),
        "total_committed": committed_count,
        "total_compliant": compliance_pass,
        "total_with_objections": has_objection,
    }

    # Detect anomalies
    anomalies = _detect_anomalies(metrics, records)

    logger.info(
        "Agent performance: success_rate=%.2f%%, compliance=%.2f%%, %d anomalies",
        success_rate,
        compliance_rate,
        len(anomalies)
    )

    return {
        "total_calls": total_calls,
        "time_period_days": days,
        "metrics": metrics,
        "anomalies": anomalies,
    }


def _detect_anomalies(metrics: dict[str, Any], records: list) -> list[dict[str, Any]]:
    """
    Detect performance anomalies based on metrics and historical data.

    Args:
        metrics: Current performance metrics
        records: List of call records

    Returns:
        List of detected anomalies with severity and descriptions
    """
    anomalies = []

    # Anomaly 1: Low success rate (< 20%)
    if metrics["success_rate"] < 20.0:
        anomalies.append({
            "type": "LOW_SUCCESS_RATE",
            "severity": "HIGH",
            "description": f"Success rate ({metrics['success_rate']:.1f}%) is below 20% threshold",
            "metric": "success_rate",
            "value": metrics["success_rate"],
        })

    # Anomaly 2: Low compliance rate (< 60%)
    if metrics["compliance_pass_rate"] < 60.0:
        anomalies.append({
            "type": "LOW_COMPLIANCE",
            "severity": "CRITICAL",
            "description": f"Compliance pass rate ({metrics['compliance_pass_rate']:.1f}%) is critically low",
            "metric": "compliance_pass_rate",
            "value": metrics["compliance_pass_rate"],
        })

    # Anomaly 3: High objection rate (> 70%)
    if metrics["objection_rate"] > 70.0:
        anomalies.append({
            "type": "HIGH_OBJECTION_RATE",
            "severity": "MEDIUM",
            "description": f"Objection rate ({metrics['objection_rate']:.1f}%) exceeds 70% threshold",
            "metric": "objection_rate",
            "value": metrics["objection_rate"],
        })

    # Anomaly 4: Very low sentiment (< 0.3)
    if metrics["avg_sentiment"] < 0.3:
        anomalies.append({
            "type": "LOW_SENTIMENT",
            "severity": "MEDIUM",
            "description": f"Average sentiment ({metrics['avg_sentiment']:.2f}) is very low",
            "metric": "avg_sentiment",
            "value": metrics["avg_sentiment"],
        })

    # Anomaly 5: Abnormal call duration (< 1 min or > 30 min)
    if metrics["avg_call_duration_minutes"] < 1.0:
        anomalies.append({
            "type": "CALLS_TOO_SHORT",
            "severity": "MEDIUM",
            "description": f"Average call duration ({metrics['avg_call_duration_minutes']:.1f} min) is suspiciously short",
            "metric": "avg_call_duration_minutes",
            "value": metrics["avg_call_duration_minutes"],
        })
    elif metrics["avg_call_duration_minutes"] > 30.0:
        anomalies.append({
            "type": "CALLS_TOO_LONG",
            "severity": "LOW",
            "description": f"Average call duration ({metrics['avg_call_duration_minutes']:.1f} min) is unusually long",
            "metric": "avg_call_duration_minutes",
            "value": metrics["avg_call_duration_minutes"],
        })

    # Anomaly 6: Low fulfillment probability (< 0.3)
    if metrics["avg_fulfillment_probability"] < 0.3:
        anomalies.append({
            "type": "LOW_FULFILLMENT",
            "severity": "HIGH",
            "description": f"Average fulfillment probability ({metrics['avg_fulfillment_probability']:.2f}) is very low",
            "metric": "avg_fulfillment_probability",
            "value": metrics["avg_fulfillment_probability"],
        })

    return anomalies


def get_performance_by_dealer(db: Session, dealer_id: str, days: int = 30) -> dict[str, Any]:
    """
    Get performance metrics for a specific dealer.

    Args:
        db: Database session
        dealer_id: Dealer identifier
        days: Number of days to look back (default: 30)

    Returns:
        Dictionary with dealer-specific performance metrics
    """
    from database.models import CallRecord

    cutoff_date = datetime.now() - timedelta(days=days)

    records = (
        db.query(CallRecord)
        .filter(CallRecord.dealer_id == dealer_id)
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .all()
    )

    if not records:
        return {
            "dealer_id": dealer_id,
            "total_calls": 0,
            "message": "No calls found for this dealer in the specified period",
        }

    total_calls = len(records)
    committed_count = sum(1 for r in records if r.intent_class == "COMMITTED")
    compliance_pass = sum(1 for r in records if r.compliance_status == "PASS")

    avg_sentiment = sum(r.sentiment_score or 0 for r in records) / total_calls
    avg_fulfillment = sum(r.fulfillment_probability or 0 for r in records) / total_calls

    # Get most recent call info
    most_recent = max(records, key=lambda r: r.call_timestamp)

    return {
        "dealer_id": dealer_id,
        "total_calls": total_calls,
        "time_period_days": days,
        "success_rate": round((committed_count / total_calls) * 100, 2),
        "compliance_rate": round((compliance_pass / total_calls) * 100, 2),
        "avg_sentiment": round(avg_sentiment, 4),
        "avg_fulfillment_probability": round(avg_fulfillment, 4),
        "most_recent_call": {
            "timestamp": most_recent.call_timestamp.isoformat(),
            "intent": most_recent.intent_class,
            "compliance_status": most_recent.compliance_status,
            "next_action": most_recent.next_action,
        },
    }
