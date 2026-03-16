"""
Metadata enrichment service.

Derives additional fields from raw record data:
  - call_duration_minutes  (from duration_sec)
  - delta_aging_bucket     (from days_past_due)
  - time_of_day_category   (from call_timestamp)
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _aging_bucket(days_past_due: int) -> str:
    """Map days-past-due to a standard aging bucket label."""
    if days_past_due <= 0:
        return "CURRENT"
    if days_past_due <= 30:
        return "1-30"
    if days_past_due <= 60:
        return "31-60"
    if days_past_due <= 90:
        return "61-90"
    return "90+"


def _time_of_day_category(timestamp: datetime) -> str:
    """Categorise the call time into morning / afternoon / evening."""
    hour = timestamp.hour
    if hour < 12:
        return "MORNING"
    if hour < 17:
        return "AFTERNOON"
    return "EVENING"


def enrich_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Return derived metadata fields for a processed record."""
    duration_sec = record.get("call_duration_sec", record.get("duration", 0))
    days = record.get("days_past_due", 0)

    timestamp = record.get("call_timestamp")
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    result = {
        "call_duration_minutes": round(duration_sec / 60, 2) if duration_sec else 0.0,
        "delta_aging_bucket": _aging_bucket(days),
        "time_of_day_category": (
            _time_of_day_category(timestamp) if timestamp else "UNKNOWN"
        ),
    }

    logger.info(
        "Metadata enriched: bucket=%s, duration=%.2fmin, time_of_day=%s",
        result["delta_aging_bucket"],
        result["call_duration_minutes"],
        result["time_of_day_category"],
    )
    return result
