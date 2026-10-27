---
name: device-discovery
description: Baseline a previously unseen device on the network.
---

# Baseline a previously unseen device on the network

## Workflow

Select/create a device profile without activating DNS changes. Record MAC, locally assigned IP, traffic destinations, ports, mDNS/SSDP and BLE advertisements. Document what actually appeared, not vendor assumptions.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
