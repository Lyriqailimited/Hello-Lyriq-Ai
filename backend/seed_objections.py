"""
Seed script to populate database with random objection test data.

Generates call records with various objection types to test objections endpoints:
- FINANCIAL_HARDSHIP
- DISPUTE_DEBT
- REQUEST_VALIDATION
- PAYMENT_PLAN
- INSUFFICIENT_FUNDS
- MEDICAL_EMERGENCY
- ATTORNEY_REPRESENTATION
- BANKRUPTCY
- REFUSES_CONTACT
- OTHER

Usage: python seed_objections.py [--count N]
"""

import sys
import os
import random
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from database.database import engine, Base, SessionLocal
from models.schemas import CallRecordCreate
from preprocessor.preprocessor import run_pipeline
from services.compliance_service import check_compliance
from services.metadata_service import enrich_metadata
from services.tm_service import classify_intent
from services.decision_service import make_decision
from services.objection_service import extract_objections
import crud

Base.metadata.create_all(bind=engine)

# Objection categories and sample transcripts
OBJECTION_TEMPLATES = {
    "FINANCIAL_HARDSHIP": [
        "I lost my job last month and can't afford to pay right now. I'm on unemployment benefits.",
        "I've been laid off recently due to company downsizing. I have no income currently.",
        "My hours were cut drastically and I can barely make rent. I have financial hardship.",
        "I'm unemployed and struggling to pay bills. Can we work something out?",
        "I lost my job and have no money coming in. I'm experiencing severe financial difficulties.",
    ],
    "DISPUTE_DEBT": [
        "I don't owe this debt. This is not my account. I already paid this off last year.",
        "This debt isn't mine. I never opened this account. You have the wrong person.",
        "I dispute this entire balance. The amount is completely incorrect.",
        "I already paid this debt in full. Your records are wrong.",
        "This is fraudulent. I never authorized these charges. I dispute everything.",
    ],
    "REQUEST_VALIDATION": [
        "I need you to prove this debt. Send me written proof and validation documentation.",
        "Please send me validation of this debt. I want to see all the paperwork.",
        "I'm requesting debt validation. Send me everything in writing.",
        "Prove this debt is mine. I want all documentation sent to me by mail.",
        "I need written validation of this account before I discuss any payment.",
    ],
    "PAYMENT_PLAN": [
        "Can we set up a payment plan? I can pay $100 monthly. Let's negotiate a settlement.",
        "I'd like to arrange a payment plan. What are my options for monthly payments?",
        "Can we negotiate a settlement? I can pay 50% if you waive the rest.",
        "I want to set up monthly payments. What's the minimum I can pay each month?",
        "Let's work out a payment arrangement. I can start with small payments.",
    ],
    "INSUFFICIENT_FUNDS": [
        "I don't have money right now. I'm waiting for my paycheck next week.",
        "I don't have the funds available today. Can I call you back on Friday?",
        "My bank account is empty right now. I get paid on the 15th.",
        "I don't have enough money to pay this. Maybe next month when I get my check.",
        "I'm broke right now. I have no money until my next paycheck arrives.",
    ],
    "MEDICAL_EMERGENCY": [
        "I had a medical emergency and have huge hospital bills from my surgery.",
        "I've been dealing with a serious illness and massive medical expenses.",
        "I was hospitalized last month and my medical bills are overwhelming.",
        "I had emergency surgery and can't afford anything right now due to medical costs.",
        "My spouse had a medical emergency. All our money is going to medical bills.",
    ],
    "ATTORNEY_REPRESENTATION": [
        "I have an attorney. Please talk to my lawyer. I'm legally represented.",
        "Contact my attorney. I'm represented by counsel. Do not call me directly.",
        "My lawyer handles all my debts. You need to speak with them, not me.",
        "I have legal representation. All communication should go through my attorney.",
        "Talk to my lawyer. I'm not discussing this without my attorney present.",
    ],
    "BANKRUPTCY": [
        "I filed for Chapter 7 bankruptcy last month. This debt was discharged.",
        "I'm in the middle of bankruptcy proceedings. You shouldn't be calling me.",
        "I filed Chapter 13 bankruptcy. This debt is included in my bankruptcy plan.",
        "This was discharged in bankruptcy. I filed last year and this was included.",
        "I'm under bankruptcy protection. You need to contact my bankruptcy trustee.",
    ],
    "REFUSES_CONTACT": [
        "Stop calling me. This is harassment. Do not contact me again. Cease and desist.",
        "Do not call me anymore. This is my final warning. Cease all contact.",
        "Stop harassing me with these calls. I demand you cease and desist immediately.",
        "Remove me from your call list. Do not contact me by phone ever again.",
        "This is harassment. Stop calling or I'll report you. Cease all communication.",
    ],
    "OTHER": [
        "I'm dealing with a family emergency right now. Can't discuss this.",
        "I'm going through a divorce and everything is complicated right now.",
        "My identity was stolen. I think this might be related to that.",
        "I'm out of the country for the next six months. Can't handle this now.",
        "I don't understand what this debt is for. Can you explain it better?",
    ],
    None: [  # No objection
        "Yes, I acknowledge the debt. I'll pay the full amount today by card.",
        "I understand. Let me make a payment right now. I have my card ready.",
        "Thanks for calling. I'll pay this off in full by end of business today.",
        "Okay, I'll take care of this immediately. Processing payment now.",
        "Confirmed. I'll make the full payment within the next hour.",
    ],
}

# Random debtor names
FIRST_NAMES = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
               "James", "Maria", "William", "Jennifer", "Richard", "Jessica", "Thomas"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
              "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor"]

def generate_random_call(index, days_ago=None):
    """Generate a random call record with objection data."""

    # Random objection type (60% have objections, 40% have none)
    objection_type = random.choice(
        list(OBJECTION_TEMPLATES.keys()) * 3 + [None] * 2
    )

    # Random transcript from templates
    transcript = random.choice(OBJECTION_TEMPLATES[objection_type])

    # Random debtor info
    dealer_id = f"DLR-{random.randint(1000, 9999)}"
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

    # Random financial data
    outstanding_amount = round(random.uniform(500, 15000), 2)
    past_due = random.randint(5, 180)

    # Promise amount based on objection type
    if objection_type in [None, "PAYMENT_PLAN"]:
        promise_amount = round(random.uniform(100, outstanding_amount), 2)
    else:
        promise_amount = 0.0

    # Sentiment based on objection type
    if objection_type in ["REFUSES_CONTACT", "BANKRUPTCY", "ATTORNEY_REPRESENTATION"]:
        sentiment = random.uniform(0.05, 0.25)
    elif objection_type in ["DISPUTE_DEBT", "MEDICAL_EMERGENCY"]:
        sentiment = random.uniform(0.2, 0.4)
    elif objection_type in ["PAYMENT_PLAN", "INSUFFICIENT_FUNDS"]:
        sentiment = random.uniform(0.4, 0.7)
    elif objection_type is None:
        sentiment = random.uniform(0.7, 0.95)
    else:
        sentiment = random.uniform(0.3, 0.6)

    # Random call metadata
    duration = random.randint(30, 600)

    # Timestamp distribution (ensure reasonable call hours 8am-8pm)
    if days_ago is None:
        days_ago = random.randint(0, 30)

    base_date = datetime.now() - timedelta(days=days_ago)
    # Set to a specific hour between 8am-8pm (20:00)
    call_hour = random.randint(8, 20)
    call_minute = random.randint(0, 59)
    timestamp = base_date.replace(hour=call_hour, minute=call_minute, second=0, microsecond=0)

    # Dispute flag based on objection type
    dispute_flag = objection_type in ["DISPUTE_DEBT", "REQUEST_VALIDATION"]

    return {
        "dealer_id": dealer_id,
        "name": name,
        "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        "transcript": transcript,
        "duration": duration,
        "timestamp": timestamp.isoformat(),
        "past_due": past_due,
        "outstanding_amount": outstanding_amount,
        "promise_amount": promise_amount,
        "compliance_flags": "TCPA_OK" if random.random() > 0.1 else "",
        "dispute_flag": dispute_flag,
        "sentiment_raw": str(sentiment),
        "_objection_type": objection_type,  # For tracking
    }


def seed_objections(count=50):
    """Seed database with random objection test data."""
    db = SessionLocal()
    try:
        print(f"Generating {count} random call records with objections...\n")

        objection_counts = {}

        for i in range(count):
            raw = generate_random_call(i)
            objection_type = raw.pop("_objection_type", None)

            # Track objection distribution
            objection_counts[objection_type] = objection_counts.get(objection_type, 0) + 1

            # Process through pipeline
            processed = run_pipeline(raw)
            cleaned_transcript = processed.pop("_cleaned_transcript", "")

            # Add compliance check
            compliance = check_compliance(processed)

            # Add metadata enrichment
            metadata = enrich_metadata(processed)

            # Classify intent
            intent = classify_intent(cleaned_transcript or processed.get("transcript_summary", ""))

            # Extract objections
            objections = extract_objections(
                cleaned_transcript or processed.get("transcript_summary", ""),
                processed.get("transcript_summary", "")
            )

            # Combine all enriched data
            enriched = {**processed, **compliance, **metadata, **intent, **objections}

            # Make decision
            decision = make_decision(enriched)

            # Create full record
            full_record = {**enriched, **decision}

            # Convert list fields to comma-separated strings for database
            if isinstance(full_record.get("compliance_violations"), list):
                full_record["compliance_violations"] = ",".join(full_record["compliance_violations"])
            if isinstance(full_record.get("all_objections"), list):
                full_record["all_objections"] = ",".join(full_record["all_objections"])

            # Save to database
            validated = CallRecordCreate(**full_record)
            record = crud.create_record(db, validated.model_dump())

            print(
                f"  [{i+1:3d}] id={record.id} dealer={record.dealer_id} "
                f"objection={record.primary_objection or 'NONE':25s} "
                f"confidence={record.objection_confidence or 0:.2f}"
            )

        print(f"\n{'='*60}")
        print("Objection Distribution:")
        print(f"{'='*60}")
        for obj_type, obj_count in sorted(objection_counts.items(),
                                          key=lambda x: x[1], reverse=True):
            obj_label = obj_type or "NO_OBJECTION"
            percentage = (obj_count / count) * 100
            print(f"  {obj_label:25s}: {obj_count:3d} ({percentage:5.1f}%)")

        print(f"\n✓ Successfully seeded {count} call records with objection data.")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Seed database with random objection test data"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of random call records to generate (default: 50)"
    )
    args = parser.parse_args()

    print("="*60)
    print("Marco Database - Objections Test Data Seeder")
    print("="*60)
    print()

    seed_objections(args.count)


if __name__ == "__main__":
    main()
