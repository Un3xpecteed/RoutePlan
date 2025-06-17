#!/bin/sh
set -e

DB_WAIT_HOST=${DB_HOST:-db}
DB_WAIT_USER=${DATABASE_USER:-db_user}
DB_WAIT_NAME=${DATABASE_NAME:-routeplan}
DB_WAIT_PASSWORD=${DATABASE_PASSWORD}

echo "Waiting for PostgreSQL at $DB_WAIT_HOST as user $DB_WAIT_USER for DB $DB_WAIT_NAME..."

retries=30
until env PGPASSWORD="$DB_WAIT_PASSWORD" pg_isready -h "$DB_WAIT_HOST" -p "5432" -U "$DB_WAIT_USER" -d "$DB_WAIT_NAME" -q || [ $retries -eq 0 ]; do
  echo "Postgres is unavailable - sleeping (retries left: $retries)"
  retries=$((retries-1))
  sleep 2
done

if [ $retries -eq 0 ] && ! env PGPASSWORD="$DB_WAIT_PASSWORD" pg_isready -h "$DB_WAIT_HOST" -p "5432" -U "$DB_WAIT_USER" -d "$DB_WAIT_NAME" -q; then
    echo "PostgreSQL did not become available with user $DB_WAIT_USER and DB $DB_WAIT_NAME. Exiting."
    exit 1
fi

echo "PostgreSQL is up - continuing..."

echo "Applying database migrations..."
python manage.py migrate --noinput # Python из venv должен быть найден через PATH

echo "Starting application with command: $@"
exec "$@"