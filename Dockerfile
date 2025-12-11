# Use an official Python runtime based on Debian 10 "buster" as a parent image.
FROM python:3.14-rc-bookworm

# Add user that will be used in the container.
RUN useradd wagtail

# Port used by this container to serve HTTP.
EXPOSE 8000

# Set environment variables.
# 1. Force Python stdout and stderr streams to be unbuffered.
# 2. Set PORT variable that is used by Gunicorn. This should match "EXPOSE"
#    command.
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system packages required by Wagtail and Django.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    gnupg2 \
    ca-certificates \
    build-essential \
    libpq-dev \
    libmariadb-dev-compat \
    libmariadb-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    cron \
    nodejs \
    npm \
 && rm -rf /var/lib/apt/lists/*

# Install the application server.
RUN pip install "gunicorn==20.0.4"

# Create cronjob
RUN echo "0 0 * * * /usr/local/bin/python /app/manage.py export_rdf" > /etc/cron.d/export_rdf \
 && chmod 0644 /etc/cron.d/export_rdf \
 && crontab /etc/cron.d/export_rdf

# Install the project requirements.
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Use /app folder as a directory where the source code is stored.
WORKDIR /app

# Set this directory to be owned by the "wagtail" user. This Wagtail project
# uses SQLite, the folder needs to be owned by the user that
# will be writing to the database file.
RUN chown haskala:haskala /app

# Copy the source code of the project into the container.
COPY --chown=haskala:haskala . .

# Import the initial data required by Wagtail.
RUN psql -U haskala -d haskala < haskala_dump.sql

# Use user "wagtail" to run the build commands below and the server itself.
USER haskala

RUN npm install

RUN npm run copy:icons
RUN npm run build:css
RUN npm run build:js

# Collect static files.
RUN python manage.py collectstatic --noinput --clear

# Migrate database
RUN python manage.py makemigrations
RUN python manage.py migrate --noinput

# TODO: load initial data
# RUN python manage.py loaddata initial_data.json

# Create a superuser account with default credentials.
RUN python manage.py createsuperuser --noinput --username admin --email info@haskala-library.net --password admin

# Runtime command that executes when "docker run" is called, it does the
# following:
#   1. Migrate the database.
#   2. Start the application server.
# WARNING:
#   Migrating database at the same time as starting the server IS NOT THE BEST
#   PRACTICE. The database should be migrated manually or using the release
#   phase facilities of your hosting platform. This is used only so the
#   Wagtail instance can be started with a simple "docker run" command.
CMD set -xe; python manage.py migrate --noinput; gunicorn haskala.wsgi:application
