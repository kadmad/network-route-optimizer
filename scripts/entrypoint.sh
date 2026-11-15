#!/bin/sh
# Container entrypoint: optionally apply migrations, then hand over to the CMD (PID 1 = gunicorn).
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

exec "$@"
