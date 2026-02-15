# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.10.0-python3.14-trixie-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_DEV=1

WORKDIR /usr/src/ephios

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
            gettext \
            supervisor \
            locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN dpkg-reconfigure locales && \
	locale-gen C.UTF-8 && \
	/usr/sbin/update-locale LANG=C.UTF-8

ENV PATH=/root/.local/bin:$PATH
RUN uv tool install gunicorn

RUN mkdir -p /var/ephios/data/ && \
    mkdir -p /var/log/supervisord/ && \
    mkdir -p /var/run/supervisord/

COPY . /usr/src/ephios
RUN uv sync --locked --all-extras

COPY deployment/docker/entrypoint.sh /usr/local/bin/ephios
RUN chmod +x /usr/local/bin/ephios

COPY deployment/docker/supervisord.conf /etc/supervisord.conf
COPY deployment/docker/cron.sh /usr/local/bin/cron.sh
RUN chmod +x /usr/local/bin/cron.sh

ENTRYPOINT ["ephios"]
CMD ["run"]
HEALTHCHECK CMD curl -f http://localhost:80/healthcheck || exit 1
