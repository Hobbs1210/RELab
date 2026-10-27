---
name: device-ai-safety-audit
description: Review MCP permissions and lab security boundaries.
---

# Review MCP permissions and lab security boundaries

## Workflow

Verify target ownership and isolated network. Check that control interfaces bind to loopback, mutations need operator approval, PCAPs and BLE pairing secrets remain local. Inspect compose and tokens before proposing elevated permissions.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
