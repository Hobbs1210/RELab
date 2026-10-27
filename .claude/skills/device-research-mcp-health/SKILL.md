---
name: device-research-mcp-health
description: Check MCP transport and permissions across supported IDEs
---

# Device Research Mcp Health

Review IDE MCP registrations for Codex, Antigravity, VS Code and Cursor. Run `scripts/check-mcp.py --json-out data/research/mcp-health.json` on the same machine as the MCP endpoints. Report **live handshake** success separately from static configuration; Ghidra is an optional profile. The unified Research Hub MCP is read-only; invoke state mutations through approved token-protected localhost API calls.

## Constraints

Research only owned or authorized hardware and networks. Document source material, hashes and reversible experiment steps. Follow `AGENTS.md`, `docs/RESEARCH_HUB.md` and `SECURITY.md`.
