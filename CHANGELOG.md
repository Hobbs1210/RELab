## Unreleased — Integrated Research Hub (MVP)

- Added PostgreSQL research projects, project-linked devices, hashed artifacts and evidence.
- Added NATS JetStream event transport with durable SQL outbox and queued, retried worker jobs.
- Added named research recipes, heuristic firmware intelligence, protocol-state inference, Kaitai KSY and Wireshark Lua candidates, offline replay/mutation, API client drafts and report bundles.
- Added data bridges for existing mock API journal and Zeek JSON logs; metadata-only import with redaction of URL query strings.
- Added new localhost Research Hub dashboard, read-only MCP integration, VS Code/Codex/Antigravity registrations, CLI, skill pack and feature implementation matrix.
- Added mobile logcat importer, saved-PCAP Wireshark extcap adapter, manual capture time offsets, topology and offline experiment reproduction.
- Unverified in this environment: full Debian Docker builds, NATS deliveries and live MCP tool handshakes.

# Changelog

## Unreleased — Public repository preparation

- Headless Debian 12/13 installer using Docker's official apt repository and existing OpenSSH accounts.
- VS Code Remote-SSH developer setup and safe localhost-first port binding.
- Firmware acquisition from direct public HTTPS URLs in web workbench and CLI, with size limits, checksums and provenance metadata.
- Additional public-source documentation, security policy, contribution guide, license and sanitized source release packaging.
- No additional device-specific DNS rules or backend implementations enabled by default.

## Previous research prototype

- Network capture, DNS, TLS diagnostics, BLE, protocol workbench, optional firmware tooling and experimental MCP integrations.
