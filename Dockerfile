# syntax=docker/dockerfile:1
FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_VERSION=1.6.1

WORKDIR /usr/src/ephios

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
            gettext \
            cron \
            supervisor \
            locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN dpkg-reconfigure locales && \
	locale-gen C.UTF-8 && \
	/usr/sbin/update-locale LANG=C.UTF-8

RUN pip install "poetry==$POETRY_VERSION" gunicorn

RUN mkdir -p /var/ephios/data/ && \
    mkdir -p /var/log/supervisord/ && \
    mkdir -p /var/run/supervisord/

COPY . /usr/src/ephios
RUN poetry install -E pgsql -E redis -E mysql

COPY deployment/docker/entrypoint.sh /usr/local/bin/ephios
RUN chmod +x /usr/local/bin/ephios

COPY deployment/docker/cronjob /etc/cron.d/ephios-cron
COPY deployment/docker/supervisord.conf /etc/supervisord.conf
COPY deployment/docker/cron.sh /usr/local/bin/cron.sh
RUN chmod +x /usr/local/bin/cron.sh

ENTRYPOINT ["ephios"]
CMD ["run"]