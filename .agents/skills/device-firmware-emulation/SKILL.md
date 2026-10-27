---
name: device-firmware-emulation
description: Prepare hardware-specific firmware emulation with Renode or QEMU
---

# Device Firmware Emulation

First confirm executable architecture and ABI, then choose Renode board model or QEMU user-mode binary. See docs/ADVANCED_RESEARCH.md; there is no universal emulation. Use network_mode:none and no host device mounts for untrusted firmware.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
