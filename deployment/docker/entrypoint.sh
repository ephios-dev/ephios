#!/bin/bash

set -e

if [ "$1" == "run" ]; then
  python manage.py migrate
  python manage.py collectstatic --no-input
  python manage.py compilemessages
  python manage.py compilejsi18n
  exec supervisord -n -c /etc/supervisord.conf
fi

exec python manage.py "$@"
