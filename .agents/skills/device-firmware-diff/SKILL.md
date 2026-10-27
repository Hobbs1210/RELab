---
name: device-firmware-diff
description: Compare firmware versions with evidence and limits
---

# Device Firmware Diff

Use /v1/firmware/compare?a=X&b=Y. Save full SHA256 and exact sizes; only first 2 MiB receive byte-by-byte range comparisons. For function semantics, use optional Ghidra profile. Never confuse changed bytes with fixed security vulnerabilities.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
