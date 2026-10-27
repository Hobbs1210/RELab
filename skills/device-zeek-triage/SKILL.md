---
name: device-zeek-triage
description: Compare indexed captures through Zeek and TShark.
---

# Compare indexed captures through Zeek and TShark

## Workflow

Run scripts/analyze-now.sh after closing a capture. Read data/analysis/<sha-prefix>/summary.json, compare protocol and connection metrics, then corroborate with packet samples.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
