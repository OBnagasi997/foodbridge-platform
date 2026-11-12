from unittest.mock import patch


def test_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readiness_ok_with_database(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_readiness_503_when_database_down(client):
    with patch("sqlalchemy.orm.Session.execute", side_effect=RuntimeError("db down")):
        r = client.get("/health/ready")
    assert r.status_code == 503


def test_liveness_survives_database_outage(client):
    with patch("sqlalchemy.orm.Session.execute", side_effect=RuntimeError("db down")):
        assert client.get("/health").status_code == 200


def test_metrics_exposes_http_and_business_series(client):
    client.get("/health")
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    assert "foodbridge_users_registered_total" in body or "foodbridge_kg_rescued_total" in body
