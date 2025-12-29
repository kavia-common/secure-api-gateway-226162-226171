# Secure API Gateway - REST API Backend (FastAPI)

This service provides JWT-authenticated REST endpoints with versioned routes under `/v1.0`.

## Environment variables

Create a `.env` file (do not commit secrets). Required variables:
- JWT_SECRET=<provide strong secret>
- JWT_ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRES_MINUTES=30
- DATABASE_URL=postgresql://appuser:dbuser123@localhost:5000/myapp

Optional overrides to handle preview DB port:
- POSTGRES_PORT=5001
- DB_FALLBACK_PORT_OVERRIDE=5001

Notes:
- If `DATABASE_URL` is not set, the app will try to read from `../secure-api-gateway-226162-226172/database/db_connection.txt` and apply a port override if `POSTGRES_PORT` or `DB_FALLBACK_PORT_OVERRIDE` is provided. This resolves the common mismatch where local scripts use port 5000 but the preview DB runs on port 5001.

## Run locally

Install dependencies and run uvicorn:
1) python -m venv .venv && source .venv/bin/activate
2) pip install -r requirements.txt
3) uvicorn src.api.main:app --reload

Open:
- Docs: http://localhost:8000/docs (endpoints under /v1.0)
- Health: GET http://localhost:8000/v1.0/health

## Verify DB connectivity

Ensure the database is reachable via `DATABASE_URL` or the db_connection.txt fallback. If using preview DB exposed at port 5001, set POSTGRES_PORT=5001 (or DB_FALLBACK_PORT_OVERRIDE=5001) in .env.

## JWT authentication flow

Seeded user expected by the database (as provisioned):
- username: testuser
- password: testpass

1) Obtain a token
curl -s -X POST http://localhost:8000/v1.0/get_token \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'

Example response:
{ "access_token": "<JWT>", "token_type": "bearer" }

2) Use the token to call /me
TOKEN="<JWT from previous step>"
curl -s http://localhost:8000/v1.0/me -H "Authorization: Bearer $TOKEN"

Expected response:
{ "username": "testuser", "created_at": "..." }

## OpenAPI

- /docs should show the versioned endpoints under /v1.0.
- OpenAPI JSON at /openapi.json includes security scheme for bearer JWT.

## Notes

- CORS is permissive for development.
- Avoid hardcoding connection details in code; use .env.
- For CI or preview environments, set POSTGRES_PORT to the preview's port (commonly 5001).
