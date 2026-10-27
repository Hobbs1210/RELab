#!/usr/bin/env bash
set -euo pipefail
command -v codex >/dev/null || { echo 'Codex CLI not installed'; exit 1; }
# Run on the machine where Codex is installed. All endpoints are loopback-only.
codex mcp add device-dns --url http://127.0.0.1:8301/
codex mcp add device-mitm --url http://127.0.0.1:8302/mcp
codex mcp add device-pcap --url http://127.0.0.1:8303/mcp
codex mcp add device-ble --url http://127.0.0.1:8304/mcp
codex mcp add device-docker --url http://127.0.0.1:8305/mcp
codex mcp add device-api --url http://127.0.0.1:8090/mcp
codex mcp add device-workbench --url http://127.0.0.1:8310/mcp
codex mcp add device-research --url http://127.0.0.1:8320/mcp
codex mcp add device-ghidra --url http://127.0.0.1:8306/mcp
codex mcp list
