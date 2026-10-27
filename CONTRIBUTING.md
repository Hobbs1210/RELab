# Contributing

Thanks for contributing to Device RE Lab. This is a research platform, **not** a library of unauthorized device exploits.

## Before submitting a pull request

1. Open an issue describing the device-independent use case and expected behavior.
2. Add a test with synthetic fixtures, not real device data or real API tokens.
3. Run `python3 -m pip install -r requirements-dev.txt`, `python3 scripts/validate-project.py`, and `python3 -m pytest -q tests/`.
4. If Docker is installed, run `docker compose config -q`, `bash scripts/smoke-test.sh`, and `python3 scripts/check-mcp.py`. Report which tests could not run.
5. Update the README and related docs, including the adapter/MCP security boundary.

## Security and privacy

Never commit proprietary firmware images, encryption keys, session tokens, device IDs, IPs of private networks, or packet captures containing other people's data. Prefer tiny synthetic binary fixtures. New write-capable MCP tools require scoped permissions and explicit operator approval; keep default interfaces read-only. For vulnerabilities, see [SECURITY.md](SECURITY.md).

## Style

Python 3.12+ for the application; shell scripts use `set -euo pipefail`. Keep Docker services optional where they need hardware or heavyweight emulation. Give every protocol claim a capture ID or firmware offset, and clearly mark hypotheses. Third-party containers retain their respective licenses.
