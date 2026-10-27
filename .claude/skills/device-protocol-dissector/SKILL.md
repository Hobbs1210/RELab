---
name: device-protocol-dissector
description: Create a candidate Wireshark dissector for an observed binary protocol.
---

# Create a candidate Wireshark dissector for an observed binary protocol

## Workflow

Inspect packet framing and device firmware evidence. Start from tools/wireshark/device_candidate.lua. Only bind to a validated port. Document unknown fields and keep decode assertions reversible.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
