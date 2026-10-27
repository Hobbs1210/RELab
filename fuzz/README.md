# Bounded stateful fuzzing

`docker compose --profile fuzz run --rm fuzz` exercises the local FastAPI emulator only. All fuzz traffic is constrained to Compose's `api:8000`; modifying the hostname or port fails closed. The example uses a two-step setup/action state machine, boofuzz persistence, a maximum of 100 cases (configurable up to 1000) and no remote device access. The REST emulator will likely respond 501 to unknown paths; those results do not imply a vulnerability.

A physical device requires a separately reviewed transport adapter, an operator-controlled hardware route, a precise device allowlist, an approved protocol model, and recovery procedures. No autonomous hardware fuzzing, flashing or BLE/GATT writes are enabled by default.

## Physical serial device (opt-in)

Set `SERIAL_FUZZ_DEVICE=/dev/ttyUSB0` in `.env` and `SERIAL_FUZZ_ACK=I_OWN_THIS_DEVICE` **only after reviewing the device and message seed**. Then use:

```bash
docker compose --profile fuzz-hardware run --rm fuzz-serial --seed-hex 01020304 --cases 5 --delay 0.5 --confirm
```

Default is `/dev/null` and `DISABLED`, which prevents hardware mutation. Never use on an unsafe physical process, production equipment, or a connected vehicle. Serial data formats, checksums, session state, and device reset logic are deliberately **not inferred**. The operator must supply a harmless seed from an authorized development device. Serial hardware passthrough and permissions vary by Linux host.
