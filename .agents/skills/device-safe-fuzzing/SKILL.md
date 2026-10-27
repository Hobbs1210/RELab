---
name: device-safe-fuzzing
description: Run bounded network or hardware fuzz experiments with approval
---

# Device Safe Fuzzing

Start with docker compose --profile fuzz run --rm fuzz against the mock API only. Never point network fuzzer to outside services. For attached serial devices follow fuzz/README.md and obtain explicit operator approval, device passthrough and safe recovery. Limit case count, rate and duration; preserve crash reports.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
