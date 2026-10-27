FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    adb python3 python3-pip python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' 'mcp<2,>=1.12.0' 'fastapi-mcp==0.4.0'
COPY server.py /app/server.py
WORKDIR /app
ENV PATH=/venv/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

