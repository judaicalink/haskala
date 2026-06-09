FROM python:3.12-bookworm

# Application user
RUN useradd --create-home --shell /bin/bash haskala

# HTTP port
EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# System dependencies for Wagtail, Pillow, the database client, GeoDjango
# (libgdal for django-leaflet) and the asset pipeline. Node 22 comes
# from NodeSource — the Debian-bookworm package is Node 18, which can't
# `require()` an ES Module, and our sass dependency pulls in
# chokidar@4 which is ESM-only.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    gnupg2 \
    curl \
    ca-certificates \
    build-essential \
    libpq-dev \
    libmariadb-dev-compat \
    libmariadb-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    libgdal-dev \
    gdal-bin \
    cron \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install --yes --quiet --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Application server is installed via requirements.txt (the explicit
# gunicorn pin used to live here, but the old release pulled pkg_resources
# from setuptools which is no longer available by default on Python 3.14).

# Daily RDF export cronjob.
RUN echo "0 0 * * * /usr/local/bin/python /app/manage.py export_rdf" > /etc/cron.d/export_rdf \
 && chmod 0644 /etc/cron.d/export_rdf \
 && crontab /etc/cron.d/export_rdf

# Python dependencies.
COPY requirements.txt /
RUN pip install -r /requirements.txt

WORKDIR /app

# Source code, owned by the application user.
COPY --chown=haskala:haskala . .
RUN chown -R haskala:haskala /app

USER haskala

# Build the front-end theme.
RUN npm install
RUN npm run copy:icons
RUN npm run build:css
RUN npm run build:js

# Collect static files into STATIC_ROOT.
RUN python manage.py collectstatic --noinput --clear

# The database dump is loaded by the postgres container via
# /docker-entrypoint-initdb.d on first boot (see docker-compose.yml).
# Migrations live in the repository and are applied at container start.

CMD set -xe; \
    python manage.py migrate --noinput; \
    exec gunicorn --bind 0.0.0.0:8000 --workers 3 --access-logfile - haskala.wsgi:application
