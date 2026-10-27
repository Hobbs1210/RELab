FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends tshark ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'mcp-wireshark==0.5.0' 'mcp-proxy==0.13.0'
WORKDIR /captures
EXPOSE 8000
