---
name: device-architecture-detection
description: Identify architecture candidates and firmware signatures
---

# Device Architecture Detection

Use /v1/firmware/<basename>/architecture for signatures. Distinguish ELF machine IDs from filesystem markers. For raw MCU firmware, correlate Ghidra disassembly, boot addresses, datasheet and board revisions; unknown means unknown.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
