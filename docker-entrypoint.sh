#!/bin/sh
set -eu

mkdir -p /data

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec uvicorn deareditors.asgi:application \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips="*"
