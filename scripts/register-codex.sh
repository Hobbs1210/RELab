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
codex mcp add device-binwalk --url http://127.0.0.1:8307/mcp
codex mcp add device-radare --url http://127.0.0.1:8308/mcp
codex mcp add device-yara --url http://127.0.0.1:8309/mcp
codex mcp add device-zeek --url http://127.0.0.1:8311/mcp
codex mcp add device-nmap --url http://127.0.0.1:8312/mcp
codex mcp add device-adb --url http://127.0.0.1:8313/mcp
codex mcp add device-filesystem --url http://127.0.0.1:8314/mcp
codex mcp add device-db --url http://127.0.0.1:8315/mcp
codex mcp list
