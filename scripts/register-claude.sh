#!/usr/bin/env bash
# Register RELab MCP servers with Claude Desktop and Claude Code CLI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$ROOT/config"
CLAUDE_CONFIG_EXPORT="$CONFIG_DIR/claude_mcp_config.json"
mkdir -p "$CONFIG_DIR"

SERVERS=(
  "device-dns|http://127.0.0.1:8301/|AdGuard DNS management"
  "device-mitm|http://127.0.0.1:8302/mcp|mitmproxy traffic inspection"
  "device-pcap|http://127.0.0.1:8303/mcp|Wireshark PCAP inspection"
  "device-ble|http://127.0.0.1:8304/mcp|Bluetooth Low Energy analysis"
  "device-docker|http://127.0.0.1:8305/mcp|Docker container proxy"
  "device-api|http://127.0.0.1:8090/mcp|Lab API and mock observation"
  "device-workbench|http://127.0.0.1:8310/mcp|Universal protocol workbench"
  "device-research|http://127.0.0.1:8320/mcp|Unified research hub & evidence"
  "device-ghidra|http://127.0.0.1:8306/mcp|Firmware reverse engineering"
  "device-binwalk|http://127.0.0.1:8307/mcp|Binwalk firmware extraction"
  "device-radare|http://127.0.0.1:8308/mcp|Radare2 binary analysis"
  "device-yara|http://127.0.0.1:8309/mcp|YARA secrets scanner"
  "device-zeek|http://127.0.0.1:8311/mcp|Zeek protocol analyzer"
  "device-nmap|http://127.0.0.1:8312/mcp|Nmap network discovery"
  "device-adb|http://127.0.0.1:8313/mcp|ADB companion app inspector"
  "device-filesystem|http://127.0.0.1:8314/mcp|Lab filesystem explorer"
  "device-db|http://127.0.0.1:8315/mcp|Database query inspector"
)

# 1. Generate standard claude_mcp_config.json export
python3 - "$CLAUDE_CONFIG_EXPORT" <<'PY'
import json, sys
from pathlib import Path

out_path = Path(sys.argv[1])
servers = {
    "device-dns": {"type": "http", "url": "http://127.0.0.1:8301/"},
    "device-mitm": {"type": "http", "url": "http://127.0.0.1:8302/mcp"},
    "device-pcap": {"type": "http", "url": "http://127.0.0.1:8303/mcp"},
    "device-ble": {"type": "http", "url": "http://127.0.0.1:8304/mcp"},
    "device-docker": {"type": "http", "url": "http://127.0.0.1:8305/mcp"},
    "device-api": {"type": "http", "url": "http://127.0.0.1:8090/mcp"},
    "device-workbench": {"type": "http", "url": "http://127.0.0.1:8310/mcp"},
    "device-research": {"type": "http", "url": "http://127.0.0.1:8320/mcp"},
    "device-ghidra": {"type": "http", "url": "http://127.0.0.1:8306/mcp"},
    "device-binwalk": {"type": "http", "url": "http://127.0.0.1:8307/mcp"},
    "device-radare": {"type": "http", "url": "http://127.0.0.1:8308/mcp"},
    "device-yara": {"type": "http", "url": "http://127.0.0.1:8309/mcp"},
    "device-zeek": {"type": "http", "url": "http://127.0.0.1:8311/mcp"},
    "device-nmap": {"type": "http", "url": "http://127.0.0.1:8312/mcp"},
    "device-adb": {"type": "http", "url": "http://127.0.0.1:8313/mcp"},
    "device-filesystem": {"type": "http", "url": "http://127.0.0.1:8314/mcp"},
    "device-db": {"type": "http", "url": "http://127.0.0.1:8315/mcp"}
}

doc = {"mcpServers": servers}
out_path.write_text(json.dumps(doc, indent=2) + "\n")
print(f"Generated Claude MCP configuration template: {out_path}")
PY

# 2. If claude CLI is available, register servers
if command -v claude >/dev/null 2>&1; then
  echo "Claude CLI detected. Registering MCP servers..."
  for entry in "${SERVERS[@]}"; do
    IFS='|' read -r name url desc <<< "$entry"
    claude mcp add "$name" --transport sse "$url" 2>/dev/null || \
      claude mcp add "$name" "$url" 2>/dev/null || true
  done
  echo "Claude CLI registration complete. Run 'claude mcp list' to verify."
else
  echo "Claude CLI not found in PATH (skipping CLI registration)."
fi

# 3. Locate Claude Desktop config file if present
desktop_config=""
if [[ -n "${APPDATA:-}" && -d "$APPDATA/Claude" ]]; then
  desktop_config="$APPDATA/Claude/claude_desktop_config.json"
elif [[ -d "$HOME/Library/Application Support/Claude" ]]; then
  desktop_config="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
elif [[ -d "$HOME/.config/Claude" ]]; then
  desktop_config="$HOME/.config/Claude/claude_desktop_config.json"
fi

if [[ -n "$desktop_config" ]]; then
  python3 - "$desktop_config" "$CLAUDE_CONFIG_EXPORT" <<'PY'
import json, sys
from pathlib import Path
target = Path(sys.argv[1])
source = json.loads(Path(sys.argv[2]).read_text())

data = {}
if target.is_file():
    try:
        data = json.loads(target.read_text())
    except Exception:
        data = {}

data.setdefault("mcpServers", {})
for k, v in source["mcpServers"].items():
    data["mcpServers"][k] = v

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(data, indent=2) + "\n")
print(f"Updated Claude Desktop configuration: {target}")
PY
else
  echo "To use with Claude Desktop, merge config/claude_mcp_config.json into your claude_desktop_config.json."
fi
