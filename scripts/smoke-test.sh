#!/usr/bin/env bash
set -euo pipefail
printf '[1/5] API health\n'
curl -fsS http://127.0.0.1:8090/__lab__/health && echo
printf '[2/5] Synthetic HTTP mock (expect HTTP 200)\n'
test "$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/__mock_test__)" = 200
printf '[3/5] HTTPS edge (self-signed cert, -k FOR SYNTHETIC TEST ONLY)\n'
test "$(curl -ksS -o /dev/null -w '%{http_code}' --resolve device.example.test:443:127.0.0.1 https://device.example.test/__mock_test__)" = 200
printf '[4/5] DNS API readiness\n'
curl -fsS http://127.0.0.1:8090/__lab__/dns && echo
printf '[5/5] Live MCP list-tools checks\n'
python3 ./scripts/check-mcp.py
