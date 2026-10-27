---
name: device-sdk-scaffolding
description: Generate research-only candidate SDKs from observed HTTP calls
---

# Device Sdk Scaffolding

Use workbench_generate_candidate_openapi and workbench_generate_candidate_sdk tools to preview C#, Python and TypeScript sources; inspect observed operation IDs; never call this a verified vendor SDK. Compare generated code to captures, add authentication, schemas, error handling and contract tests before use.

## Evidence and permissions

Prefer offline evidence, hashes, event IDs and a reproducible experiment. Keep the `generic` profile active until the operator explicitly selects a device. Follow AGENTS.md and docs/SECURITY.md for all network interception or hardware mutation.
