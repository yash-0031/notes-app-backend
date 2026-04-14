#!/bin/sh
set -e

echo "Waiting for database and Redis..."
python -c "
import os
import time
import psycopg2
import redis

for i in range(30):
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        break
    except Exception:
        time.sleep(2)

r = redis.from_url(os.environ['REDIS_URL'])
for i in range(30):
    try:
        r.ping()
        break
    except Exception:
        time.sleep(2)

print('Dependencies ready!')
"

echo "Starting Celery..."
exec "$@"
