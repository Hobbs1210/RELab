---
name: device-protocol-workbench
description: Inspect and compare protocol captures in the local interactive workbench
---

# Device Protocol Workbench

Use http://127.0.0.1:8310 to inspect timeline, decode hex, infer structures and preview contracts. All default MCP calls are read-only. Any REST POST requires the generated X-Lab-Token and explicit operator approval.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
