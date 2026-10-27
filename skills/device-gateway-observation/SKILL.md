---
name: device-gateway-observation
description: Establish safe traffic visibility on a Linux lab gateway.
---

# Establish safe traffic visibility on a Linux lab gateway

## Workflow

Verify host actually forwards/mirrors device traffic; default to observe mode. To redirect plaintext DNS only, print a gateway-dns.sh plan for a single TARGET_IP and LAB_IP; only apply after explicit approval.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
