"""Integration tests for POST /api/ingest."""


def test_ingest_valid_call(client, sample_raw_call):
    resp = client.post("/api/ingest", json=sample_raw_call)
    assert resp.status_code == 201
    data = resp.json()

    assert data["id"] == 1
    assert data["dealer_id"] == "DLR-00421"
    assert data["compliance_status"] == "PASS"
    assert data["intent_class"] == "COMMITTED"
    assert data["next_action"] == "SCHEDULE_FOLLOWUP"
    assert "Jane Smith" not in data["transcript_summary"]
    assert data["fulfillment_probability"] is not None


def test_ingest_missing_required_fields(client):
    resp = client.post("/api/ingest", json={})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "errors" in detail
    assert any("dealer_id" in e for e in detail["errors"])
    assert any("transcript" in e for e in detail["errors"])
    assert any("timestamp" in e for e in detail["errors"])


def test_ingest_invalid_past_due_type(client):
    payload = {
        "dealer_id": "DLR-001",
        "transcript": "Test call",
        "timestamp": "2026-03-12T14:00:00",
        "past_due": "not_a_number",
        "compliance_flags": "TCPA_OK",
    }
    resp = client.post("/api/ingest", json=payload)
    assert resp.status_code == 400
    assert any("past_due" in e for e in resp.json()["detail"]["errors"])


def test_ingest_negative_outstanding_amount(client):
    payload = {
        "dealer_id": "DLR-001",
        "transcript": "Test call",
        "timestamp": "2026-03-12T14:00:00",
        "outstanding_amount": -100,
        "compliance_flags": "TCPA_OK",
    }
    resp = client.post("/api/ingest", json=payload)
    assert resp.status_code == 400
    assert any("non-negative" in e for e in resp.json()["detail"]["errors"])


def test_ingest_creates_persisted_record(client, sample_raw_call):
    client.post("/api/ingest", json=sample_raw_call)
    decisions_resp = client.get("/api/decisions")
    assert decisions_resp.status_code == 200
    assert len(decisions_resp.json()) == 1
