---
name: device-ble-research
description: Collect repeatable BLE GATT observations.
---

# Collect repeatable BLE GATT observations

## Workflow

Record scan timestamps, advertised services, GATT reads, notifications and device state. Handle adapter/DBus permission errors as hardware limitations; maintain a comparison journal.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
