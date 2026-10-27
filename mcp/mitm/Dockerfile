FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
# Review upstream changes when upgrading. Native MCP addon must be loaded by mitmweb.
ARG MITM_MCP_REF=master
RUN git clone --depth 1 https://github.com/lups2000/mitmproxy-MCP.git /opt/mitmproxy-mcp \
 && cd /opt/mitmproxy-mcp && pip install --no-cache-dir "mitmproxy>=12.2.1" "mcp>=1.27.0" \
 && python -m compileall -q /opt/mitmproxy-mcp
RUN mkdir -p /home/mitmproxy
ENV HOME=/home/mitmproxy PYTHONPATH=/opt/mitmproxy-mcp
EXPOSE 8080 8081 8000
