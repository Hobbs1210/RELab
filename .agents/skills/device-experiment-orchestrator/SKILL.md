---
name: device-experiment-orchestrator
description: Run hypothesis-driven tests with snapshots and rollback.
---

# Run hypothesis-driven tests with snapshots and rollback

## Workflow

Name the hypothesis, start via scripts/labctl.py, record baseline and target profile, change one variable with approval, capture+analyze, compare, finish, and rollback. Separate observable changes from conclusions.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
