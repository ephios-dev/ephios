#!/bin/bash

set -e

if [ "$1" == "run" ]; then
  python manage.py migrate
  python manage.py build
  exec supervisord -n -c /etc/supervisord.conf
fi

exec python manage.py "$@"
