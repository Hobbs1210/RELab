---
name: device-profile-authoring
description: Create safe reusable profiles for new devices.
---

# Create safe reusable profiles for new devices

## Workflow

Copy profiles/generic.json to a new normalized ID. Document hardware, candidate DNS names, protocol hints and firmware keywords; validate with device-profile.py. Profiles are opt-in and never enable rewrites on their own.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
