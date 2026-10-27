---
name: device-dns-test
description: Plan and safely execute DNS rewrite experiments.
---

# Plan and safely execute DNS rewrite experiments

## Workflow

Show selected profile first, inspect AdGuard queries, and verify exact hostnames. Plan a change only for the lab-owned rewrite set. Ask approval; use enable-rewrites.sh LAB_IP PROFILE. Undo with disable-rewrites.sh PROFILE.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
