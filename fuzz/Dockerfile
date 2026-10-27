FROM python:3.12-slim
RUN pip install --no-cache-dir boofuzz==0.4.2 pyserial==3.5
WORKDIR /app
COPY run.py serial_fuzz.py ./
RUN useradd --uid 10001 --create-home lab
USER lab
ENTRYPOINT ["python","run.py"]
