FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
ENV PYTHONDONTWRITEBYTECODE=1
RUN useradd --uid 10001 --create-home lab
USER lab
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
