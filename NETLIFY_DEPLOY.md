# Netlify -> Railway

This version uses Netlify's native rewrite proxy.

## Netlify settings

- Base directory: `frontend`
- Build command: `node build-config.js`
- Publish directory: `.`

## Environment variable

Set:

`RAILWAY_API_URL=https://YOUR-RAILWAY-DOMAIN.up.railway.app`

Do not add `/api`.

During deploy, `build-config.js` generates:

`/api/*  https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/:splat  200!`

The browser only calls `/api`, so mobile and desktop use exactly the same path.
