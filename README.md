# RELab — Device Reverse Engineering Lab

**A self-hosted, extensible research lab for analyzing devices, firmware, and network protocols.**

[![CI](https://github.com/Hobbs1210/RELab/actions/workflows/validate.yml/badge.svg)](https://github.com/Hobbs1210/RELab/actions/workflows/validate.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE) [![Debian](https://img.shields.io/badge/Debian-12%20%7C%2013-A81D33)](./docs/DEBIAN_INSTALL.md)

[RELab](https://github.com/Hobbs1210/RELab) brings network captures, controlled DNS rewriting, BLE observations, firmware inspection, protocol decoding, API simulation and repeatable experiments together in one Docker Compose project. **The integrated Research Hub** adds PostgreSQL-backed projects, durable jobs, NATS events, linked evidence, recipes, and a unified MCP API. It also includes **MCP integrations** and workspace configurations for **VS Code, Codex and Google Antigravity**.

> **Status: research prototype.** Individual features and Python tests have been implemented, but full multi-container deployment and physical-device compatibility must be verified on your own host. Third-party MCP interfaces are independently maintained. This project does not automatically break TLS, decode every protocol, or emulate every device.

## What you can do

| Area | Available capabilities | Where |
|---|---|---|
| Observe | DNS query logging, TCP/UDP PCAP, mitmproxy flows, Zeek offline analysis | AdGuard, capture, mitmweb, `analysis/` |
| Understand | Unified timeline, binary framing, field inference, architecture detection, firmware comparison | Protocol workbench |
| Experiment | Local mock API, stateful response scenarios, test baselines/rollback | Lab dashboard |
| Firmware | **Download from a public HTTPS URL**, verify optional SHA-256, inspect with Binwalk / Ghidra, optional QEMU / Renode, Syft / Grype | Workbench + optional profiles |
| Hardware | BLE GATT discovery and read-only USB/serial inventory | BLE profile + workbench |
| Integrate | Read-only MCP research APIs and third-party DNS/proxy/PCAP/BLE/Docker tools | MCP endpoints, IDE configs |
| Develop | Headless Debian installer, SSH remote workspace, Python tests, agent skills | `scripts/`, `.vscode/`, `.agents/skills/` |
| Research Hub | Projects, device records, content-addressed artifacts, linked findings, deterministic offline replay, job queue, report bundles, MCP | `http://127.0.0.1:8320`, `research-hub/` |

Some capabilities require real hardware, appropriate network visibility, or compatible firmware models. The optional services are **not** needed for ordinary use. See [Advanced Research](docs/ADVANCED_RESEARCH.md).

## Source repository

**GitHub:** https://github.com/Hobbs1210/RELab  
**Issues:** https://github.com/Hobbs1210/RELab/issues  
**Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)  
**Installation:** [docs/DEBIAN_INSTALL.md](docs/DEBIAN_INSTALL.md)

Clone the repository with its hidden VS Code, MCP, Codex, Antigravity, and GitHub configuration files intact:

```bash
git clone https://github.com/Hobbs1210/RELab.git
cd RELab
```

If you're initializing this GitHub repository from the downloadable full-source ZIP instead, use the **[publishing guide](docs/PUBLISHING.md)**. The ZIP includes every source file and dotfolder required for development, but no `.git` history or local runtime data.

## One-command bootstrap: headless Debian 12/13

**You do not need to install Git or clone the repository first.** Once this ZIP has been pushed to the public [`Hobbs1210/RELab`](https://github.com/Hobbs1210/RELab) repository's `main` branch, connect to your Debian host with an existing non-root user and run:

```bash
curl -fsSLo /tmp/relab-bootstrap.sh \
  https://raw.githubusercontent.com/Hobbs1210/RELab/main/scripts/bootstrap-debian.sh
# Review the downloaded installer before giving it root privileges.
less /tmp/relab-bootstrap.sh
sudo bash /tmp/relab-bootstrap.sh --user "$USER"
```

The bootstrap installs Git and prerequisites, **clones the repository into `/opt/RELab`**, and invokes the headless Debian installer. That installer sets up Docker Engine and Compose, OpenSSH, Python and other dependencies; starts the default RELab services; and installs **code-server**, a browser-based VS Code-compatible editor, configured to **open `/opt/RELab` automatically**. It listens only on `127.0.0.1:8443` on Debian, so reach it through an SSH tunnel:

```bash
# Run on your laptop (replace the hostname):
ssh -L 8443:127.0.0.1:8443 YOUR_USER@YOUR_DEBIAN_IP
# Browse http://127.0.0.1:8443
```

To see your browser editor password on Debian, run `sudo cat /home/YOUR_USER/.config/relab-code-server/config.yaml` (keep it private). For **desktop VS Code**, install VS Code and its **Remote - SSH** extension on your laptop, connect to Debian, and open `/opt/RELab`; desktop VS Code is not installed on the headless host. These are two independent ways to edit the same Git checkout.

To bind only the device-facing DNS/HTTPS services to an existing, isolated lab-network address (rather than localhost), pass `--lab-ip`:

```bash
sudo bash /tmp/relab-bootstrap.sh --user "$USER" --lab-ip 192.168.50.20
```

This IP must actually be assigned to the host. Research dashboards and MCP services remain loopback-bound. The installer doesn't change your router, firewall rules, or SSH authentication settings and does not grant Docker group access by default. Optional flags include `--skip-code-server`, `--skip-docker-install`, `--grant-docker-access` (root-equivalent access), `--skip-update`, and `--no-start`.

**Important:** The raw GitHub URL cannot work until you have committed `scripts/bootstrap-debian.sh` to `main`. See the [Debian installation guide](docs/DEBIAN_INSTALL.md) for reruns, debugging, and remote IDE setup. Prefer downloading and inspecting the script instead of executing unreviewed `curl | bash` pipelines.

### Existing Linux Docker host (no OS installation)

```bash
cp .env.example .env
bash scripts/setup.sh
python3 scripts/validate-project.py
python3 scripts/check-mcp.py
bash scripts/smoke-test.sh
```

The first run generates random admin secrets in the untracked `.env`. Commands requiring live Docker will only pass after images build and services start. For slow/expensive optional services, use Compose profiles selectively.

## Dashboard and workspace

| Service | Local URL / interface |
|---|---|
| Research dashboard | `http://127.0.0.1:8090` |
| Universal protocol workbench | `http://127.0.0.1:8310` |
| **Integrated research hub** | **`http://127.0.0.1:8320`** |
| mitmproxy browser | `http://127.0.0.1:8081` |
| AdGuard setup/admin | `http://127.0.0.1:3000` |
| MCP research APIs | `http://127.0.0.1:8090/mcp`, `http://127.0.0.1:8310/mcp` |

**VS Code from your laptop:** install the **Remote - SSH** extension, choose `Remote-SSH: Connect to Host...`, connect to your Debian account, and open `/opt/RELab`. Forward ports `8090`, `8310`, and `8320` in VS Code's **Ports** panel. No desktop UI or VS Code installation is required on Debian. Use workspace tasks, debugger configuration and MCP registrations. [Full VS Code/SSH guide](docs/IDE.md).

Codex reads `.codex/config.toml` and `AGENTS.md`; Antigravity reads `.agents/mcp_config.json` and `.agents/skills/`. If the agent is running on your **laptop** instead of the remote host, forward its required loopback MCP ports through SSH. [MCP guide](docs/MCP.md).

## Download firmware from a link (MVP)

Use the browser at `http://127.0.0.1:8310` → **Download public firmware**, enter a direct HTTPS download URL and the write token from the server's private `.env`. Add the vendor-published SHA-256 when possible. The operation is deliberately **not** exposed as an unauthenticated MCP mutation.

Or download on the Debian host without starting Docker:

```bash
python3 scripts/download-firmware.py \
  'https://downloads.vendor.example/device/firmware-v1.bin' \
  --name firmware-v1.bin \
  --sha256 'REPLACE_WITH_VENDOR_PUBLISHED_64_DIGIT_SHA256'
```

Omit `--sha256` if you have no vendor-provided hash; the resulting hash still identifies what you downloaded but cannot prove its origin. Files land in untracked `firmware/` with metadata in `firmware/<name>.json`. The tool only supports public HTTPS on port 443, validates each redirect, rejects local/private address resolution, limits downloads to 100 MiB, and never overwrites a filename. Signed firmware URLs can have secret query parameters—don't paste them into issue reports or agents. [Firmware acquisition guide](docs/FIRMWARE_DOWNLOAD.md).

## Normal research flow

```bash
# Start with a profile that changes nothing.
python3 scripts/device-profile.py list
python3 scripts/device-profile.py show generic

# Optional: capture only on a gateway/TAP/mirrored interface; set TARGET_IP in .env first.
docker compose --profile capture up -d capture
bash scripts/analyze-now.sh

# Track test evidence and restore controlled lab state.
python3 scripts/labctl.py start 'Initial boot' 'Baseline observed behavior'
python3 scripts/labctl.py list
```

`profiles/generic.json` has **no DNS rewrites**. Stadia and local-test example profiles are optional; no vendor domains are spoofed automatically. You must explicitly choose an isolated test network and authorize DNS changes. Packet captures and third-party firmware are **never included in source releases**.

## Integrated research workflow (new)

The default stack now starts a **PostgreSQL research database, NATS JetStream event broker, Research Hub API and persistent worker**. Existing captures and HTTP request logs remain available in their original stores; the worker imports metadata with stable IDs into the evidence index. New firmware downloaded through the workbench is automatically registered in the default research project when the hub is reachable.

```bash
# Create an investigation and register a device (no network configuration changes)
python3 scripts/researchctl.py project thermostat "Thermostat investigation"
python3 scripts/researchctl.py device controller "Controller" --project thermostat

# Place authorized firmware in firmware/, then import and automatically scan it:
python3 scripts/researchctl.py import firmware device-v1.bin --project thermostat
python3 scripts/researchctl.py list jobs --project thermostat

# Run a protocol recipe; useful even with only manually imported observations.
python3 scripts/researchctl.py recipe protocol-research --project thermostat
python3 scripts/researchctl.py list evidence --project thermostat

# Verify all default MCP handshakes and retain an operational report:
python3 scripts/check-mcp.py --json-out data/research/mcp-health.json
```

The Research Hub exposes a **read-only MCP endpoint** at `http://127.0.0.1:8320/mcp`; write actions require a local `X-Lab-Token` and are not part of this default MCP tool list. Research recipes perform bounded offline analysis and report skipped steps when required inputs are missing. Read [Integrated Research Hub](docs/RESEARCH_HUB.md) and the [feature implementation map](docs/FEATURE_MATRIX.md) before running experiments.

## Optional Compose profiles

| Profile | Use | Extra requirements |
|---|---|---|
| `capture` | Packet capture | Linux host gateway/TAP/SPAN and selected test-device IP |
| `ble` | BLE utilities | Linux BlueZ/DBus and supported radio |
| `ghidra` | Headless firmware decompilation and MCP | Significant memory/storage; optional binary URL |
| `firmware` | Binwalk v3 | Separate build, untrusted firmware input |
| `emulation` | QEMU / Renode | Appropriate CPU, board definitions or models |
| `sbom` | Syft / Grype | SBOM inputs; vulnerability DB download |
| `fuzz` | Local emulator fuzzing | Explicit bounded campaign |
| `fuzz-hardware` | Physical serial fuzzing | Explicit allowlist/acknowledgment, owned target only |

See [Advanced Research](docs/ADVANCED_RESEARCH.md) and [MCP server reference](docs/MCP.md) for exact commands and current limitations.

## Architecture

```text
           Device on isolated test network
                         |
                   Lab gateway / TAP
                         |
              optional DNS / packet capture
                         |
                   HTTPS test edge
                         |
              mitmproxy -> mock FastAPI
                         |
         request journal / experiments / PCAPs
                         |
        PostgreSQL + NATS + durable research worker
                         |
     Projects / content hashes / evidence / jobs / plans
                         |
   +---------------------+----------------------+
   | Protocol workbench  | Firmware tool profiles |
   +---------------------+----------------------+
                         |
        Unified Research MCP + scoped tool MCP servers / Codex / Antigravity / VS Code
```

DNS redirection is **not** HTTPS decryption; proprietary certificate validation and encrypted transports can prevent message inspection. Evidence, hypotheses and test outcomes should be clearly distinguished.

## Safety, reliability and public repository notes

- **Authorization:** test only your own devices, networks and firmware, or those you are authorized to research. Do not enable global DNS rewrites by accident.
- **Security boundary:** UIs/MCP bind to loopback; mutation endpoints require a private token. Community MCP services have different capabilities and need independent review.
- **Sensitive content:** `.env`, packet captures, certificates, local databases, downloaded firmware and extraction outputs are excluded from source control and release archives.
- **Validation:** `python3 -m pytest -q tests/`, `python3 scripts/validate-project.py`, `docker compose config -q`, `python3 scripts/check-mcp.py` (live), `bash scripts/smoke-test.sh` (live).
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) · **License:** [MIT](LICENSE) for this repository's original source; third-party tools retain their own licenses. **Disclosure:** [SECURITY.md](SECURITY.md).

Full documentation: [Debian installation](docs/DEBIAN_INSTALL.md) · [IDE setup](docs/IDE.md) · [Firmware](docs/FIRMWARE_DOWNLOAD.md) · [Experiments](docs/EXPERIMENTS.md) · [Protocol APIs](docs/WORKBENCH_API.md) · [Security](docs/SECURITY.md).

---

Source: [github.com/Hobbs1210/RELab](https://github.com/Hobbs1210/RELab) · [Report an issue](https://github.com/Hobbs1210/RELab/issues/new/choose) · [Security policy](SECURITY.md)
