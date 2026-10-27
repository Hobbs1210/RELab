---
name: device-firmware-acquisition
description: Retrieve and register authorized public firmware safely with the workbench and CLI.
---
# Firmware acquisition

1. Confirm rights to retrieve and analyze the firmware.
2. Prefer vendor-published direct HTTPS URLs and a published digest or signature.
3. Obtain operator approval before a download; do not leak URLs with signed query parameters or `LAB_ADMIN_TOKEN`.
4. Use `python3 scripts/download-firmware.py URL [--name BASENAME] [--sha256 HASH]` or the authenticated firmware workbench UI.
5. Never overwrite files, use private network SSRF destinations, disable TLS certificate checks, execute downloads, or flash devices automatically.
6. Record SHA-256 and provenance and distinguish a digest match from authentic publisher identity.
7. Use read-only MCP tools to list, analyze and compare downloaded images with evidence-backed findings.

See docs/FIRMWARE_DOWNLOAD.md and SECURITY.md.
