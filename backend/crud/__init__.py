"""
CRUD operations for the call_records table.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import CallRecord


def create_record(db: Session, data: dict) -> CallRecord:
    """Insert a fully-enriched call record into the database."""
    record = CallRecord(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_all_records(db: Session, skip: int = 0, limit: int = 20) -> list[CallRecord]:
    """Return paginated call records."""
    return db.query(CallRecord).offset(skip).limit(limit).all()


def get_dashboard_kpis(db: Session) -> dict:
    """Compute aggregate KPIs for the dashboard."""
    total = db.query(func.count(CallRecord.id)).scalar() or 0
    avg_sentiment = db.query(func.avg(CallRecord.sentiment_score)).scalar() or 0.0
    avg_promise = db.query(func.avg(CallRecord.promise_coverage_ratio)).scalar() or 0.0

    committed_count = (
        db.query(func.count(CallRecord.id))
        .filter(CallRecord.compliance_status == "PASS")
        .scalar()
        or 0
    )
    compliance_pass_rate = (committed_count / total) if total > 0 else 0.0

    # Intent distribution
    intent_rows = (
        db.query(CallRecord.intent_class, func.count(CallRecord.id))
        .group_by(CallRecord.intent_class)
        .all()
    )
    intent_distribution = {row[0]: row[1] for row in intent_rows}

    return {
        "total_calls": total,
        "avg_sentiment": round(float(avg_sentiment), 4),
        "avg_promise_coverage": round(float(avg_promise), 4),
        "compliance_pass_rate": round(float(compliance_pass_rate), 4),
        "intent_distribution": intent_distribution,
    }
