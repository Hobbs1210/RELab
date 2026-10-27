---
name: device-tls-probing
description: Differentiate DNS reachability, TCP setup, TLS and HTTP failures.
---

# Differentiate DNS reachability, TCP setup, TLS and HTTP failures

## Workflow

Run each layer as a separate experiment: target DNS logs, SYN, ClientHello, certificate validation, HTTP journal. Document first failing layer and only retest a single variable.

## Evidence & safety

Operate only on devices and networks you own or have permission to test. Persist relevant observations and reversible changes. Do not invent a device protocol or bypass TLS validation based on DNS alone.
