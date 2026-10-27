# Device RE Lab — phases 0 to 4

| Phase | Generalized implementation | Limitations requiring real hardware |
|---|---|---|
| 0 — repair | NGINX → mitmproxy reverse → FastAPI; authorized REST mutations, scoped AdGuard rewrite ownership, offline tests | Build all external images and perform live MCP tool-list checks |
| 1 — observation | optional device-IP-scoped Linux host tcpdump, isolated gateway DNS/53 nftables plan/apply/remove, controlled DNS profiles | Host must actually route/mirror selected target traffic; DoH/DoT not covered |
| 2 — analysis | Zeek/TShark indexing; TLS/STUN/DTLS metadata; file hashes; firmware strings; optional Ghidra MCP | Firmware format/CPU must be identified; metadata does not expose encrypted messages |
| 3 — protocol hypotheses | configurable response rules, ordered per-source API scenarios, delays, offline rule replay, BLE discovery, candidate Lua dissector, protobuf workflow notes | No universal BLE provisioning, trusted HTTPS proxy certificate or vendor protocol emulation |
| 4 — reproducible AI research | experiment journal, snapshots, compare, rollback, report generator, MCP/IDE/skills, CI, read-only agent interface | Privileged actions need explicit operator approval |

## Network modes

**Observe:** Default. On an authorized Linux gateway or TAP, set `TARGET_IP` in `.env` and run `docker compose --profile capture up -d capture`.

**Redirect selected DNS:** Run `scripts/gateway-dns.sh plan TARGET_IPV4 LAB_GATEWAY_IPV4`; apply only with operator approval, then `scripts/gateway-dns.sh remove --apply` to undo the dedicated nftables table. The port-53 redirect is scoped to one device and is not effective against encrypted DNS protocols.

**Inspect synthetic HTTPS:** NGINX terminates HTTPS with a self-signed test certificate, forwards HTTP to mitmproxy reverse mode, then FastAPI. `scripts/smoke-test.sh` exercises this synthetic path; a real device may reject the certificate before sending any API call.

The optional `ghidra` Compose profile is heavy and not part of default startup. Ghidra MCP configured in IDE files may therefore be disconnected by design.
