"""
Seed script – ingests 10 varied sample calls through the full pipeline
to populate the database with demo data.

Usage:  python seed.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database.database import engine, Base, SessionLocal
from models.schemas import CallRecordCreate
from preprocessor.preprocessor import run_pipeline
from services.compliance_service import check_compliance
from services.metadata_service import enrich_metadata
from services.tm_service import classify_intent
from services.decision_service import make_decision
import crud

Base.metadata.create_all(bind=engine)

SAMPLE_CALLS = [
    {
        "dealer_id": "DLR-00421",
        "name": "Jane Smith",
        "phone": "555-867-5309",
        "transcript": "Agent greeted the debtor Jane Smith. Debtor acknowledged the outstanding balance of $4,200. Debtor stated they will pay $500 by end of month. Agent confirmed the arrangement and reminded of next steps.",
        "duration": 372,
        "timestamp": "2026-03-12T14:30:00",
        "past_due": 45,
        "outstanding_amount": 4200.00,
        "promise_amount": 500.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.72",
    },
    {
        "dealer_id": "DLR-00533",
        "name": "John Doe",
        "transcript": "Agent contacted John Doe regarding past-due balance. Debtor said they refuse to pay anything and hung up abruptly.",
        "duration": 98,
        "timestamp": "2026-03-11T09:15:00",
        "past_due": 92,
        "outstanding_amount": 8750.00,
        "promise_amount": 0.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.15",
    },
    {
        "dealer_id": "DLR-00612",
        "transcript": "Debtor disputed the account balance claiming they already paid in full. Requested documentation and escalation to a manager.",
        "duration": 540,
        "timestamp": "2026-03-10T11:00:00",
        "past_due": 30,
        "outstanding_amount": 2100.00,
        "promise_amount": 0.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": True,
        "sentiment_raw": "0.30",
    },
    {
        "dealer_id": "DLR-00421",
        "transcript": "Follow-up call with debtor. Debtor confirmed previous arrangement and stated they will pay $500 as promised. Payment expected by Friday.",
        "duration": 180,
        "timestamp": "2026-03-13T10:45:00",
        "past_due": 46,
        "outstanding_amount": 4200.00,
        "promise_amount": 500.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.80",
    },
    {
        "dealer_id": "DLR-00789",
        "transcript": "Agent called debtor after hours. Debtor was upset about the late call. Debtor said maybe they can send something next week if they get paid.",
        "duration": 210,
        "timestamp": "2026-03-09T22:30:00",
        "past_due": 15,
        "outstanding_amount": 1500.00,
        "promise_amount": 200.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.35",
    },
    {
        "dealer_id": "DLR-00855",
        "transcript": "Debtor said they might consider making a partial payment if the interest is waived. Agent explained options.",
        "duration": 420,
        "timestamp": "2026-03-12T16:00:00",
        "past_due": 60,
        "outstanding_amount": 6300.00,
        "promise_amount": 1000.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.55",
    },
    {
        "dealer_id": "DLR-00901",
        "transcript": "Debtor stated they cannot pay due to job loss. No money available. Agent offered hardship program information.",
        "duration": 300,
        "timestamp": "2026-03-11T15:30:00",
        "past_due": 120,
        "outstanding_amount": 12000.00,
        "promise_amount": 0.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.20",
    },
    {
        "dealer_id": "DLR-00102",
        "transcript": "New account contact. Debtor was cooperative and agreed to a payment plan. They will pay the full balance of $800 by end of week.",
        "duration": 150,
        "timestamp": "2026-03-13T08:30:00",
        "past_due": 5,
        "outstanding_amount": 800.00,
        "promise_amount": 800.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.90",
    },
    {
        "dealer_id": "DLR-00533",
        "transcript": "Second attempt to reach debtor. Debtor answered but said won't discuss anything and disconnected.",
        "duration": 45,
        "timestamp": "2026-03-12T13:00:00",
        "past_due": 93,
        "outstanding_amount": 8750.00,
        "promise_amount": 0.00,
        "compliance_flags": "",
        "dispute_flag": False,
        "sentiment_raw": "0.10",
    },
    {
        "dealer_id": "DLR-00670",
        "transcript": "Debtor acknowledged debt and said they possibly can arrange a payment next month depending on their bonus. Promised to call back.",
        "duration": 260,
        "timestamp": "2026-03-10T17:45:00",
        "past_due": 75,
        "outstanding_amount": 5500.00,
        "promise_amount": 1500.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.50",
    },
]


def seed():
    db = SessionLocal()
    try:
        for i, raw in enumerate(SAMPLE_CALLS, 1):
            processed = run_pipeline(raw)
            cleaned_transcript = processed.pop("_cleaned_transcript", "")
            compliance = check_compliance(processed)
            metadata = enrich_metadata(processed)
            intent = classify_intent(cleaned_transcript or processed.get("transcript_summary", ""))
            enriched = {**processed, **compliance, **metadata, **intent}
            decision = make_decision(enriched)
            full_record = {**enriched, **decision}

            validated = CallRecordCreate(**full_record)
            record = crud.create_record(db, validated.model_dump())
            print(
                f"  [{i:2d}] id={record.id} dealer={record.dealer_id} "
                f"intent={record.intent_class} compliance={record.compliance_status} "
                f"action={record.next_action}"
            )
        print(f"\nSeeded {len(SAMPLE_CALLS)} call records successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding Marco database...\n")
    seed()
