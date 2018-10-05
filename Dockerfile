FROM python:3.7-alpine

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pagespeed_exporter ./

ENTRYPOINT ["/usr/bin/env", "python", "-m" "pagespeed_exporter"]