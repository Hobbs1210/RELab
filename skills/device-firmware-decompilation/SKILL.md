---
name: device-firmware-decompilation
description: Analyze authorized firmware in offline Ghidra.
---

# Analyze authorized firmware in offline Ghidra

## Workflow

Hash firmware and place it in firmware/. Start optional Ghidra profile, inspect architecture and extraction format, invoke headless analysis. Attribute every finding to file hash and function/offset.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
