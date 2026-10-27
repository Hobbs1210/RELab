---
name: device-stateful-fuzzing
description: Design safe boofuzz request sequences against lab emulator
---

# Device Stateful Fuzzing

Use fuzz/run.py setup->action example and docs. Keep FUZZ_MAX_CASES <=1000. Mutate the local emulator only, collect boofuzz SQLite logs, compare baseline and candidate. External target fuzz requires a separately authorized and reviewed workflow.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
