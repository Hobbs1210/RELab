FROM zeek/zeek:lts
USER root
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 tshark binutils file && rm -rf /var/lib/apt/lists/*
COPY analyze.py /opt/lab/analyze.py
CMD ["python3", "/opt/lab/analyze.py", "watch"]
