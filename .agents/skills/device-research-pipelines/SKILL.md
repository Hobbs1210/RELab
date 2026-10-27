---
name: device-research-pipelines
description: Plan and monitor durable firmware/protocol research pipelines
---

# Device Research Pipelines

Use `research_list_recipes`, `research_research_plan`, and `research_list_jobs` to recommend a named pipeline based on existing evidence. Mark an absent SHA-256 or TCP port as missing rather than inventing it. Operator-approved writes go through `scripts/researchctl.py recipe ...` or the token-protected API. Check job status and report any failed/skipped stages honestly; generated protocol artifacts are candidates, not verified reverse-engineering results.

## Constraints

Research only owned or authorized hardware and networks. Document source material, hashes and reversible experiment steps. Follow `AGENTS.md`, `docs/RESEARCH_HUB.md` and `SECURITY.md`.
