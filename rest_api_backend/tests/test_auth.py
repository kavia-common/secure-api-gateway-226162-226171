from fastapi import status

# Tests for POST /v1.0/get_token and GET /v1.0/me


def test_get_token_success(client):
    payload = {"username": "testuser", "password": "testpass"}
    resp = client.post("/v1.0/get_token", json=payload)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    # Basic shape assertions
    assert "access_token" in data and isinstance(data["access_token"], str) and data["access_token"]
    assert data.get("token_type") == "bearer"


def test_get_token_invalid_credentials(client):
    payload = {"username": "testuser", "password": "wrongpass"}
    resp = client.post("/v1.0/get_token", json=payload)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED, resp.text


def test_me_with_valid_token(client, bearer_token):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    resp = client.get("/v1.0/me", headers=headers)
    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()
    assert data.get("username") == "testuser"
    # created_at is optional in schema, but our override provides it
    assert "created_at" in data
    assert isinstance(data["created_at"], str)


def test_me_missing_token(client):
    resp = client.get("/v1.0/me")
    # OAuth2PasswordBearer will produce a 401 for missing token
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED, resp.text


def test_me_invalid_token(client):
    headers = {"Authorization": "Bearer invalid.token.value"}
    resp = client.get("/v1.0/me", headers=headers)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED, resp.text
