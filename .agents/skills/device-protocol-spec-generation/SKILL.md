---
name: device-protocol-spec-generation
description: Generate candidate Kaitai formats, dissectors and SDKs from evidence
---

# Device Protocol Spec Generation

Begin with captured bytes and a stated framing hypothesis. Use bounded `kaitai`, `dissector`, and `sdk` recipe jobs, then validate generated KSY/Lua/client code against independent test samples. Use the offline emulator for regression fixtures, not a physical device by default. Preserve the source evidence IDs and clearly mark any generated definitions unverified.

## Constraints

Research only owned or authorized hardware and networks. Document source material, hashes and reversible experiment steps. Follow `AGENTS.md`, `docs/RESEARCH_HUB.md` and `SECURITY.md`.
