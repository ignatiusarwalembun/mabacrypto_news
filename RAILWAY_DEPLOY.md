# Railway Deployment

This repository is structured as an isolated monorepo.

## Railway service settings

- Root Directory: `/backend`
- Config file: `/railway.toml` (repository root)
- Builder: Railpack
- Start command: defined in `railway.toml`
- Healthcheck: `/api/health`

## Variables

```env
NEWS_REFRESH_MINUTES=20
MAX_ITEMS_PER_FEED=8
CORS_ORIGINS=*
DATABASE_PATH=/app/data/news.db
```

Do not set `PORT`; Railway provides it automatically.

## Persistent SQLite

Attach a Railway Volume to `/app/data` and set:

```env
DATABASE_PATH=/app/data/news.db
```

## Python

The old exact `python-3.12.4` runtime pin was removed. `backend/mise.toml`
requests Python `3.13`, allowing Railpack/mise to resolve a maintained
3.13 patch release instead of the problematic old artifact.
