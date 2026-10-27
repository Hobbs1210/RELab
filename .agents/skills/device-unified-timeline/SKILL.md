---
name: device-unified-timeline
description: Correlate network and imported hardware observations
---

# Device Unified Timeline

Query /v1/timeline with a target IP and analysis ID; correlate Zeek DNS, conn, SSL, HTTP entries with the emulator request IDs and optional imported BLE/USB/serial timestamped events. Cite exact evidence IDs and note clock drift and gaps. Never treat event correlation alone as causation.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
