"""
SQLAlchemy ORM model – maps to the call_records table in SQLite.
Every column stores one enriched pipeline output per ingested call.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Index
from database.database import Base


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dealer_id = Column(String, index=True)
    transcript_summary = Column(String)
    sentiment_score = Column(Float)
    call_outcome = Column(String)
    call_timestamp = Column(DateTime, index=True)
    days_past_due = Column(Integer)
    debt_balance = Column(Float)
    promise_amount = Column(Float)
    compliance_status = Column(String, index=True)
    compliance_violations = Column(String)  # Comma-separated violation codes
    compliance_details = Column(String)
    promise_coverage_ratio = Column(Float)
    delta_aging_bucket = Column(String)
    call_duration_minutes = Column(Float)
    time_of_day_category = Column(String)
    intent_class = Column(String, index=True)
    confidence = Column(Float)
    next_action = Column(String)
    decision_rationale = Column(String)
    dispute_flag = Column(Boolean, default=False)
    fulfillment_probability = Column(Float)
    primary_objection = Column(String, index=True)  # Main objection category
    all_objections = Column(String)  # Comma-separated list of all objections
    objection_details = Column(String)
    objection_confidence = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
