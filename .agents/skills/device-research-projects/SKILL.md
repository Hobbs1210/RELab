---
name: device-research-projects
description: Manage project-scoped research evidence and artifacts
---

# Device Research Projects

Use `research_list_projects`, `research_list_devices`, `research_list_artifacts`, and `research_search_evidence` on the `device-research` MCP server. Always pass the intended project ID; never cite evidence from another project. To register a new device or import an artifact, request operator approval for the localhost REST/CLI operation, then verify its generated hash. For firmware hashes, cite exact artifact SHA-256 and evidence IDs.

## Constraints

Research only owned or authorized hardware and networks. Document source material, hashes and reversible experiment steps. Follow `AGENTS.md`, `docs/RESEARCH_HUB.md` and `SECURITY.md`.
