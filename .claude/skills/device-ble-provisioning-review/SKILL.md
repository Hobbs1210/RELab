---
name: device-ble-provisioning-review
description: Review vendor provisioning workflows before trying writes.
---

# Review vendor provisioning workflows before trying writes

## Workflow

Identify firmware revision and GATT services. Review any external provisioning implementation and cryptographic format. Require explicit approval before pairing, credential transmission or writing characteristics; capture outcome and rollback.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
