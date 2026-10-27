---
name: device-binwalk3
description: Inspect firmware with Binwalk v3 in an isolated container
---

# Device Binwalk3

With an authorized firmware image in firmware/, use docker compose --profile firmware run --rm binwalk <basename>. Use --extract only when approved and inspect data/firmware-extracted/session. Always hash original input; extraction signatures are not proof of architecture or integrity.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
