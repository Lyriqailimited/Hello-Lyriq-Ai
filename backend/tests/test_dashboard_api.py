"""Integration tests for GET /api/dashboard."""


def test_dashboard_empty(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 0
    assert data["avg_sentiment"] == 0.0
    assert data["avg_promise_coverage"] == 0.0
    assert data["compliance_pass_rate"] == 0.0
    assert data["intent_distribution"] == {}


def test_dashboard_after_ingestion(client, sample_raw_call):
    client.post("/api/ingest", json=sample_raw_call)

    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 1
    assert data["avg_sentiment"] == 0.72
    assert data["compliance_pass_rate"] == 1.0
    assert "COMMITTED" in data["intent_distribution"]
    assert data["intent_distribution"]["COMMITTED"] == 1


def test_dashboard_mixed_records(client, sample_raw_call):
    # Record 1: compliant, committed
    client.post("/api/ingest", json=sample_raw_call)

    # Record 2: non-compliant (after hours)
    non_compliant = {**sample_raw_call, "timestamp": "2026-03-12T03:00:00"}
    client.post("/api/ingest", json=non_compliant)

    resp = client.get("/api/dashboard")
    data = resp.json()
    assert data["total_calls"] == 2
    assert data["compliance_pass_rate"] == 0.5
