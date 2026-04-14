#!/bin/sh
set -e

echo "Waiting for database..."
python -c "
import os
import time
import psycopg2

for i in range(30):
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        print('Database ready!')
        break
    except Exception:
        print(f'Waiting for DB... ({i+1}/30)')
        time.sleep(2)
else:
    print('Database not ready after 60s')
    raise SystemExit(1)
"

echo "Running migrations..."
flask --app wsgi db upgrade

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app
