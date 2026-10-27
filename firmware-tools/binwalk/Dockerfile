# Binwalk v3 CLI from crates.io; full recursive extraction benefits from extra external tools.
FROM rust:1-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends pkg-config libssl-dev liblzma-dev clang libclang-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
RUN cargo install binwalk --locked
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates file xz-utils gzip bzip2 unzip p7zip-full cpio squashfs-tools zstd libssl3 liblzma5 zlib1g && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/cargo/bin/binwalk /usr/local/bin/binwalk
COPY entrypoint.sh /usr/local/bin/scan-firmware
RUN chmod +x /usr/local/bin/scan-firmware && useradd -u 10001 -m lab
USER lab
ENTRYPOINT ["/usr/local/bin/scan-firmware"]
