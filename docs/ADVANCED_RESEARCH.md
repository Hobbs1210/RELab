# Advanced research stack — 13 requested enhancements

This package is intentionally **device-agnostic**. Built-in profile `generic` is selected by default and makes no automatic DNS changes.

## What is shipped (honest capability levels)

| Requested # | Feature | Implementation | Status/limitation |
|---|---|---|---|
| 1 | Universal protocol engine | `workbench/engine.py` + declarative `protocols/*.json`; framed raw, delimiter, length prefix, MQTT fixed header, CoAP header and gRPC framing | Working offline parser **primitives**, not full vendor decoders; adding a plugin requires an operator-reviewed declarative config |
| 2 | Unified timeline | `workbench/timeline.py`, `/v1/timeline`, dashboard view | Correlates emulator HTTP + Zeek DNS/conn/SSL/HTTP logs and imported BLE/USB/serial observation JSONL; live hardware sniffing is not automatic |
| 4 | Automatic protocol inference | `/v1/infer` from HTTP request IDs, `/v1/infer/hex` for opaque binary messages | Conservative candidate prefix, length, delimiter, entropy, JSON; no verified semantic reconstruction |
| 8 | Hardware/network fuzzing | Bounded `boofuzz` emulator target; separate opt-in USB serial fuzz profile | Physical serial fuzzing explicitly gated; no autonomous BLE/JTAG/flashing or third-party network targeting |
| 10 | Interactive protocol workbench | UI + JSON API on 127.0.0.1:8310 | Decode frames, infer fields, compare firmware, review timeline, generate SDK previews |
| 19 | Binwalk v3 | Optional `firmware` Compose profile with source-built Rust Binwalk v3 and basic extractors | Needs substantial one-time build; not all extractor helpers installed |
| 20 | Firmware architecture detection | ELF machine identification, candidate signatures for PE, WebAssembly and filesystem formats | Raw proprietary images may have no recognizable architecture signature |
| 21 | Firmware version comparison | SHA256 full-file hashes, byte ranges for first 2 MiB of both files | Doesn't claim semantic disassembly/function changes; use Ghidra for follow-up |
| 22 | Firmware emulation | Optional Renode and QEMU user-mode images | Requires supported architecture and CPU/board/peripheral model; no out-of-box universal image boot |
| 23 | SBOM/vulnerability analysis | Syft/Grype Compose profiles | SBOM meaningful when firmware contents contain recognizable packages; Grype DB update needs outbound access |
| 26 | Stateful protocol fuzzing | `fuzz/run.py` boofuzz multi-node setup/action state machine with bounded cases | Only tests the local lab emulator by default; results in `data/fuzz/` |
| 32 | Custom hardware MCP tools | Read-only inventory endpoint exposed as `workbench_hardware_inventory` | USB/tty sysfs inspection; no hardware writes or radio access from MCP |
| 36 | Integration SDK generation | Candidate OpenAPI 3.1 + Python, TypeScript, C# client source generators | Scaffolds for HTTP observations only, not proven vendor SDKs |

## Start the default environment

```sh
bash scripts/setup.sh
python3 scripts/validate-project.py
python3 scripts/check-mcp.py
```

Open the primary mock backend at `http://127.0.0.1:8090` and **protocol workbench** at `http://127.0.0.1:8310`.

The workbench MCP is `http://127.0.0.1:8310/mcp`. Alongside the original 7 registered MCPs, there are 8 registrations total (Ghidra remains optional); six original services plus the new workbench start by default. Registered endpoints are not proof of live startup.

## Interactive decoding / inference

```sh
curl 'http://127.0.0.1:8310/v1/protocols'
curl 'http://127.0.0.1:8310/v1/decode?protocol=example-len16&hexdata=0003616263'
curl 'http://127.0.0.1:8310/v1/infer/hex?samples=0003616263,000378797a'
curl 'http://127.0.0.1:8310/v1/timeline?limit=50'
```

To activate a new **declarative** adapter, create e.g. `protocols/my-device.json` with `{"id":"my-device","framing":"length-prefix","length_bytes":2,"byteorder":"big"}` and restart not required (configs reloaded on each query). No dynamic Python code is loaded from adapters. API POST `/v1/protocols` also supports authenticated registration; MCP has read-only access.

Use `/v1/infer?ids=1,2` to infer from recorded emulator request bodies. Use `/v1/infer/hex?samples=<hex1>,<hex2>` to infer from arbitrary manually extracted binary messages. Use `/v1/hardware` for read-only USB and TTY inventory.

### Hardware event import (timeline)

The core network timeline receives Zeek and HTTP events automatically. To correlate independently captured BLE, USB or serial events, import an observation with its timestamp. This is **not** a live hardware sniffer:

```sh
# Requires X-Lab-Token from the untracked .env; run from a trusted host only.
TOKEN=$(sed -n 's/^LAB_ADMIN_TOKEN=//p' .env)
curl -fsS -X POST http://127.0.0.1:8310/v1/hardware-events \
  -H "X-Lab-Token: $TOKEN" -H 'Content-Type: application/json' \
  -d '{"time":"2026-01-01T12:00:00Z","kind":"ble","source":"controller-lab","fields":{"state":"connected"}}'
```

The local observation journal is at `data/workbench/hardware-events.jsonl`. Synchronize clocks across capture devices before drawing conclusions.

## Firmware processing — optional (never runs automatically)

Put an **authorized** firmware image in `firmware/`, for example `firmware/test.bin`.

```sh
# Rust Binwalk v3; builds a heavyweight optional image.
docker compose --profile firmware build binwalk
# Passive scan
docker compose --profile firmware run --rm binwalk test.bin
# Attempt extraction into data/firmware-extracted/session/ (untrusted content)
docker compose --profile firmware run --rm binwalk test.bin --extract

# Fast heuristic architecture identification in the workbench
curl http://127.0.0.1:8310/v1/firmware/test.bin/architecture
# Compare an old and new version (URL-encode names if needed)
curl 'http://127.0.0.1:8310/v1/firmware/compare?a=old.bin&b=new.bin'
```

Only the **first 2 MiB** are byte-compared. Full-file SHA-256 and full lengths are reported. Run extracted untrusted filesystem content only in a disposable offline virtual environment; do not mount untrusted `/etc`, executables, or firmware-extracted scripts into the host.

## SBOM + vulnerability scan

```sh
mkdir -p data/sbom
# Extracted directory (recognized packages only), output redirected on the host:
docker compose --profile sbom run --rm syft dir:/extracted/session -o syft-json > data/sbom/firmware.syft.json
# Grype needs its vulnerability DB; first scan fetches one if network is allowed:
docker compose --profile sbom run --rm grype sbom:/reports/firmware.syft.json -o json > data/sbom/firmware.grype.json
```

A successful scan with zero packages **does not** mean the firmware is safe. Third-party signatures and CVE matches need validation.

## Emulation (optional, not automatic firmware support)

```sh
# Requires a reviewed compatible script you created in firmware-tools/renode/
docker compose --profile emulation run --rm renode /work/my-board.resc

# Runs user-mode ARM/AArch64 Linux ELF only if ABI/libs are compatible:
docker compose --profile emulation run --rm qemu 'qemu-aarch64-static /firmware/your-aarch64-linux-elf'
```

Renode needs the appropriate `.resc` platform definition. QEMU user-mode doesn't model unknown hardware peripherals and cannot boot bare-metal firmware images by itself.

## Stateful and hardware fuzzing

```sh
# Bounded run against mock API:8000 only, no external targets.
docker compose --profile fuzz run --rm fuzz
```

To use **physical serial testing**, read `fuzz/README.md` and provide an operator-approved device mapped explicitly into the `fuzz-serial` profile. Its default device `/dev/null`, acknowledgement `DISABLED`, low case limit and 0.2 s minimum delay are intentional. No physical fuzzing occurs during normal startup. Don't fuzz equipment whose malfunction could cause physical harm.

## Protocol contract / candidate SDK generation

```sh
curl -fsS http://127.0.0.1:8310/v1/contracts/openapi > candidate-openapi.json
curl -fsS http://127.0.0.1:8310/v1/contracts/sdk/python > DeviceClient.py
curl -fsS http://127.0.0.1:8310/v1/contracts/sdk/typescript > DeviceClient.ts
curl -fsS http://127.0.0.1:8310/v1/contracts/sdk/csharp > DeviceClient.cs

# Optional authenticated file export inside data/workbench:
TOKEN=$(sed -n 's/^LAB_ADMIN_TOKEN=//p' .env)
curl -fsS -X POST -H "X-Lab-Token: $TOKEN" http://127.0.0.1:8310/v1/exports
```

Candidate OpenAPI is derived from the saved emulator HTTP journal. It cannot infer valid request schemas, certificates, authentication, response schemas, hidden state or actual API compatibility. Inspect all generated code and add authentication manually before use.

## Model/tool boundaries

- Workbench MCP is **read-only**: observation, decode, inference, hardware inventory, candidate contracts and SDK previews. Mutations require local REST auth token, independently of MCP.
- Original community DNS/mitmproxy MCPs may have write-capable tools: approve changes explicitly. Keep all MCP ports on loopback.
- Firmware parsing and fuzzing are **offline/opt-in** to reduce unintended side effects.
- The lab is not an exploit toolkit, and it does not automatically bypass device trust stores, vendor authentication, secure boot or certificate pinning.

Run `pytest -q tests` before changes. Docker image builds, MCP handshake and physical hardware features must be verified on an actual Linux host; CI/test results are not substitutes.
