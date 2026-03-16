"""
POST /ingest – accepts a raw call JSON, runs the full enrichment pipeline,
persists the result, and returns the saved record.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.database import get_db
from models.schemas import CallRecordCreate, CallRecordRead
from preprocessor.preprocessor import run_pipeline
from services.compliance_service import check_compliance
from services.metadata_service import enrich_metadata
from services.tm_service import classify_intent
from services.decision_service import make_decision
from services.objection_service import extract_objections
import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ingest"])

_REQUIRED_FIELDS = ["dealer_id", "transcript", "timestamp"]


def _validate_input(raw_body: dict) -> list[str]:
    """Return a list of validation error messages for the raw input."""
    errors = []
    for field in _REQUIRED_FIELDS:
        alt = {"dealer_id": "call_id", "timestamp": "call_timestamp"}.get(field)
        if not raw_body.get(field) and not raw_body.get(alt, ""):
            errors.append(f"Missing required field: '{field}'")

    past_due = raw_body.get("past_due", raw_body.get("days_past_due"))
    if past_due is not None:
        try:
            int(past_due)
        except (ValueError, TypeError):
            errors.append(f"'past_due' must be an integer, got: {past_due!r}")

    outstanding = raw_body.get(
        "outstanding_amount",
        raw_body.get("original_balance", raw_body.get("debt_balance")),
    )
    if outstanding is not None:
        try:
            val = float(outstanding)
            if val < 0:
                errors.append("'outstanding_amount' must be non-negative")
        except (ValueError, TypeError):
            errors.append(f"'outstanding_amount' must be a number, got: {outstanding!r}")

    return errors


from fastapi import APIRouter, Depends, HTTPException, Body

@router.post("/ingest", response_model=CallRecordRead, status_code=201)
def ingest_call(
    raw_body: dict = Body(
        ...,
        json_schema_extra={
            "examples": [
                {
                    "dealer_id": "D-7890",
                    "transcript": "Agent: Hello, this is Marco collections. Am I speaking with John Doe?\nCustomer: Yes, this is John.\nAgent: Great, I'm calling regarding your auto loan which is 15 days past due for $500. Can we set up a payment today?\nCustomer: I get paid tomorrow. I can pay the full $500 then.\nAgent: Perfect, I will schedule that for tomorrow.",
                    "timestamp": "2023-11-01T14:30:00Z",
                    "days_past_due": 15,
                    "debt_balance": 1500.0,
                    "promise_amount": 500.0,
                }
            ]
        }
    ),
    db: Session = Depends(get_db)
):
    """
    Full ingestion pipeline:
    1. Validate raw input fields
    2. Preprocess raw input (clean, summarise, extract metadata)
    3. Run compliance checks
    4. Enrich metadata (aging bucket, duration, time-of-day)
    5. Classify intent
    6. Run decision engine
    7. Merge all outputs → persist → return 201
    """
    validation_errors = _validate_input(raw_body)
    if validation_errors:
        logger.warning("Ingest validation failed: %s", validation_errors)
        raise HTTPException(status_code=400, detail={"errors": validation_errors})

    try:
        processed = run_pipeline(raw_body)
        cleaned_transcript = processed.pop("_cleaned_transcript", "")
        compliance = check_compliance(processed, db)

        # Convert compliance_violations list to comma-separated string for storage
        if "compliance_violations" in compliance and isinstance(compliance["compliance_violations"], list):
            compliance["compliance_violations"] = ",".join(compliance["compliance_violations"])

        metadata = enrich_metadata(processed)
        intent = classify_intent(cleaned_transcript or processed.get("transcript_summary", ""))

        # Extract objections from transcript
        objections = extract_objections(
            cleaned_transcript,
            processed.get("transcript_summary", "")
        )

        # Convert all_objections list to comma-separated string for storage
        if "all_objections" in objections and isinstance(objections["all_objections"], list):
            objections["all_objections"] = ",".join(objections["all_objections"])

        enriched = {**processed, **compliance, **metadata, **intent, **objections}
        decision = make_decision(enriched)
        full_record = {**enriched, **decision}

        validated = CallRecordCreate(**full_record)
        saved = crud.create_record(db, validated.model_dump())
        logger.info("Ingested call record id=%s dealer=%s", saved.id, saved.dealer_id)
        return saved

    except ValidationError as e:
        logger.warning("Pydantic validation failed: %s", e.error_count())
        raise HTTPException(status_code=422, detail={"errors": e.errors()})

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error during ingestion")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal processing error. Please try again or contact support."},
        )
