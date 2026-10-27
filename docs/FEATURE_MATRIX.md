# Requested capability map (numbers from feature discussion)

**Legend:** Integrated MVP = implemented and covered by offline tests; Candidate = heuristic / draft requiring human verification; Optional adapter = host hardware/external binary required; Partial = a deliberately bounded subset, not a production-complete engine.

| # | Requested feature | Implemented component | Maturity / limit |
|---|---|---|---|
| 1 | Unified research database | PostgreSQL ORM: projects, devices, artifacts, evidence, links, jobs, clocks | Integrated MVP |
| 2 | Event-driven architecture | Transactional event outbox to NATS JetStream; automated import analysis | Integrated MVP (single worker) |
| 3 | Persistent job orchestrator | PostgreSQL queue, retries, restart recovery, cancellation of pending jobs | Integrated MVP (no workflow distribution/priority) |
| 4 | Automatic research pipelines | Named recipes with ordered steps, skipped-step reporting | Partial (heavyweight external tools remain manual) |
| 7 | Unified observability | `/v1/metrics`, durable events, worker logs, MCP handshake report | Partial (no OTLP collector) |
| 8 | Projects and workspaces | Project-scoped evidence, devices, artifacts, jobs, client CLI | Integrated MVP (single-user auth) |
| 9 | Cross-layer correlation | Firmware endpoint strings ↔ observed hostnames ↔ evidence IDs | Candidate (matching ≠ causality) |
| 10 | State machine discovery | Adjacent observed protocol events → candidate transitions | Candidate (sequence ≠ protocol proof) |
| 11 | Kaitai Struct integration | `.ksy` generator for raw / BE length-prefixed framing | Candidate (no compiler bundled) |
| 12 | Virtual device emulator | Offline declarative transitions/response history | Partial (not generic live TCP/USB emulator) |
| 14 | Firmware intelligence | Format/URL/hostname extraction, SHA-256 linkage, version comparisons in workbench | Partial (Binwalk/Ghidra opt-in) |
| 15 | Mobile companion analysis | Local ADB logcat collector + bounded log metadata indexing | Partial (no full Android emulator) |
| 16 | Wireshark dissector generation | Candidate Lua TCP-port dissector output in job results | Candidate (manual validation) |
| 17 | Deterministic replay | Recorded evidence actions against in-process state machine | Integrated offline MVP (not network-level timing replay) |
| 18 | Intelligent mutation | Bounded deterministic bit mutation, isolated emulator testing | Partial (heuristic, no arbitrary target mutation) |
| 19 | Unified MCP research server | `device-research` read-only Streamable HTTP /mcp | Integrated MVP; live handshake unverified here |
| 20 | AI research planner | `/v1/plans` evidence-guided recommended next steps | Partial deterministic heuristics (not LLM agent) |
| 21 | Evidence-aware agent memory | Findings with project and evidence IDs, status, text search | Integrated MVP (no embeddings) |
| 22 | Investigation reports | Evidence citations, confidence/locator Markdown | Integrated MVP |
| 23 | AI-assisted protocol implementation | Candidate OpenAPI + Python/TypeScript/C# HTTP clients, emulation recipe | Partial; generated SDKs unverified |
| 24 | Approvals and rollback | Token-protected decision log; immutable offline experiment reset | Partial; no automatic physical/DNS rollback from hub |
| 25 | MCP registry and health | 9 IDE configs; live `scripts/check-mcp.py --json-out` report | Integrated MVP; requires running servers |
| 29 | Device topology | Evidence-linked device IP → endpoint graph | Integrated MVP for observed endpoints |
| 30 | Capture time sync | Source offset/uncertainty normalization in timeline | Integrated MVP (manual calibration) |
| 31 | Wireshark extcap | Saved-PCAP external source script | Optional adapter, Ethernet-only |
| 32 | Research recipes | Firmware, protocol, replay, full research | Integrated MVP; bounded stages |
| 38 | One-click experiment reproduction | Immutable offline experiment snapshot and rerun API | Integrated offline MVP |
| 39 | Research bundles | ZIP with manifest, report, generated candidate artifacts | Integrated MVP; raw firmware and PCAP excluded |

**Not claimed:** universally decoding encrypted vendor protocols, automatic Google certificate trust bypass, running Renode on arbitrary firmware without a board model, full mobile dynamic instrumentation, physically safe fuzzing without device-specific safeguards, or a complete multi-user authorization layer.
