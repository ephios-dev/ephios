#!/bin/bash

NUM_WORKERS_DEFAULT=$((2 * $(nproc --all)))
export NUM_WORKERS=${NUM_WORKERS:-$NUM_WORKERS_DEFAULT}

python manage.py migrate
python manage.py collectstatic --no-input
python manage.py compilemessages
python manage.py compilejsi18n

echo "Starting" "$@"

if [ "$1" == "gunicorn" ]; then
    exec gunicorn ephios.wsgi \
        --name ephios \
        --workers $NUM_WORKERS \
        --max-requests 1000 \
        --max-requests-jitter 100
fi

exec python manage.py "$@"
