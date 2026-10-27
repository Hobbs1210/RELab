# Security and operational boundaries

- Test only devices, networks, firmware and APIs you own or have permission to investigate.
- `TARGET_PROFILE=generic` has no DNS rewrites. Profile files list candidate hosts, not automatic interception actions.
- Run services on an isolated SSID/VLAN. DNS 53 and HTTPS 443 bind to the addresses configured in `.env`; default `0.0.0.0` must be changed when the host is reachable outside the isolated lab.
- MCP endpoints are loopback-only but have different permissions: `device-api` is read-only, Docker MCP is read-only via a socket proxy, BLE writes default off; DNS/mitm upstream MCPs may modify external state.
- Authenticated REST control-plane modifications require a random secret from untracked `.env`. Do not paste the token into AI chats, issue trackers or commits. Do not share saved PCAPs or raw request bodies without sanitization.
- The synthetic HTTPS certificate is self-signed. It is not trusted by vendor hardware, and DNS redirection does not bypass TLS certificate validation.
- Packet captures, HTTP request journals and BLE notifications can contain credentials and personal data. Use storage quotas and retention, restrict file permissions, and never upload raw captures to public AI services.
- Optional capture uses host networking and NET_RAW; optional router nftables changes require `sudo`; optional Ghidra uses additional compute. These are not suitable on untrusted shared hosts.
- Community MCP image versions, CLI flags and capabilities may drift. Before device testing, run the setup, validate, handshake checks, inspect container logs, and audit the third-party code.
