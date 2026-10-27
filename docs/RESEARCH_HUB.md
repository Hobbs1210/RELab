# Integrated Research Hub (MVP)

This is a **general-purpose**, local-only evidence and experiment control plane. The original workbench, AdGuard, Zeek, mitmproxy, Ghidra, Binwalk, and existing device profiles remain independent. The new hub is the common place to **link the results**.

## Services and data

| Service | Function | Exposure |
|---|---|---|
| `research-db` | PostgreSQL projects/devices/evidence/jobs/outbox, survives restarts | Internal Docker network |
| `research-events` | NATS JetStream on `research.>` subjects | Internal Docker network |
| `research-worker` | Durable job polling; automatic firmware/mobile metadata jobs; HTTP + Zeek observation ingestion; event delivery | No host port |
| `research-hub` | FastAPI research dashboard, token-protected REST, read-only MCP | `127.0.0.1:8320` |

Metadata is linked in PostgreSQL and binary artifacts are deduplicated by SHA-256 at `data/research/objects/<first-two>/<sha256>`. Firmware imported from `firmware/` and capture files imported from `data/pcaps/` stay in their original locations. Research releases do not include their bytes. NATS is a delivery channel, while the DB queue and outbox are the system of record. If NATS is down, jobs still run and outbox items remain pending.

The bridge ingests HTTP metadata from `data/api/requests.db` and Zeek JSON logs from `data/analysis/*/{dns,ssl,conn}.log` into the **default** research project. It strips HTTP query strings and never reads request bodies, but captured metadata can still be sensitive. Manually link evidence to other projects via the authenticated API.

## CLI and API walkthrough

```bash
bash scripts/setup.sh
python3 scripts/researchctl.py list projects
python3 scripts/researchctl.py project demo 'Demo Research'
python3 scripts/researchctl.py device dev-001 'Test Device' --project demo
# Download approved firmware with scripts/download-firmware.py or place local file in firmware/
python3 scripts/researchctl.py import firmware firmware-v1.bin --project demo
python3 scripts/researchctl.py list jobs --project demo
python3 scripts/researchctl.py recipe firmware-intelligence --project demo --params '{"sha256":"YOUR_SHA256"}'
python3 scripts/researchctl.py recipe protocol-research --project demo --params '{"tcp_port":9000}'
python3 scripts/researchctl.py list evidence --project demo
```

**Research API:** `http://127.0.0.1:8320/docs`. Mutating requests require `X-Lab-Token: <private LAB_ADMIN_TOKEN from .env>`. Read operations support `project_id`. The MCP endpoint is `http://127.0.0.1:8320/mcp` and advertises only non-mutating research operations. Community MCP endpoints remain separately registered and should not be considered permission-equivalent.

## Integrated recipes and artifacts

- `firmware-intelligence`: heuristic firmware scan, endpoint strings, cross-layer correlations, Markdown report; `sha256` required.
- `protocol-research`: state-transition candidates, evidence correlations, Kaitai `.ksy` candidate, optional Lua dissector (`tcp_port` required), SDK/contract drafts, report.
- `session-replay`: deterministic offline replay against declarative transition table and report.
- `full-research`: tries each supported step, explicitly marking unsupported/missing-input steps **skipped**.

Jobs persist through worker restarts and have queued/running/succeeded/retry/failed/cancelled states, bounded retries, structured results, and events. Candidate code and reports are saved as deduplicated generated artifacts and included in research bundles. Optional Ghidra, Binwalk, Renode and other heavyweight profiles remain **manual tools**; this MVP does not automatically decompile or emulate unknown firmware hardware.

## Evidence correlation and clocks

The timeline supports `clock_source` and per-source offset/uncertainty records in milliseconds (`POST /v1/clocks`). Changes are applied to **displayed timestamps** and never modify raw event times. Domain matching is evidence of a shared identifier, **not proof of code execution or semantic causality**.

Record protocol messages through `POST /v1/evidence` with `fields.action` for offline replay, `fields.host/path/method` for candidate SDK generation, and a capture/firmware locator where possible. Evidence-backed agent memory requires existing evidence IDs for project-specific findings. `/v1/plans` provides deterministic next-step recommendations; it is not a deployed autonomous AI researcher.

## Experiments, approval and safety

`POST /v1/experiments` stores immutable offline emulation/replay/mutation inputs. `/v1/experiments/{id}/reproduce` re-queues the same inputs. `/v1/experiments/{id}/restore` resets **only the offline simulation** to its recorded initial state; it does not modify real devices, AdGuard or external APIs. General approval requests record a decision and **do not execute hardware mutations**. Those remain manual and explicit using their respective scoped tools.

Generated boofuzz-style mutation vectors are bounded to 100 **offline samples** in the Hub. Existing boofuzz tooling for the local emulator remains under the optional `fuzz` profile; physical-device fuzzing is never started automatically. Kaitai `.ksy`, Lua dissectors and C#/Python/TypeScript clients are candidates and require validation against actual traffic.

## Extcap and Android logs

- `tools/wireshark/extcap/device_re_pcap.py`: optional Wireshark extcap adapter to **replay a selected saved Ethernet PCAP file** from the capture directory, not a live radio sniffer. Install in your workstation's extcap directory, adjust `DEVICE_RE_CAPTURE_DIR`, and confirm compatibility with your Wireshark build.
- `tools/mobile/collect-logcat.sh DEVICE_SERIAL`: run on a workstation with Android platform-tools and a locally authorized test device. The script saves a private log to `data/mobile/`; import using `researchctl import mobile-log`. No USB passthrough or remote ADB access is enabled by default.

## Troubleshooting

```bash
docker compose ps
docker compose logs --tail=100 research-db research-events research-hub research-worker
python3 scripts/check-mcp.py --json-out data/research/mcp-health.json
python3 scripts/researchctl.py list jobs
```

Web/MCP APIs are intentionally loopback-only. For remote development, connect using VS Code Remote-SSH or SSH port forwarding; never publish port 8320 unauthenticated on the internet. `/v1/metrics` and event delivery statuses show queue activity and pending NATS delivery. Live Docker startup and device-specific compatibility must be verified on your Debian machine.
