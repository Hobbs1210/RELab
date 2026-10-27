---
name: device-protocol-adapters
description: Add and test device-independent declarative framing adapters
---

# Device Protocol Adapters

Read docs/ADVANCED_RESEARCH.md and workbench/engine.py. Inspect /v1/protocols. Define protocol framing only, as JSON under protocols/<id>.json; never import or eval unknown decoder code. Validate with known synthetic hex and compare against real PCAP evidence. Treat all vendor-specific claims as unverified until tested.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
