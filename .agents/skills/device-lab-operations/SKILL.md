---
name: device-lab-operations
description: Troubleshoot Compose services and research pipeline.
---

# Troubleshoot Compose services and research pipeline

## Workflow

Check docker compose ps, container logs, health endpoint, free ports 53/443, packet analyzer, and MCP handshake. Avoid destructive docker cleanup or socket access changes without permission.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
