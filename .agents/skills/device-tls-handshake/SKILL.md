---
name: device-tls-handshake
description: Investigate certificate and TLS negotiation without guessing.
---

# Investigate certificate and TLS negotiation without guessing

## Workflow

Examine SNI, ALPN, chain issuer, TLS versions and errors with capture/TShark; use the synthetic -k smoke test only for lab plumbing. DNS redirection cannot defeat TLS verification.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
