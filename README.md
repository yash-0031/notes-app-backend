# NoteShare Backend

This directory contains the Flask API, PostgreSQL, Redis, and Celery workers for NoteShare.

## Run With Docker

Use this Docker setup when you want to run only the backend stack from this directory.

```bash
cd /Users/mavenik/Documents/Personal/NoteShare/notes-app-backend
cp .env.example .env
docker compose up --build
```

Then open:

- Backend health: [http://localhost:5001/api/v1/health](http://localhost:5001/api/v1/health)

## What Runs

This compose file starts:

- `db`
- `redis`
- `backend_init`
- `web`
- `celery_worker`
- `celery_beat`

`backend_init` waits for Postgres, runs migrations, and exits successfully before the API and workers start.

## Configuration

Important `.env` values:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `GEMINI_API_KEY`
- `DB_PASSWORD`
- `WEB_PORT`
- `AI_QUERY_MAX_NOTES`
- `AI_QUERY_SUMMARY_CHUNK_LIMIT`
- `AI_QUERY_MAX_CONTEXT_CHARS`

Generate the two Flask/JWT secrets with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Notes

- This compose file is backend-only. It does not run the frontend.
- The frontend in `/Users/mavenik/Documents/Personal/NoteShare/notes-app` should point to `http://localhost:5000/api/v1` when you use this stack.
- The frontend in `/Users/mavenik/Documents/Personal/NoteShare/notes-app` should point to `http://localhost:5001/api/v1` when you use this stack.
- If you want the full stack in one command, use the root compose file in:
  - `/Users/mavenik/Documents/Personal/NoteShare/docker-compose.yml`
