# Workbench REST and MCP contract

Loopback base: `http://127.0.0.1:8310`.

Read-only endpoints (also individually exposed through MCP):

- `GET /v1/health` lab metadata.
- `GET /v1/protocols` declarative decoder registry.
- `GET /v1/decode?protocol=mqtt&hexdata=3003616263` frame analysis.
- `GET /v1/infer?ids=1,2` hypotheses from stored emulator request bodies.
- `GET /v1/infer/hex?samples=0003616263,000378797a` hypotheses from generic binary samples.
- `GET /v1/timeline?limit=200&src=IP_OR_NAME&analysis_id=ID` merged captured events.
- `GET /v1/hardware`, `/v1/hardware/usb`, `/v1/hardware/serial` read-only USB and TTY info from mounted sysfs. Each has a separate read-only MCP tool.
- `GET /v1/firmware` available firmware filenames.
- `GET /v1/firmware/FILE/architecture` signature/candidate ISA.
- `GET /v1/firmware/compare?a=FILE&b=FILE` hash + first-2MiB change ranges.
- `GET /v1/contracts/openapi` versioned candidate OpenAPI 3.1.
- `GET /v1/contracts/sdk/{python|typescript|csharp}` generated source preview.

Authenticated mutations (NOT exposed through MCP):

- `POST /v1/protocols` with JSON adapter and `X-Lab-Token`. Declarative framing only; no code import.
- `POST /v1/hardware-events` imports an operator-supplied BLE/USB/serial timestamped observation JSON object. It does **not** send packets.
- `POST /v1/exports` saves an OpenAPI candidate and three SDK sources under `data/workbench/`.

Hardware MCP limitation: USB/tty listing does not enumerate BLE GATT or query live device registers. The separate BLE MCP handles Bluetooth radio requests, with writes disabled by default. All direct hardware writes, serial fuzzing, target network fuzzing, router modification and firmware flashing require a separate explicit operator workflow.

The user-facing workbench UI is at `/`. Its forms only issue GET read calls. Firmware parsing loads only basenames from the read-only firmware bind mount, not arbitrary host filesystem paths.
