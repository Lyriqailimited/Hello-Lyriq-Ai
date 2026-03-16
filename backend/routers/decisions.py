"""
GET /decisions – paginated list of all enriched call records.
GET /dashboard  – aggregated KPI summary.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.database import get_db
from models.schemas import CallRecordRead, KPISummary
import crud

router = APIRouter(prefix="/api", tags=["decisions"])


@router.get("/decisions", response_model=list[CallRecordRead])
def list_decisions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return a paginated list of enriched call records."""
    return crud.get_all_records(db, skip=skip, limit=limit)


@router.get("/dashboard", response_model=KPISummary)
def get_dashboard(db: Session = Depends(get_db)):
    """Return aggregated KPI metrics for the dashboard."""
    return crud.get_dashboard_kpis(db)
