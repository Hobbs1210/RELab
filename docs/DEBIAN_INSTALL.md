# Headless Debian deployment (12 Bookworm / 13 Trixie)

Use a dedicated host or VM on an isolated lab network. Required: Debian 12/13, a **non-root user**, working apt networking, sudo/root access, and recommended 4+ GB RAM (significantly more for Ghidra). VS Code runs on your laptop, **not** on Debian.

## 1. SSH access

If already connected by SSH you can keep using that session. The installer installs `openssh-server` and enables the `ssh` service; it does **not** change passwords, disable root login, authorize keys, alter firewalls, or open external ports. Use SSH public keys and host-specific firewall rules. Test a second SSH session before modifying SSH settings.

## 2. Bootstrap from GitHub (no manual clone)

After the full RELab source ZIP has been published to `https://github.com/Hobbs1210/RELab` on `main`, download the bootstrap script and inspect it:

```bash
curl -fsSLo /tmp/relab-bootstrap.sh https://raw.githubusercontent.com/Hobbs1210/RELab/main/scripts/bootstrap-debian.sh
less /tmp/relab-bootstrap.sh
sudo bash /tmp/relab-bootstrap.sh --user "$USER"
```

This works on a fresh Debian 12/13 installation with `curl` installed and sudo/root privileges. If curl is not installed yet, first run `sudo apt-get update && sudo apt-get install -y curl`. The script checks whether the `re` user exists, creates it if missing, and configures full passwordless root escalation (`re ALL=(ALL:ALL) NOPASSWD: ALL` in `/etc/sudoers.d/re`). The `--user` parameter defaults to `re` (or the invoking `SUDO_USER`). The bootstrap installs Git and certificates, clones RELab into `/opt/RELab`, and calls `scripts/install-debian.sh`, which installs Docker Engine/Compose v2, OpenSSH Server, Python, code-server, and the default Compose services. It is safe to rerun: the Git checkout fast-forwards if there are no tracked local edits; existing `.env`, capture files, downloaded firmware, and research data are preserved. Use `--skip-update` to preserve local tracked edits without Git updates.

To bind **only the isolated device-facing ports** (53 TCP/UDP DNS and 443 TCP HTTPS) to a private address already configured on the host:

```bash
sudo bash /tmp/relab-bootstrap.sh --user "$USER" --lab-ip 192.168.50.20
```

The bootstrap intentionally rejects public IPs and addresses that aren't on the host. Default is localhost-only, so other devices cannot reach its DNS/HTTPS service until you opt in. Research APIs and MCP endpoints remain loopback-only either way. The installer does **not** configure DHCP, Wi-Fi, or packet routing.

Other flags accepted by the bootstrap:

```text
--user USER                    Linux/SSH account (default: re or SUDO_USER)
--re-password PASS             Password for re user & lab apps (default: securely generated)
--ssh-key "KEY"                Authorize public SSH key for re user (e.g. "ssh-ed25519 ...")
--copy-ssh-id                  Copy deploying user's ~/.ssh/authorized_keys to user re
--install-dir /opt/RELab       Default Git working tree and deployment folder
--grant-docker-access          Add account & re user to Docker group (opt-in)
--skip-docker-install          Require Docker Engine/Compose already installed
--skip-code-server             Skip browser-based VS Code editor
--skip-update                  Preserve existing checkout without git fetch
--no-start                     Install and prepare services but don't launch Compose
```

### Automated Pre-flight and Guardrails

* **Hardware & Pre-flight Checks**: Warns if system RAM is below 4 GB (recommended for containerized research and Ghidra) or available disk space is under 10 GB.
* **Port 53 Resolution**: Detects `systemd-resolved` stub listeners on port 53 and configures `DNSStubListener=no` with upstream fallback nameservers so AdGuard Home can bind port 53 without Docker errors.
* **Unattended Apt Guardrails**: Packages install non-interactively with `-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"` to avoid hanging headless setups.
* **Safe Atomic Updates**: Changes to `.env` create `.env.bak` and write to a temporary file before atomic renaming, protecting against interrupted installs.
* **Unified Application Credentials**: A strong password is automatically generated (or passed via `--re-password`) for the `re` user, applied to Linux system login via `chpasswd`, browser code-server, and AdGuard Home (`ADGUARD_USERNAME=re`). A clean credentials banner is displayed at the end of the installation.

Docker uses the official Debian apt repository. Installer reruns preserve untracked local `.env`, firmware and capture data. Docker group access is **not** granted automatically. For an existing, locally extracted checkout, you can instead invoke `sudo bash scripts/install-debian.sh --user "$USER"` directly.

### Browser VS Code that opens RELab automatically

The installer starts a systemd service named `relab-code-server` as your SSH user, bound to `127.0.0.1:8443`. It runs `code-server ... /opt/RELab`, so the web editor opens the Git working tree by default. Forward the port from your laptop:

```bash
ssh -L 8443:127.0.0.1:8443 YOUR_USER@YOUR_DEBIAN_IP
# In your laptop browser: http://127.0.0.1:8443
```

The password is in the SSH user's `~/.config/relab-code-server/config.yaml` (mode `0600`). It is generated on first install and not re-created on reruns. Don't expose port 8443 or MCP endpoints to the public internet. This is **code-server**, not Microsoft's desktop VS Code; Remote-SSH is the preferred setup for full desktop VS Code features.

## 3. Open in VS Code

On the laptop, install VS Code and **Remote - SSH**. Add a host to the local `~/.ssh/config`:

```ssh-config
Host device-re-lab
    HostName YOUR_DEBIAN_IP_OR_HOSTNAME
    User YOUR_DEBIAN_USERNAME
    IdentityFile ~/.ssh/id_ed25519
```

Run `Remote-SSH: Connect to Host...` → `device-re-lab`, then `File → Open Folder...` → `/opt/RELab`.

Use VS Code **Ports** panel to forward `8090`, `8310`, `8081` and whichever MCP ports your local editor agent needs. If the AI agent runs **inside the remote session**, its `127.0.0.1` references already point to the Debian host and extra forwarding is unnecessary. Optional Dev Container support exists but Remote-SSH is the recommended first setup.

## 4. Validate and operate

```bash
cd /opt/RELab
sudo docker compose ps
sudo docker compose logs --tail=100
python3 scripts/validate-project.py
python3 scripts/check-mcp.py
bash scripts/smoke-test.sh
```

If Docker access was granted, you may omit `sudo`. Note that live MCP tests require all default services to start successfully. Docker images and third-party dependencies may require manual adjustments. To stop:

```bash
sudo docker compose down
```

`down` does not remove bind-mounted data; **do not use `down -v` casually**. To upgrade, pull a reviewed release or update the repository and re-run the installer, then inspect the Compose changes before rebuilding.

## 5. Network and security

Only the designated lab VLAN/SSID should use this DNS or HTTPS interception endpoint; never expose these services to the public internet. Docker-managed firewall rules can bypass simplified host firewalls; enforce segmentation at the physical/virtual gateway. Use SSH tunnels for dashboards and MCP. The system does not bypass vendor TLS trust or impersonate remote services without protocol work.

## 6. Decommission and cleanup

To tear down RELab and restore system defaults (systemd-resolved port 53 stub, code-server unit, sudoers rule):

```bash
# Preview actions without modifying system
sudo bash scripts/uninstall-debian.sh

# Apply teardown (preserves captures and database)
sudo bash scripts/uninstall-debian.sh --apply

# Full teardown including workspace purge
sudo bash scripts/uninstall-debian.sh --apply --purge-data
```
