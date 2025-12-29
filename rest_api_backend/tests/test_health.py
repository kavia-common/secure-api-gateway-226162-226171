from fastapi import status


def test_health_v1(client):
    resp = client.get("/v1.0/health")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data.get("status") == "ok"


def test_root_health(client):
    resp = client.get("/")
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data.get("status") == "ok"
    assert data.get("message") == "Healthy"
