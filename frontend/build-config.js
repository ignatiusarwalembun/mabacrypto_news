const fs = require("fs");

const raw = String(process.env.RAILWAY_API_URL || "")
  .trim()
  .replace(/\/+$/, "");

if (!raw) {
  console.error("ERROR: RAILWAY_API_URL belum diatur di Netlify Environment Variables.");
  process.exit(1);
}

let backend;
try {
  backend = new URL(raw);
} catch {
  console.error("ERROR: RAILWAY_API_URL bukan URL valid.");
  process.exit(1);
}

if (backend.protocol !== "https:" && backend.protocol !== "http:") {
  console.error("ERROR: RAILWAY_API_URL harus dimulai http:// atau https://");
  process.exit(1);
}

// Frontend uses same-origin /api.
// Netlify proxies it directly to Railway.
fs.writeFileSync(
  "config.js",
  `window.APP_CONFIG = {\n  API_BASE_URL: "/api"\n};\n`,
  "utf8"
);

const redirects = `/api/*  ${raw}/api/:splat  200!\n`;
fs.writeFileSync("_redirects", redirects, "utf8");

console.log(`Netlify proxy configured: /api/* -> ${raw}/api/:splat`);
