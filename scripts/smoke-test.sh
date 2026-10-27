#!/usr/bin/env bash
# RELab end-to-end smoke test with readiness polling and diagnostics.
set -euo pipefail

# ANSI color codes (fallback if not tty or NO_COLOR set)
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  C_GREEN='\033[0;32m'
  C_RED='\033[0;31m'
  C_YELLOW='\033[0;33m'
  C_CYAN='\033[0;36m'
  C_RESET='\033[0m'
else
  C_GREEN=''
  C_RED=''
  C_YELLOW=''
  C_CYAN=''
  C_RESET=''
fi

PASSED=0
FAILED=0
TOTAL=5

# [Warm-up Polling Loop] Wait up to 30s for Lab API to report ready
printf "${C_CYAN}==> Waiting for RELab API to be ready (up to 30s)...${C_RESET}\n"
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8090/__lab__/health >/dev/null 2>&1; then
    printf "${C_GREEN}[READY]${C_RESET} API health endpoint responded on attempt %d.\n\n" "$i"
    break
  fi
  if [[ $i -eq 30 ]]; then
    printf "${C_RED}[TIMEOUT]${C_RESET} API did not become ready after 30s. Check logs: docker compose logs api\n"
  fi
  sleep 1
done

run_check() {
  local num="$1" title="$2" cmd="$3" fail_hint="$4"
  printf "[%s/%s] %s... " "$num" "$TOTAL" "$title"
  if eval "$cmd" >/dev/null 2>&1; then
    printf "${C_GREEN}[PASS]${C_RESET}\n"
    ((PASSED++)) || true
  else
    printf "${C_RED}[FAIL]${C_RESET}\n"
    printf "      ${C_YELLOW}Hint: %s${C_RESET}\n" "$fail_hint"
    ((FAILED++)) || true
  fi
}

run_check 1 "API health" \
  "curl -fsS http://127.0.0.1:8090/__lab__/health" \
  "docker compose logs api"

run_check 2 "Synthetic HTTP mock (expect HTTP 200)" \
  "test \"\$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/__mock_test__)\" = 200" \
  "Check mock rules in config/rules.json and api service"

run_check 3 "HTTPS edge (self-signed cert, synthetic test)" \
  "test \"\$(curl -ksS -o /dev/null -w '%{http_code}' --resolve device.example.test:443:127.0.0.1 https://device.example.test/__mock_test__)\" = 200" \
  "docker compose logs https-edge cert-init"

run_check 4 "DNS API readiness" \
  "curl -fsS http://127.0.0.1:8090/__lab__/dns" \
  "docker compose logs dns api"

run_check 5 "Live MCP list-tools checks" \
  "python3 ./scripts/check-mcp.py" \
  "python3 scripts/check-mcp.py --json-out - for detailed MCP failure info"

printf "\n===================================================\n"
if [[ $FAILED -eq 0 ]]; then
  printf "${C_GREEN}Smoke tests complete: %d/%d passed.${C_RESET}\n" "$PASSED" "$TOTAL"
  printf "===================================================\n"
  exit 0
else
  printf "${C_RED}Smoke tests completed with %d failure(s). (%d/%d passed)${C_RESET}\n" "$FAILED" "$PASSED" "$TOTAL"
  printf "===================================================\n"
  exit 1
fi
