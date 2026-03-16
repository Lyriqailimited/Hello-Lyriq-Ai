"""
Analytics API endpoints.

Provides advanced analytics for:
  - Objection trends and distribution
  - Agent/system performance metrics
  - Compliance violation analysis
  - Call outcome patterns
  - Dealer-specific insights
"""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database.database import get_db
from services.objection_service import analyze_objection_trends, get_objection_description
from services.agent_performance_service import (
    calculate_agent_performance,
    get_performance_by_dealer
)
from database.models import CallRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/objections")
def get_objection_analytics(
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get objection trends and distribution across all calls.

    Returns top objections with counts, percentages, and descriptions.
    """
    result = analyze_objection_trends(db, days=days)
    logger.info("Objection analytics requested for past %d days", days)
    return result


@router.get("/objections/{category}")
def get_objection_details(
    category: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific objection category.

    Returns all calls with the specified objection type and related metrics.
    """
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    calls = (
        db.query(CallRecord)
        .filter(CallRecord.primary_objection == category.upper())
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .all()
    )

    if not calls:
        return {
            "category": category.upper(),
            "description": get_objection_description(category.upper()),
            "total_calls": 0,
            "calls": [],
        }

    # Calculate metrics for calls with this objection
    total = len(calls)
    avg_sentiment = sum(c.sentiment_score or 0 for c in calls) / total
    avg_fulfillment = sum(c.fulfillment_probability or 0 for c in calls) / total
    committed_count = sum(1 for c in calls if c.intent_class == "COMMITTED")

    call_details = [
        {
            "id": c.id,
            "dealer_id": c.dealer_id,
            "timestamp": c.call_timestamp.isoformat(),
            "intent": c.intent_class,
            "sentiment": c.sentiment_score,
            "compliance_status": c.compliance_status,
            "next_action": c.next_action,
        }
        for c in calls[:20]  # Limit to first 20 for performance
    ]

    return {
        "category": category.upper(),
        "description": get_objection_description(category.upper()),
        "total_calls": total,
        "time_period_days": days,
        "metrics": {
            "avg_sentiment": round(avg_sentiment, 4),
            "avg_fulfillment_probability": round(avg_fulfillment, 4),
            "success_rate": round((committed_count / total) * 100, 2),
        },
        "calls": call_details,
    }


@router.get("/performance")
def get_performance_metrics(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get overall system/agent performance metrics with anomaly detection.

    Returns success rates, compliance rates, and performance anomalies.
    """
    result = calculate_agent_performance(db, days=days)
    logger.info(
        "Performance analytics: %d calls, %d anomalies detected",
        result.get("total_calls", 0),
        len(result.get("anomalies", []))
    )
    return result


@router.get("/performance/dealer/{dealer_id}")
def get_dealer_performance(
    dealer_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for a specific dealer.

    Returns dealer-specific success rates, compliance, and call history.
    """
    result = get_performance_by_dealer(db, dealer_id=dealer_id, days=days)
    logger.info("Dealer performance requested: dealer=%s", dealer_id)
    return result


@router.get("/compliance/violations")
def get_compliance_violations(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get all compliance violations with details.

    Returns calls with compliance failures, violation codes, and details.
    """
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    violations = (
        db.query(CallRecord)
        .filter(CallRecord.compliance_status == "FAIL")
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .order_by(CallRecord.call_timestamp.desc())
        .limit(limit)
        .all()
    )

    # Count violations by type
    violation_counts = {}
    for call in violations:
        if call.compliance_violations:
            for code in call.compliance_violations.split(","):
                violation_counts[code] = violation_counts.get(code, 0) + 1

    violation_details = [
        {
            "id": c.id,
            "dealer_id": c.dealer_id,
            "timestamp": c.call_timestamp.isoformat(),
            "violations": c.compliance_violations.split(",") if c.compliance_violations else [],
            "details": c.compliance_details,
            "call_duration": c.call_duration_minutes,
            "days_past_due": c.days_past_due,
        }
        for c in violations
    ]

    logger.info(
        "Compliance violations: %d total violations in past %d days",
        len(violations),
        days
    )

    return {
        "total_violations": len(violations),
        "time_period_days": days,
        "violation_distribution": violation_counts,
        "violations": violation_details,
    }


@router.get("/outcomes")
def get_outcome_distribution(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get distribution of call outcomes and next actions.

    Returns counts and percentages for each outcome type.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func

    cutoff_date = datetime.now() - timedelta(days=days)

    # Intent distribution
    intent_dist = (
        db.query(CallRecord.intent_class, func.count(CallRecord.id))
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .group_by(CallRecord.intent_class)
        .all()
    )

    # Next action distribution
    action_dist = (
        db.query(CallRecord.next_action, func.count(CallRecord.id))
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .group_by(CallRecord.next_action)
        .all()
    )

    # Call outcome distribution
    outcome_dist = (
        db.query(CallRecord.call_outcome, func.count(CallRecord.id))
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .group_by(CallRecord.call_outcome)
        .all()
    )

    total_calls = (
        db.query(func.count(CallRecord.id))
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .scalar()
    ) or 1

    # Format as percentages
    intent_data = {
        row[0]: {
            "count": row[1],
            "percentage": round((row[1] / total_calls) * 100, 2)
        }
        for row in intent_dist
    }

    action_data = {
        row[0]: {
            "count": row[1],
            "percentage": round((row[1] / total_calls) * 100, 2)
        }
        for row in action_dist
    }

    outcome_data = {
        row[0]: {
            "count": row[1],
            "percentage": round((row[1] / total_calls) * 100, 2)
        }
        for row in outcome_dist
    }

    logger.info("Outcome distribution: %d total calls analyzed", total_calls)

    return {
        "total_calls": total_calls,
        "time_period_days": days,
        "intent_distribution": intent_data,
        "next_action_distribution": action_data,
        "call_outcome_distribution": outcome_data,
    }


@router.get("/trends/daily")
def get_daily_trends(
    days: int = Query(14, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """
    Get daily trends for key metrics over time.

    Returns time-series data for success rate, sentiment, compliance, etc.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, case

    cutoff_date = datetime.now() - timedelta(days=days)

    # Get calls grouped by date
    daily_data = (
        db.query(
            func.date(CallRecord.call_timestamp).label("date"),
            func.count(CallRecord.id).label("total_calls"),
            func.avg(CallRecord.sentiment_score).label("avg_sentiment"),
            func.avg(CallRecord.fulfillment_probability).label("avg_fulfillment"),
            func.sum(
                case((CallRecord.intent_class == "COMMITTED", 1), else_=0)
            ).label("committed_count"),
            func.sum(
                case((CallRecord.compliance_status == "PASS", 1), else_=0)
            ).label("compliant_count"),
        )
        .filter(CallRecord.call_timestamp >= cutoff_date)
        .group_by(func.date(CallRecord.call_timestamp))
        .order_by(func.date(CallRecord.call_timestamp))
        .all()
    )

    trends = [
        {
            "date": str(row.date),
            "total_calls": row.total_calls,
            "avg_sentiment": round(float(row.avg_sentiment or 0), 4),
            "avg_fulfillment_probability": round(float(row.avg_fulfillment or 0), 4),
            "success_rate": round((row.committed_count / row.total_calls) * 100, 2) if row.total_calls > 0 else 0,
            "compliance_rate": round((row.compliant_count / row.total_calls) * 100, 2) if row.total_calls > 0 else 0,
        }
        for row in daily_data
    ]

    logger.info("Daily trends: %d days of data", len(trends))

    return {
        "time_period_days": days,
        "data_points": len(trends),
        "trends": trends,
    }
