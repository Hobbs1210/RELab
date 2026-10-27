# Publishing RELab on GitHub

Target repository: **https://github.com/Hobbs1210/RELab**

## Starting with the full-source ZIP

The release archive contains a single `RELab/` folder, including `.github/`, `.agents/`, `.codex/`, `.vscode/`, `.devcontainer/`, `.cursor/`, `.claude/` and all project source code. It does **not** include `.git/`, local secrets, certificates, device captures, downloaded firmware, or database content.

If the GitHub repo is empty, extract the ZIP, then run:

```bash
unzip RELab-github-ready.zip
cd RELab
git init -b main
git remote add origin https://github.com/Hobbs1210/RELab.git
git add -A
git status --short
git commit -m "Initial public RELab release"
git push -u origin main
```

Before the push, inspect `git status` and `git diff --cached --stat` (and optionally `git diff --cached`) to verify no private information is included. GitHub will require an appropriate account login or credential manager; do not put tokens in scripts or remote URLs.

If the repository **already has commits**, clone it first and copy the extracted `RELab/` *contents including dotfiles* into your cloned checkout. Review changes and commit normally; do **not** force-push or overwrite unrelated project history. A typical example on Linux/macOS:

```bash
git clone https://github.com/Hobbs1210/RELab.git relab-checkout
unzip RELab-github-ready.zip
cp -a RELab/. relab-checkout/
cd relab-checkout
git status
git add -A
git commit -m "Add integrated Device RE Lab"
git push
```

## Before making it public

- Read [SECURITY.md](../SECURITY.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).
- Verify archive integrity with `unzip -t RELab-github-ready.zip` and SHA-256 supplied alongside the archive.
- Run `python3 -m pip install -r requirements-dev.txt`, `python3 scripts/validate-project.py`, and `python3 -m pytest -q tests/`.
- If Docker is available, run `cp .env.example .env && docker compose config -q`, then live smoke/MCP tests on a dedicated host.
- Configure GitHub Actions and branch protections according to your review policy.
- Never attach raw PCAPs, credentials, personal device data, downloaded proprietary firmware, `.env`, or private keys to an issue or release.

## Headless Debian deployment

After the code is in GitHub:

```bash
git clone https://github.com/Hobbs1210/RELab.git
cd RELab
sudo bash scripts/install-debian.sh --user "$USER"
```

The installer deploys to `/opt/RELab`; this installation path does not need to match the GitHub repository name. The first install is not equivalent to a verified production deployment: test Docker services, MCP handshakes, and any hardware adapters on the actual target host.

## Verify the one-command bootstrap after publishing

The bootstrap URL only resolves once the source files are on GitHub's `main` branch. On the Debian host, download and inspect it before executing:

```bash
curl -fsSLo /tmp/relab-bootstrap.sh https://raw.githubusercontent.com/Hobbs1210/RELab/main/scripts/bootstrap-debian.sh
less /tmp/relab-bootstrap.sh
sudo bash /tmp/relab-bootstrap.sh --user "$USER"
```

This clones `/opt/RELab`, installs the headless stack, and sets up code-server to open `/opt/RELab` automatically through an SSH tunnel. Do not expect GitHub raw URLs to work until the ZIP has been committed and pushed.
