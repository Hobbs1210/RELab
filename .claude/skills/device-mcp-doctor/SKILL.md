---
name: device-mcp-doctor
description: Validate MCP availability across IDEs.
---

# Validate MCP availability across IDEs

## Workflow

Run scripts/validate-project.py and scripts/check-mcp.py. Inspect actual tool schemas in Antigravity, Codex or VS Code. Optional Ghidra requires profile startup. A reachable HTTP endpoint alone is not proof tools work.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
