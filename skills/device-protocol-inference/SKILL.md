---
name: device-protocol-inference
description: Infer candidate binary message structure conservatively
---

# Device Protocol Inference

Collect at least two related authorized messages; use /v1/infer?ids=... or /v1/infer/hex?samples=... and /v1/decode. Test prefix, framing, lengths, delimiter and entropy hypotheses with one variable changed at a time. Record failures. Do not assert semantic fields without controlled evidence.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
