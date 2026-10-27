---
name: device-stateful-protocol
description: Model ordered request-response protocols using scenarios.
---

# Model ordered request-response protocols using scenarios

## Workflow

Define config/scenarios.json steps by method, host and path; test a multi-step session by source IP with synthetic clients, reset only the intended session, and record sequence mismatches.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
