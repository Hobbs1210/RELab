---
name: device-mcp-security
description: Choose least-privilege agent tools for research.
---

# Choose least-privilege agent tools for research

## Workflow

MCP API exposes read-only operations by default; authenticated REST+labctl handle state mutations. Limit BLE writes, Ghidra exposure and Docker proxy privileges. Prefer operator-reviewed plans over automated interception changes.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
