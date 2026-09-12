#!/bin/sh
set -eu

mkdir -p /data

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn deareditors.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-1}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
