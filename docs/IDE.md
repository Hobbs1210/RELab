# VS Code, Codex, Antigravity and other IDEs

## Preferred development: VS Code Remote-SSH to the Linux Docker server

Install Remote-SSH, Python, Python Debugger, Docker/Containers, YAML, Codex or GitHub Copilot. Connect to the Linux host, open **`/opt/RELab`** (not just an SSH terminal), and run **Terminal → Run Task → Device: Setup (first run)**. Inspect the Tasks menu for validation, Compose logs, capture and tests.

MCP is configured at `.vscode/mcp.json`. Use the VS Code MCP server management UI to verify each endpoint. If Copilot discovers the portable `.mcp.json` too, disable the duplicate registrations. The FastAPI debugger config runs a separate development API instance; do not confuse it with Docker's port 8090.

## Browser-based editor (code-server)

`bootstrap-debian.sh` installs a separate `relab-code-server` systemd service and opens `/opt/RELab` as the default workspace. It binds to the Debian loopback interface on port 8443. From your laptop, run `ssh -L 8443:127.0.0.1:8443 USER@DEBIAN_IP` and visit `http://127.0.0.1:8443`. View the locally generated password in `~/.config/relab-code-server/config.yaml` on Debian. `sudo systemctl status relab-code-server` provides service health. Some proprietary desktop VS Code extensions may not be available in code-server; use desktop VS Code + Remote-SSH when needed.

## Codex

Open the same trusted workspace in Codex CLI or the VS Code Codex extension. The project `.codex/config.toml` registers `device-*` MCP endpoints. `codex mcp list` shows registrations; `python3 scripts/check-mcp.py` establishes live tool discovery independently. Reusable skills are in `.agents/skills/`, and agent instructions are in `AGENTS.md`.

## Google Antigravity

Open the same workspace in Antigravity. `.agents/mcp_config.json` defines the nine endpoints using `serverUrl`. `.agents/skills/` contains the same generic skills. Use its MCP management UI to test connection status and schemas.

## Remote MCP ports from a local agent

Local `127.0.0.1` is relative to the machine running the agent. If Docker is remote but the agent runs on a laptop, forward necessary ports via SSH:

```bash
ssh -N -L 8090:127.0.0.1:8090 -L 8301:127.0.0.1:8301 \
  -L 8302:127.0.0.1:8302 -L 8303:127.0.0.1:8303 \
  -L 8304:127.0.0.1:8304 -L 8305:127.0.0.1:8305 \
  -L 8310:127.0.0.1:8310 -L 8320:127.0.0.1:8320 user@LINUX_HOST
```

Optional Ghidra: add `-L 8306:127.0.0.1:8306`. Do not forward DNS/53 or device-facing HTTPS/443 to normal internet interfaces.

The optional `.devcontainer/devcontainer.json` uses `--network=host`, which is Linux-specific and may conflict with your host ports; prefer Remote-SSH for initial setup. Always run `python3 scripts/device-profile.py list` and confirm `TARGET_PROFILE` before any DNS experiment.

## Headless Debian installer and firmware acquisition

The curl-driven, Git-cloning Debian bootstrap and the reproducible deployment path are in [DEBIAN_INSTALL.md](DEBIAN_INSTALL.md). The installer enables `openssh-server` on Debian but does not modify sshd authentication policies; use an existing authorized SSH user and SSH key. The workspace root is `/opt/RELab` by default.

Remote-SSH starts a VS Code Server on Debian automatically; you do not install desktop VS Code there. If device MCP endpoints run on Debian, open the **remote** VS Code workspace so their loopback addresses resolve correctly. For local Codex or Antigravity sessions, see the explicit SSH forwarding examples above. An SSH login user is not automatically in the root-equivalent `docker` group; either use `sudo` or explicitly opt in when installing.

Firmware downloads are available from the workbench UI and `scripts/download-firmware.py`; see [FIRMWARE_DOWNLOAD.md](FIRMWARE_DOWNLOAD.md). The privileged download operation is not exposed as a default MCP tool.

## Research Hub

Use VS Code task **Research: Tests** for SQLite integration tests, **Research: MCP verification & save report** to query live MCP tool lists, or **Research: Show persistent worker** for NATS/outbox and job logs. Port-forward 8320 for the research dashboard. `python3 scripts/researchctl.py` works inside Remote-SSH.
