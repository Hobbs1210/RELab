# MCP servers and permission boundaries

| Server | Endpoint (agent host) | Startup | Permissions |
|---|---|---|---|
| `device-dns` | `http://127.0.0.1:8301/` | default | AdGuard community MCP may modify DNS: approve each change |
| `device-mitm` | `http://127.0.0.1:8302/mcp` | default | Observe/replay mitmproxy traffic; changing flows requires approval |
| `device-pcap` | `http://127.0.0.1:8303/mcp` | default | PCAP mounted read-only; community tool capabilities may vary |
| `device-ble` | `http://127.0.0.1:8304/mcp` | default | BLE writes disabled by environment; radio requires host BlueZ/DBus |
| `device-docker` | `http://127.0.0.1:8305/mcp` | default | Read-only docker-socket proxy: no POST/EXEC/build |
| `device-api` | `http://127.0.0.1:8090/mcp` | default | **Read-only** experimental API observations and reports |
| `device-workbench` | `http://127.0.0.1:8310/mcp` | default | Read-only protocol decode, timeline, hardware inventory, candidate contract / SDK |
| `device-research` | `http://127.0.0.1:8320/mcp` | default | **Read-only unified projects, evidence, jobs, plans and experiments**; writes use token-protected REST |
| `device-binwalk` | `http://127.0.0.1:8307/mcp` | default | Binwalk signature scan & recursive firmware extraction |
| `device-radare` | `http://127.0.0.1:8308/mcp` | default | Radare2/Rizin binary triage, functions, strings, disasm, entropy |
| `device-yara` | `http://127.0.0.1:8309/mcp` | default | YARA rules & high-entropy secret/key discovery |
| `device-zeek` | `http://127.0.0.1:8311/mcp` | default | Zeek network security monitoring and structured PCAP log triage |
| `device-nmap` | `http://127.0.0.1:8312/mcp` | default | Bounded lab network discovery and banner analysis |
| `device-adb` | `http://127.0.0.1:8313/mcp` | default | ADB companion app logcat, packages and dumpsys |
| `device-filesystem` | `http://127.0.0.1:8314/mcp` | default | Scoped read-only access to lab files and artifacts |
| `device-db` | `http://127.0.0.1:8315/mcp` | default | Read-only SQL inspection of SQLite requests & Postgres research DB |
| `device-ghidra` | `http://127.0.0.1:8306/mcp` | optional `--profile ghidra` | Offline firmware analysis (CPU intensive) |

**Check live tools:** `python3 scripts/check-mcp.py` for all 16 default MCP servers; after starting Ghidra, run with `--all`. This must succeed on the actual host before claiming integrations are operational. Static config checks are not MCP handshakes.

**Agent files:** Antigravity `.agents/mcp_config.json`, Codex `.codex/config.toml`, VS Code/Copilot `.vscode/mcp.json`, Cursor `.cursor/mcp.json`, portable `.mcp.json`. These are workspace-local and use loopback URLs relative to the agent process. Run `bash scripts/register-codex.sh` for Codex CLI or `bash scripts/register-claude.sh` for Claude Desktop / Claude Code.

**Integrated Research & Traffic Tools:**
* **Live PCAP Streaming:** `bash scripts/stream-pcap.sh [--host re@DEBIAN_IP]` pipes live interface traffic directly into desktop Wireshark over SSH, complementing `device-pcap` MCP.
* **Lab Root CA Export:** `bash scripts/export-ca.sh` exports the lab's TLS certificates (PEM, DER, Android Magisk `<hash>.0`) to `certs/export/` for target devices, enabling clean decryption by `device-mitm` and `device-api`.
* **Cross-Layer Correlation:** `python3 scripts/correlate-traffic.py [--save]` audits DNS lookups vs. TLS ClientHello SNI and HTTP flows to flag direct IP connections (hardcoded fallbacks), DoH evasion, and domain fronting. Saved reports in `data/analysis/` are immediately indexed as evidence by `device-api` and `device-research`.

**Mutations:** `device-api` MCP exposes only GET-style operations. For response/DNS/scenario edits and experiment creation/rollback, use `scripts/labctl.py` or localhost REST with the generated `.env` `LAB_ADMIN_TOKEN` in the `X-Lab-Token` header, **after approval**. Other community MCPs have their own permission model and should be reviewed before use.

Upstream community implementations: [AdGuard MCP](https://github.com/Samik081/mcp-adguard-home), [mitmproxy MCP](https://github.com/lups2000/mitmproxy-MCP), [Wireshark MCP](https://github.com/khuynh22/mcp-wireshark), [BLE MCP](https://github.com/es617/ble-mcp-server), [Docker MCP](https://github.com/L337-org/docker-mcp), [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy), and [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp). These are third-party projects; upstream APIs can change. Never publish loopback MCP endpoints without an authenticated tunnel or gateway.

**Additional source:** The workbench implementation is in `workbench/`; see [WORKBENCH_API.md](WORKBENCH_API.md). No physical hardware writes are exposed through the workbench MCP. Device-specific binary protocol claims must include evidence.

**Firmware acquisition:** The firmware downloader is intentionally an authenticated HTTP/UI/CLI write workflow rather than a general-purpose MCP URL-fetch tool. A human approves the source, and afterward read-only `workbench_list_firmware` and architecture/diff MCP tools can examine the downloaded image. See [Firmware acquisition](FIRMWARE_DOWNLOAD.md).

**New:** `scripts/check-mcp.py --json-out data/research/mcp-health.json` records live handshake/tool-list statuses. Research Hub reads this report via `/v1/mcp/health`. A configured MCP server does *not* count as working until a live handshake passes.
