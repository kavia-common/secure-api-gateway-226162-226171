# secure-api-gateway-226162-226171

## Quick auth flow script

An automated script is provided to test the authentication flow against the FastAPI backend.

- Path: scripts/auth_flow.sh
- Prerequisites: curl, jq
- Make executable (if needed): chmod +x scripts/auth_flow.sh
- Defaults:
  - BASE_URL=http://localhost:8000
  - USERNAME=testuser
  - PASSWORD=testpass

Usage:
- Run with defaults:
  scripts/auth_flow.sh

- Override values:
  BASE_URL=http://localhost:3001 USERNAME=alice PASSWORD='s3cr3t' scripts/auth_flow.sh

The script performs:
1) GET ${BASE_URL}/v1.0/health
2) POST ${BASE_URL}/v1.0/get_token
3) GET ${BASE_URL}/v1.0/me