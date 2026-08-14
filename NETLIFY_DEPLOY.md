# Netlify -> Railway (Direct)

This version intentionally does NOT use Netlify Functions or an API proxy.

## Netlify settings

When importing the GitHub repository:

- Base directory: `frontend`
- Build command: `node build-config.js`
- Publish directory: `.`

## Required Netlify environment variable

Create:

`RAILWAY_API_URL=https://YOUR-RAILWAY-DOMAIN.up.railway.app`

Do NOT add `/api`.

During build, Netlify runs `build-config.js` and generates:

`window.APP_CONFIG.API_BASE_URL = "https://YOUR-RAILWAY-DOMAIN.up.railway.app/api"`

## Railway

For initial testing use:

`CORS_ORIGINS=*`

After the Netlify deployment is confirmed working, you can restrict CORS to the final Netlify domain.
