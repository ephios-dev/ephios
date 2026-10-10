#!/bin/bash

set -e

if [ "$1" == "run" ]; then
  python -m ephios migrate
  python -m ephios build
  exec supervisord -n -c /etc/supervisord.conf
fi

exec python -m ephios "$@"
