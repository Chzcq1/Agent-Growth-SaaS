#!/usr/bin/env bash
# Smoke-test for the Beauty Agent System dev server.
# Verifies the admin dashboard renders and the Chatwoot webhook -> supervisor
# routing pipeline actually responds (not just that the port is open).
#
# Usage: PORT=8000 bash beauty_agent_system/scripts/health_check.sh

set -euo pipefail

PORT="${PORT:-8000}"
BASE_URL="http://localhost:${PORT}"

echo "Checking ${BASE_URL}/admin/system-health ..."
status=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/system-health")
if [ "$status" != "200" ]; then
  echo "FAIL: /admin/system-health returned HTTP ${status}"
  exit 1
fi
echo "OK: admin dashboard is up (HTTP 200)"

echo "Checking ${BASE_URL}/webhooks/chatwoot ..."
response=$(curl -s -X POST "${BASE_URL}/webhooks/chatwoot" \
  -H "Content-Type: application/json" \
  -d '{"content": "ราคาเท่าไหร่คะ", "sender": {"name": "ร้านเล็บทดสอบ"}, "conversation": {"id": "1"}}')
echo "Response: ${response}"

if echo "$response" | grep -q '"intent"'; then
  echo "OK: webhook was classified and routed by the supervisor"
else
  echo "FAIL: webhook did not return an expected intent classification"
  exit 1
fi

echo "All health checks passed."
