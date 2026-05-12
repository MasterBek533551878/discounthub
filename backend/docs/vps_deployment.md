# VPS deployment notes

This is a simple VPS path for the current FastAPI backend.

## 1. Copy backend to server

Copy the `backend/` folder to your server.

## 2. Create `.env`

On the server inside `backend/`:

```bash
cp .env.production.example .env
```

Then edit:

```text
ADMIN_API_TOKEN=<long random token>
DATABASE_PATH=/data/discounthub.sqlite3
DEFAULT_FEED_PROVIDERS_PATH=config/feed_providers.production.example.json
```

## 3. Run with Docker Compose

```bash
docker compose up -d --build
```

## 4. Check

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/storage/status
```

## 5. Reverse proxy

Put Nginx/Caddy in front of the backend and proxy HTTPS traffic to `127.0.0.1:8000`.

The Flutter app should use the public HTTPS API URL, not a local IP.
