# syntax=docker/dockerfile:1
FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_VERSION=1.6.1

WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
            gettext \
            locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* \
RUN dpkg-reconfigure locales && \
	locale-gen C.UTF-8 && \
	/usr/sbin/update-locale LANG=C.UTF-8 \
RUN mkdir -p /data/static/
RUN pip install "poetry==$POETRY_VERSION" gunicorn

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
RUN poetry install -E pgsql -E redis -E mysql
# COPY most content after poetry install to make use of caching
COPY . /app

COPY deployment/docker/ephios-docker.env /app/.env
COPY deployment/docker/entrypoint.sh /usr/local/bin/ephios
RUN chmod +x /usr/local/bin/ephios
ENTRYPOINT ["ephios"]
CMD ["gunicorn"]