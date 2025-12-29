#!/usr/bin/env bash
# Auth flow helper for the FastAPI backend
# - Health check
# - Obtain JWT token
# - Call protected /me
#
# Usage:
#   scripts/auth_flow.sh [-h|--help]
#
# Environment overrides:
#   BASE_URL   (default: http://localhost:8000)
#   USERNAME   (default: testuser)
#   PASSWORD   (default: testpass)

set -euo pipefail

print_help() {
  cat <<'EOF'
Auth flow script for Secure API Gateway - REST API Backend

This script performs:
1) Health check: GET ${BASE_URL}/v1.0/health
2) Obtain token: POST ${BASE_URL}/v1.0/get_token with JSON {username, password}
3) Call protected endpoint: GET ${BASE_URL}/v1.0/me with Authorization: Bearer <token>

Usage:
  scripts/auth_flow.sh [options]

Options:
  -h, --help        Show this help and exit

Environment variables (optional):
  BASE_URL   Base URL of the backend (default: http://localhost:8000)
  USERNAME   Username for login         (default: testuser)
  PASSWORD   Password for login         (default: testpass)

Examples:
  scripts/auth_flow.sh
  BASE_URL=http://localhost:3001 scripts/auth_flow.sh
  USERNAME=alice PASSWORD='s3cr3t' scripts/auth_flow.sh
EOF
}

for arg in "${@:-}"; do
  case "$arg" in
    -h|--help) print_help; exit 0 ;;
    *) ;;
  esac
done

# Defaults
BASE_URL="${BASE_URL:-http://localhost:8000}"
USERNAME="${USERNAME:-testuser}"
PASSWORD="${PASSWORD:-testpass}"

echo "Auth flow starting..."
echo "Using BASE_URL=${BASE_URL}"
echo "USERNAME=${USERNAME}"

# Verify prerequisites
missing=0
if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: 'curl' is required but not found in PATH."
  missing=1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: 'jq' is required but not found in PATH."
  missing=1
fi
if [ "$missing" -ne 0 ]; then
  echo "Install the missing prerequisites and try again."
  exit 127
fi

overall_rc=0

step_health() {
  echo "Step 1: Health check -> GET ${BASE_URL}/v1.0/health"
  if ! resp="$(curl -sS -m 10 -w '\n%{http_code}' "${BASE_URL}/v1.0/health")"; then
    echo "Health check request failed."
    return 1
  fi
  body="$(printf "%s" "$resp" | sed '$d')"
  code="$(printf "%s" "$resp" | tail -n1)"
  if [ "$code" != "200" ]; then
    echo "Health check failed with HTTP $code. Body:"
    echo "$body"
    return 1
  fi
  status="$(echo "$body" | jq -r '.status // empty' || true)"
  echo "Health response (HTTP $code): $body"
  if [ "$status" != "ok" ]; then
    echo "Unexpected health status: ${status:-<missing>}"
    return 1
  fi
  echo "Step 1 summary: PASS"
  return 0
}

step_token() {
  echo "Step 2: Obtain token -> POST ${BASE_URL}/v1.0/get_token"
  payload=$(jq -n --arg u "$USERNAME" --arg p "$PASSWORD" '{username:$u, password:$p}')
  if ! resp="$(curl -sS -m 15 -w '\n%{http_code}' -H "Content-Type: application/json" -X POST \
      -d "$payload" "${BASE_URL}/v1.0/get_token")"; then
    echo "Token request failed."
    return 1
  fi
  body="$(printf "%s" "$resp" | sed '$d')"
  code="$(printf "%s" "$resp" | tail -n1)"
  if [ "$code" != "200" ]; then
    echo "Token endpoint returned HTTP $code. Body:"
    echo "$body"
    return 1
  fi
  token="$(echo "$body" | jq -r '.access_token // empty' || true)"
  if [ -z "$token" ] || [ "$token" = "null" ]; then
    echo "Failed to parse access_token from response:"
    echo "$body"
    return 1
  fi
  TOKEN="$token"
  echo "Step 2 summary: PASS (token acquired)"
  return 0
}

step_me() {
  echo "Step 3: Call protected endpoint -> GET ${BASE_URL}/v1.0/me"
  if [ -z "${TOKEN:-}" ]; then
    echo "No token available. Did Step 2 succeed?"
    return 1
  fi
  if ! resp="$(curl -sS -m 15 -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN}" \
      "${BASE_URL}/v1.0/me")"; then
    echo "Protected request failed."
    return 1
  fi
  body="$(printf "%s" "$resp" | sed '$d')"
  code="$(printf "%s" "$resp" | tail -n1)"
  if [ "$code" != "200" ]; then
    echo "Protected endpoint returned HTTP $code. Body:"
    echo "$body"
    return 1
  fi
  echo "Response JSON:"
  echo "$body" | jq .
  echo "Step 3 summary: PASS"
  return 0
}

if ! step_health; then
  overall_rc=1
fi

if ! step_token; then
  overall_rc=1
fi

if ! step_me; then
  overall_rc=1
fi

if [ "$overall_rc" -eq 0 ]; then
  echo "Auth flow completed successfully."
else
  echo "Auth flow encountered errors."
fi

exit "$overall_rc"
