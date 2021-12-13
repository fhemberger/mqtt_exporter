FROM python:3.10.1-alpine

LABEL org.opencontainers.image.title=mqtt_exporter
LABEL org.opencontainers.image.description="Prometheus exporter for MQTT."
LABEL org.opencontainers.image.vendor="Frederic Hemberger"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.source=https://github.com/fhemberger/mqtt_exporter

WORKDIR /usr/src/app

RUN adduser --system --no-create-home --shell /usr/sbin/nologin mqtt_exporter
COPY *.py requirements-frozen.txt ./
COPY utils ./utils
RUN pip install --no-cache-dir -r requirements-frozen.txt

USER mqtt_exporter


EXPOSE 9344
ENTRYPOINT [ "/usr/local/bin/python3", "-u", "/usr/src/app/mqtt_exporter.py" ]
