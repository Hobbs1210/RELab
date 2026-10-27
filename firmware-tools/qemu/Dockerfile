FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends qemu-user-static file binutils && rm -rf /var/lib/apt/lists/*
RUN useradd -u 10001 -m lab
USER lab
