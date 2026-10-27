---
name: device-hardware-mcp-inventory
description: Inventory serial and USB adapters without hardware changes
---

# Device Hardware Mcp Inventory

Use device-workbench MCP workbench_hardware_inventory and check read-only sysfs data. No writing, flashing, GATT mutation, port opening or device resets are permitted through this tool; use the BLE MCP with separate authorization as necessary.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
