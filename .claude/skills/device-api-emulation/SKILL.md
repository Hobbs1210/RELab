---
name: device-api-emulation
description: Build evidence-based mock HTTP API response rules.
---

# Build evidence-based mock HTTP API response rules

## Workflow

Use config/rules.json or the authenticated REST control plane to add narrow host+method+path matches. Start with benign synthetic responses; use mitmproxy to verify proxy route. Save experiment snapshot and request approval before changes.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
