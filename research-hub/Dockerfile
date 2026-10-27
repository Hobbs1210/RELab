FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
COPY ui.html ./
RUN useradd -u 10001 -r -m researcher
USER researcher
CMD ["uvicorn", "research_api:app", "--host", "0.0.0.0", "--port", "8000"]
