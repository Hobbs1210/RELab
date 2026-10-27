---
name: device-ble-discovery
description: Identify BLE adapters, advertisers, services and GATT characteristics.
---

# Identify BLE adapters, advertisers, services and GATT characteristics

## Workflow

Use BlueZ and BLE MCP to list adapters and scan only the test device. Enumerate discovered UUIDs, properties, characteristic reads and notify behavior. Never assume a UUID meaning without evidence.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
