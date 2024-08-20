#!/bin/sh
APP_ROOT='/usr/local/haskala'
SETTINGS=${DJANGO_SETTINGS_MODULE:-haskala.settings.dev}
cd "$APP_ROOT"
./manage.py collectstatic --clear --noinput --settings="$SETTINGS"
./manage.py migrate --settings="$SETTINGS"
gunicorn --workers 8 \
         --log-level DEBUG \
         --env DJANGO_SETTINGS_MODULE="$SETTINGS" \
         -u django -g django \
         -b 0.0.0.0:8000 \
         haskala.wsgi:application
cd - 2>&1
