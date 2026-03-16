"""
Pydantic v2 schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CallRecordBase(BaseModel):
    """Fields shared between create and read schemas."""

    dealer_id: str
    transcript_summary: str
    sentiment_score: float
    call_outcome: str
    call_timestamp: datetime
    days_past_due: int
    debt_balance: float
    promise_amount: float
    compliance_status: str
    compliance_violations: Optional[str] = None
    compliance_details: Optional[str] = None
    promise_coverage_ratio: float
    delta_aging_bucket: str
    call_duration_minutes: float
    time_of_day_category: str
    intent_class: str
    confidence: float
    next_action: str
    decision_rationale: str
    dispute_flag: bool = False
    fulfillment_probability: Optional[float] = None
    primary_objection: Optional[str] = None
    all_objections: Optional[str] = None
    objection_details: Optional[str] = None
    objection_confidence: Optional[float] = None


class CallRecordCreate(CallRecordBase):
    """Schema used when inserting a new record (no id yet)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dealer_id": "D-7890",
                "transcript_summary": "Customer confirmed they will make the payment of $500 tomorrow morning.",
                "sentiment_score": 0.85,
                "call_outcome": "Promise to Pay",
                "call_timestamp": "2023-11-01T14:30:00Z",
                "days_past_due": 15,
                "debt_balance": 1500.0,
                "promise_amount": 500.0,
                "compliance_status": "Passed",
                "promise_coverage_ratio": 0.33,
                "delta_aging_bucket": "1-30",
                "call_duration_minutes": 4.5,
                "time_of_day_category": "Afternoon",
                "intent_class": "Payment Arrangement",
                "confidence": 0.92,
                "next_action": "Follow up tomorrow",
                "decision_rationale": "Customer explicitly promised to pay a specific amount on a specific date.",
                "dispute_flag": False,
                "fulfillment_probability": 0.80
            }
        }
    )


class CallRecordRead(CallRecordBase):
    """Schema returned from the API (includes the DB-generated id)."""

    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KPISummary(BaseModel):
    """Aggregated dashboard KPIs."""

    total_calls: int
    avg_sentiment: float
    avg_promise_coverage: float
    compliance_pass_rate: float
    intent_distribution: dict[str, int]
