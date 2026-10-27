---
name: device-packet-forensics
description: Perform offline PCAP protocol analysis with TShark.
---

# Perform offline PCAP protocol analysis with TShark

## Workflow

Use read-only captures. Report timestamp, 5-tuple, DNS/SNI, TLS metadata, UDP, STUN or other observed protocols. Avoid transmitting raw traffic to external services.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
