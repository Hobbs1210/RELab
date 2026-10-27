---
name: device-offline-replay
description: Reproduce experiments safely from immutable inputs
---

# Device Offline Replay

Create an offline emulator-test or replay experiment using the authorized Research Hub REST endpoint. Its input parameters become an immutable snapshot. Reproduce with the experiment's rerun endpoint and compare the results. Restore affects only offline initial state and never DNS, firmware or physical hardware; do not claim otherwise. Use bounded mutations with an explicit case count.

## Constraints

Research only owned or authorized hardware and networks. Document source material, hashes and reversible experiment steps. Follow `AGENTS.md`, `docs/RESEARCH_HUB.md` and `SECURITY.md`.
