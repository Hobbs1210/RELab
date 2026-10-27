FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libyara-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' 'mcp<2,>=1.12.0' 'fastapi-mcp==0.4.0' 'yara-python>=4.5.0'
COPY server.py /app/server.py
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

