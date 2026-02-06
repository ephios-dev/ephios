#!/bin/bash

set -e

if [ "$1" == "run" ]; then
  uv run manage.py migrate
  uv run manage.py build
  exec supervisord -n -c /etc/supervisord.conf
fi

exec uv run manage.py "$@"
