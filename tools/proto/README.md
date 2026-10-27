# Protobuf / binary protocol hypotheses

Protocol Buffers are not appropriate for every device. When a confirmed raw
protobuf payload is recovered (after removing verified transport framing), run:

```bash
protoc --decode_raw < message.bin
# When an actual schema is known:
protoc --proto_path=./schemas --decode=some.package.Message ./schemas/message.proto < message.bin
```

Do not assume field numbers or message types before obtaining evidence. Save the
source PCAP SHA-256 and the offset of every extracted payload.
