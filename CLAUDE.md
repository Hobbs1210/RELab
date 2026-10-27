# Claude / other MCP-compatible agents

# Device RE Lab agent operating rules

This project is a **general-purpose** IoT and embedded device research platform. **Default target profile: `generic`**, with no active vendor DNS rewrites. Optional `profiles/stadia-original.json` is an example only.

1. Read `README.md`, `docs/PHASES.md`, `docs/MCP.md` and the relevant `.agents/skills/device-*/SKILL.md` before performing invasive actions.
2. Restrict all packet captures, BLE actions, and DNS rewrites to specifically authorized devices and an isolated test network. Observe before redirecting.
3. The built-in Device API MCP is deliberately read-only; writes go through `scripts/labctl.py` or authenticated localhost REST calls with `X-Lab-Token`, after operator approval. Never expose credentials in prompts, logs or commits.
4. DNS/HTTP simulation does not break TLS certificate validation. Do not invent vendor protocol knowledge. Cite PCAP hashes, firmware offsets and real observations in research reports.
5. Never activate DNS rewrites, BLE writes, privileged Docker APIs, router nftables rules, or firmware flashing without the operator's explicit approval.
6. Tools on localhost are on the **agent host**; use VS Code Remote-SSH to the Linux host or SSH port forwards. Ghidra is optional and requires `--profile ghidra`.
7. Use `scripts/device-profile.py list|show|validate`, `scripts/validate-project.py` and `scripts/check-mcp.py` for diagnostics.

For protocol decoding, hardware inventory and SDK candidates, use the read-only `device-workbench` MCP on localhost 8310. See `docs/ADVANCED_RESEARCH.md`; all observations are evidence, heuristics are not verified, and hardware fuzzer profiles are opt-in.

## Integrated Research Hub (port 8320)

Prefer the `device-research` read-only MCP when dealing with projects, firmware/capture hashes, historical evidence, durable jobs, experiment results or plans. Keep `project_id` explicit. Only request write actions through the token-protected REST/CLI after the operator authorizes the change; never print `.env` credentials. Source evidence by ID/hash and label generated state-machine / Kaitai / Wireshark / SDK outputs **unverified** until independently tested.

Use `python3 scripts/researchctl.py list projects` and `python3 scripts/researchctl.py list jobs` in an SSH workspace. For infrastructure health, run `python3 scripts/check-mcp.py --json-out data/research/mcp-health.json`. Review `docs/FEATURE_MATRIX.md` for feature maturity and `docs/RESEARCH_HUB.md` for exact workflows. An offline experiment restore does not roll back AdGuard DNS or physical device state.
