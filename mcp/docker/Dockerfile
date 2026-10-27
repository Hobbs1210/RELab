FROM python:3.14-slim

# Install mcp-proxy and docker-mcp-server into separate virtual environments
# to prevent conflicting mcp SDK versions (mcp-proxy requires mcp<2, docker-mcp-server requires mcp>=2.1.0).
RUN python -m venv /opt/mcp-proxy \
 && /opt/mcp-proxy/bin/pip install --no-cache-dir 'mcp-proxy==0.13.0'

RUN python -m venv /opt/docker-mcp \
 && /opt/docker-mcp/bin/pip install --no-cache-dir 'docker-mcp-server==2.2.9'

ENV PATH="/opt/mcp-proxy/bin:/opt/docker-mcp/bin:${PATH}"
EXPOSE 8000
