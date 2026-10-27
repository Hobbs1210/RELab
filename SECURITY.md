# Security policy

## Reporting a vulnerability

Please **do not** publish exploit details or real capture data in a public issue. If the project is hosted on GitHub with private vulnerability reporting enabled, use the repository **Security → Report a vulnerability** feature. Otherwise contact the repository maintainer privately through the hosting service. No public security-contact email is promised.

## Deployment boundaries

This application is a research environment, not a hardened internet-facing service. Use an isolated lab VLAN/SSID. The headless Debian installer binds DNS/HTTPS to **127.0.0.1** unless an explicit private lab-interface IP is selected. All control dashboards and MCP services bind to localhost. Access remotely through SSH tunnels or VS Code Remote-SSH.

`LAB_ADMIN_TOKEN` protects the HTTP mutation endpoints; MCP endpoints supplied by third parties can have their own permissions. Do not share `.env`, raw logs, captures, or unredacted firmware URLs. `--grant-docker-access` explicitly grants root-equivalent Docker privileges to the SSH user. Ensure operator approval before experimenting with external devices, DNS routing, GATT writes, firmware programming, or fuzzing.

Firmware downloads allow HTTPS public addresses on port 443 only, with redirects revalidated, DNS connections pinned, no HTTP proxies, and maximum 100 MiB per download. Checksums can verify transferred bytes but **not** establish firmware publisher authenticity. Download only firmware you are permitted to possess and analyze.

See [docs/SECURITY.md](docs/SECURITY.md) for detailed component boundaries and limitations. Public release checks are a best-effort audit, not a comprehensive penetration test or vulnerability clearance.
