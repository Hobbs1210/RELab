# Firmware acquisition MVP

Download a **direct public HTTPS URL** of firmware that you are permitted to retrieve and investigate. This feature is acquisition and provenance tracking, **not** automatic firmware authenticity verification or extraction.

## Browser

Open the workbench at `http://127.0.0.1:8310` through SSH/VS Code forwarded ports. Enter a direct firmware HTTPS link, optional destination basename, and preferably the SHA-256 published by the vendor. Retrieve the private `LAB_ADMIN_TOKEN` from `.env` on your own trusted Debian host, enter it in the form, and select **Download firmware**. Keep the token out of chat messages and issue reports.

## CLI (no Docker required)

```bash
python3 scripts/download-firmware.py 'https://vendor.example/releases/device.bin' --name device-v1.bin
python3 scripts/download-firmware.py 'https://vendor.example/releases/device-v2.bin' --name device-v2.bin --sha256 '<64-hex-chars>'
```

The tool saves `firmware/device-v1.bin` and `firmware/device-v1.bin.json`, including bytes downloaded, SHA-256, timestamp and source host/path. URLs' query strings are not saved (they may contain credentials). The `firmware/` directory is ignored by Git and source packaging. **No files are automatically executed or flashed.**

## HTTP API

`POST http://127.0.0.1:8310/v1/firmware/download` with `X-Lab-Token` and JSON:

```json
{"url":"https://vendor.example/device.bin", "filename":"device-v1.bin", "sha256":"<64-hex-chars>"}
```

Omit the optional `sha256` if none is available. Write endpoints require the admin token. The MCP workbench remains read-only; operators may use the UI, CLI, or REST after approval. Read-only MCP agents can subsequently list and analyze downloaded files.

## Security controls and limitations

- HTTPS on **port 443 only**, valid TLS server certificate, **no ambient HTTP(S) proxy**.
- Rejects local, private, reserved or non-global DNS results and literal addresses. DNS resolution is validated and connection is pinned to validated IPs for each URL/redirect.
- Up to four redirects, each validated; downloaded body ≤100 MiB, streaming with a read timeout.
- Exclusive output creation; refuses an existing filename. Metadata records digest and final public host/path, not sensitive query strings.
- Rejects HTML content to avoid silently storing a landing page.
- A SHA-256 match shows the downloaded bytes match the *supplied* digest, not that the digest was authentic. Confirm vendor signatures and publisher identity separately.
- No Git LFS integration, private network firmware servers, insecure HTTP mirrors, or arbitrary URL fetches. For private vendor servers, download the firmware through a separately trusted channel and copy it into `firmware/` manually.

Next: `docker compose --profile firmware run --rm binwalk ...` or read-only Ghidra analysis, after verifying format, checksum and origin.
