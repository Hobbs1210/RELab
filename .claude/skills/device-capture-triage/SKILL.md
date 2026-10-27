---
name: device-capture-triage
description: Inspect packet captures and summarize traffic behavior.
---

# Inspect packet captures and summarize traffic behavior

## Workflow

Confirm TARGET_IP and gateway/TAP visibility. Inventory PCAPs, calculate SHA-256, inspect with Zeek/TShark, distinguish observed DNS/TLS from inferred application behavior. Never infer payloads from encrypted traffic.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
