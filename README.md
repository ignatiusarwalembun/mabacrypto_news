# MabaCrypto News

Agregator berita **Investment**, **Technology**, dan **Blockchain & Crypto** dengan frontend Vanilla HTML/CSS/JS dan backend Flask + SQLite.

Tidak memakai OpenAI API, ChatGPT API, Claude API, Gemini API, atau AI API lain. Importance score murni rule-based. Translation memakai library gratis, berjalan fail-soft di background, dan selalu fallback ke teks asli jika gagal.

## Struktur

```text
mabacrypto_news/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── config.js
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── routes/
│   ├── services/
│   └── data/
├── requirements.txt       # pointer untuk deteksi Railpack
├── railway.toml
├── netlify.toml
├── set-production-api.bat
├── auto-upload-github.bat
├── .gitignore
└── README.md
```

## Environment backend

| Variable | Default | Production |
|---|---|---|
| `DATABASE_PATH` | `backend/data/news.db` | `/app/data/news.db` dengan Railway Volume mount `/app/data` |
| `NEWS_REFRESH_MINUTES` | `20` | `20` |
| `CORS_ORIGINS` | `*` | Domain Netlify, atau `*` saat tes awal |
| `ENABLE_SCHEDULER` | `true` | `true` |
| `TRANSLATION_ENABLED` | `true` | `true` |
| `PORT` | `5000` local | otomatis dari Railway |

---

## A. TEST LOCAL

1. Buka Terminal / Command Prompt.
2. Masuk ke folder backend:
   ```bat
   cd backend
   ```
3. Buat virtual environment:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependency:
   ```bat
   pip install -r requirements.txt
   ```
5. Jalankan backend:
   ```bat
   python app.py
   ```
6. Buka `http://localhost:5000/api/health`.
7. Hasil wajib:
   ```json
   {"ok": true, "service": "MabaCrypto News API"}
   ```
8. Buka terminal kedua dari folder project dan jalankan frontend sederhana:
   ```bat
   py -m http.server 8080 --directory frontend
   ```
9. Buka `http://localhost:8080`.
10. Klik **Refresh** sekali untuk mengambil berita sekarang. Background refresh selanjutnya berjalan sesuai `NEWS_REFRESH_MINUTES`.

Jika salah satu feed gagal, sumber lain tetap diproses. Jika translation gagal, artikel tetap muncul dengan teks asli.

## B. UPLOAD GITHUB

1. Pastikan Git for Windows terinstall dan login GitHub siap.
2. Double-click `auto-upload-github.bat`.
3. Script akan scan semua file, memakai remote `main` sebagai baseline tanpa `git pull --rebase`, mempertahankan snapshot folder lokal sebagai versi terbaru, commit, lalu push ke:
   `https://github.com/ignatiusarwalembun/mabacrypto_news.git`

## C. DEPLOY RAILWAY

1. Di Railway, buat project dari repository GitHub tersebut.
2. Service memakai `railway.toml` di root, jadi start command sudah disiapkan.
3. Tambahkan Railway Volume dan mount ke:
   ```text
   /app/data
   ```
4. Tambahkan variables:
   ```text
   DATABASE_PATH=/app/data/news.db
   NEWS_REFRESH_MINUTES=20
   CORS_ORIGINS=*
   ENABLE_SCHEDULER=true
   TRANSLATION_ENABLED=true
   ```
5. Generate public Railway domain.
6. Deploy.

Railway menggunakan healthcheck `/api/health`. Jangan lanjut ke Netlify sebelum langkah D sukses.

## D. TEST RAILWAY /api/health

Buka:

```text
https://DOMAIN-RAILWAY/api/health
```

**WAJIB** menghasilkan HTTP 200 dan JSON:

```json
{
  "ok": true,
  "service": "MabaCrypto News API"
}
```

Lalu tes root:

```text
https://DOMAIN-RAILWAY/
```

Harus menampilkan service dan path health.

Setelah health sukses, tes refresh:

```text
POST https://DOMAIN-RAILWAY/api/refresh
```

Cara gampang: jalankan dari PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "https://DOMAIN-RAILWAY/api/refresh"
```

Lalu buka:

```text
https://DOMAIN-RAILWAY/api/news
```

## E. MASUKKAN DOMAIN RAILWAY KE PRODUCTION CONFIG

Tidak perlu edit source code manual.

1. Double-click `set-production-api.bat`.
2. Paste domain Railway, contoh:
   ```text
   https://mabacrypto-news-production.up.railway.app
   ```
3. Script otomatis mengisi `frontend/config.js` menjadi URL `/api` production yang sama untuk laptop, HP, tablet, incognito, dan browser baru.

`localStorage` hanya optional override untuk debugging dan **bukan** koneksi production utama.

## F. PUSH UPDATE

Double-click lagi:

```text
auto-upload-github.bat
```

Perubahan production API akan dipush ke GitHub.

## G. DEPLOY NETLIFY

1. Import repository GitHub ke Netlify.
2. `netlify.toml` di root sudah mengatur:
   ```text
   publish = frontend
   ```
3. Tidak ada build command.
4. Deploy site.
5. Setelah domain Netlify sudah ada, untuk CORS yang lebih ketat ubah Railway variable:
   ```text
   CORS_ORIGINS=https://DOMAIN-NETLIFY.netlify.app
   ```
   Jika masih tahap tes lintas device, `*` tetap didukung.

## H. TEST LAPTOP

1. Buka domain Netlify di browser baru / incognito.
2. Pastikan status berubah menjadi `BACKEND AKTIF` atau `FEED BERMASALAH`, bukan `BACKEND TIDAK TERHUBUNG`.
3. Pastikan berita muncul setelah refresh backend selesai.
4. Tes search, filter kategori, filter source, menu PENTING, TERSIMPAN, save/unsave, dark/light mode, dan link sumber.
5. Refresh halaman: saved news tetap tersimpan karena statusnya ada di backend SQLite.

## I. TEST HP

1. Buka domain Netlify dari Android/iPhone tanpa setting tambahan.
2. Pastikan tidak ada horizontal scrolling.
3. Buka menu mobile dan tes semua navigasi.
4. Tes search (Safari tidak boleh auto-zoom karena input minimal 16px).
5. Tes save berita lalu reload.
6. Pastikan HP melihat data backend Railway yang sama dengan laptop.

---

## Endpoint

- `GET /`
- `GET /api/health`
- `GET /api/news`
- `POST /api/refresh`
- `PATCH /api/news/<id>/saved`

Contoh save:

```json
{
  "saved": true
}
```

## Catatan sumber berita

- Bloomberg: memakai RSS publik Bloomberg yang tersedia; bila feed langsung gagal, backend mencoba discovery publik Google News dengan filter domain Bloomberg.
- Kontan: mencoba RSS publik Kontan; bila feed langsung gagal, backend mencoba discovery publik Google News dengan filter domain Kontan.
- Google News: memakai RSS search publik sebagai discovery source.
- Backend tidak mengambil body artikel publisher, tidak bypass paywall, dan tidak memakai browser automation.
- Sebagian Google News RSS membungkus link dalam redirect `news.google.com`. Backend hanya mencoba mengikuti redirect HTTP biasa; jika Google tidak memberikan redirect langsung, link publik Google News dipertahankan agar browser tetap membawa user ke publisher.


## AUTO RUN LOCAL

Untuk menjalankan backend dan frontend sekaligus di Windows, cukup double-click `auto-run-local.bat` dari root project. Script akan membuat `.venv` bila belum ada, memasang dependency backend bila diperlukan, menjalankan backend di `http://localhost:5000`, frontend di `http://localhost:8080`, lalu membuka browser otomatis.

## Railway configuration (fixed)
Use these exact Railway service settings:
- Root Directory: leave EMPTY (repository root)
- PORT: 8080
- Target Port for Public Networking: 8080
- DATABASE_PATH: /app/data/news.db
- Volume mount path: /app/data
- Healthcheck: /api/health
- Start command comes from root railway.toml: `cd backend && gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`

Do not set Railway Root Directory to `/backend` while using this root `railway.toml`.
