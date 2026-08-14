// Production-safe API routing.
// Browser always talks to the same Netlify origin.
// Netlify Function forwards /api/* to Railway.
window.APP_CONFIG = {
  API_BASE_URL: "/api"
};
