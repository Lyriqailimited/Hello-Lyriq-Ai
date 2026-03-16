"""Integration tests for GET /api/decisions."""


def test_decisions_empty(client):
    resp = client.get("/api/decisions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_decisions_returns_ingested_records(client, sample_raw_call):
    client.post("/api/ingest", json=sample_raw_call)
    client.post("/api/ingest", json=sample_raw_call)

    resp = client.get("/api/decisions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_decisions_pagination(client, sample_raw_call):
    for _ in range(5):
        client.post("/api/ingest", json=sample_raw_call)

    resp = client.get("/api/decisions?skip=0&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/api/decisions?skip=2&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/api/decisions?skip=4&limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
