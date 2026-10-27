---
name: device-sbom-vulnerabilities
description: Produce firmware package inventories and vulnerability scan reports
---

# Device Sbom Vulnerabilities

Prefer extracted filesystem trees, then run Syft to generate Syft JSON and Grype on the SBOM. Validate package detection and DB age; an empty SBOM does not indicate safety. Review each CVE hit for applicability to the firmware build.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
