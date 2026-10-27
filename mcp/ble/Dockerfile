FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libdbus-1-3 bluez ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'ble-mcp-server[http]==0.3.0'
EXPOSE 8000
