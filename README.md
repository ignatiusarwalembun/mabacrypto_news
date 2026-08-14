# MabaCrypto News Intelligence — V1.3 No-AI

Dashboard berita investasi, teknologi, blockchain, dan crypto dengan UI gold/white/black, dark/light mode, responsive mobile-desktop, saved news, auto refresh, serta importance scoring **100% lokal tanpa OpenAI atau API AI**.

## Yang berubah di V1.3

- OpenAI SDK dihapus total.
- `OPENAI_API_KEY` dan `OPENAI_MODEL` tidak diperlukan lagi.
- Importance scoring sekarang deterministic/rule-based di backend.
- Ringkasan menggunakan snippet/feed sumber yang dibersihkan dan dipendekkan secara lokal.
- Judul/snippet Inggris memakai kamus istilah lokal untuk istilah finance/tech/crypto umum. Kata yang tidak dikenal dipertahankan agar aplikasi tidak mengarang terjemahan.
- Kategori Blockchain & Crypto tetap aktif penuh.
- GitHub auto uploader `auto-upload-github.bat` tetap disertakan.

## Struktur

```text
mabacrypto-news/
├── frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── config.js
│   └── netlify.toml
├── backend/
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── data/
│   ├── requirements.txt
│   ├── .env.example
│   └── Procfile
├── auto-upload-github.bat
├── start-all.bat
├── start-backend.bat
└── start-frontend.bat
```

## Sumber berita

Collector memakai Google News RSS search sebagai discovery layer:

- Bloomberg — query dibatasi `site:bloomberg.com`
- Kontan — query dibatasi `site:kontan.co.id`
- Google News — query umum investasi, teknologi, blockchain, dan crypto

Aplikasi menyimpan headline, snippet/feed, metadata, kategori, importance score, dan link sumber asli. Aplikasi tidak mencoba membuka atau menyalin isi paywall Bloomberg.

## Kategori

- Investasi
- Teknologi
- Blockchain & Crypto
- Penting
- Saved

Blockchain & Crypto mencakup query seperti Bitcoin, Ethereum, stablecoin, tokenisasi, Web3, regulasi crypto, ETF, hack/exploit, dan ekosistem blockchain.

## Importance scoring tanpa AI

Backend membaca sinyal pada judul/snippet. Contoh bobot:

```text
rate cut / rate hike        +18 / +20
crash                       +25
recession                   +18
semiconductor               +12
artificial intelligence     +12
bitcoin                     +12
ethereum                    +11
stablecoin                  +12
hack / exploit              +24 / +22
crypto regulation           +14
large % move                +12
large $ billion/trillion    +14
```

Level visual:

```text
0-39   Normal
40-69  Perhatian
70-84  Penting
85-100 Sangat Penting
```

Semua aturan ada di `backend/services/analyzer.py` dan dapat diubah tanpa API eksternal.

## Jalankan di Windows

### Backend

Double click:

```text
start-backend.bat
```

File `.env` cukup berisi:

```env
PORT=5000
NEWS_REFRESH_MINUTES=20
MAX_ITEMS_PER_FEED=8
CORS_ORIGINS=*
```

Tidak ada API key.

### Frontend

Double click:

```text
start-frontend.bat
```

Buka:

```text
http://localhost:5500
```

Backend lokal:

```text
http://localhost:5000/api
```

## Endpoint backend

```text
GET   /api/health
GET   /api/news
POST  /api/refresh
PATCH /api/news/:id/saved
```

Contoh:

```text
/api/news?category=investment
/api/news?category=technology
/api/news?category=crypto
/api/news?category=crypto&source=Bloomberg
/api/news?important=true
/api/news?saved=true
/api/news?search=bitcoin
```

## Deploy Railway

1. Push project ke GitHub.
2. Railway → New Project → Deploy from GitHub.
3. Pilih repo `ignatiusarwalembun/mabacrypto_news`.
4. Set **Root Directory** ke `/backend`.
5. Start command dapat memakai Procfile: `python app.py`.
6. Tambahkan variable:

```text
NEWS_REFRESH_MINUTES=20
MAX_ITEMS_PER_FEED=8
CORS_ORIGINS=*
```

`PORT` diberikan Railway otomatis, jadi tidak perlu dibuat manual.

**Tidak perlu `OPENAI_API_KEY`.**

Untuk SQLite persisten di Railway, attach Volume ke lokasi data aplikasi sebelum dipakai jangka panjang.

## Deploy Netlify

Set URL Railway di:

```js
// frontend/config.js
window.APP_CONFIG = {
  API_BASE_URL: "https://URL-BACKEND-RAILWAY-KAMU/api"
};
```

Lalu push ke GitHub dan deploy folder `frontend` ke Netlify.

## Auto upload GitHub

Double click:

```text
auto-upload-github.bat
```

Script akan scan perubahan project, commit, sync, dan push ke:

```text
https://github.com/ignatiusarwalembun/mabacrypto_news.git
```

`.env`, database lokal, virtual environment, cache, dan file development lain tetap di-ignore.

## Railway production deployment

Versi ini sudah Railway-ready:
- `railway.toml` untuk Railpack, Gunicorn, dan healthcheck.
- `backend/mise.toml` menggunakan Python 3.13 tanpa pin patch 3.12.4 lama.
- Gunicorn menjalankan satu worker dengan threads agar scheduler berita tidak terduplikasi.
- Endpoint healthcheck: `/api/health`.
- Untuk SQLite persistent, mount Railway Volume ke `/app/data` dan set `DATABASE_PATH=/app/data/news.db`.

Lihat `RAILWAY_DEPLOY.md`.

## Safe GitHub Auto Upload

`auto-upload-github.bat` versi ini tidak lagi memakai `git pull --rebase`.
Untuk workflow update via ZIP, GitHub `main` dijadikan baseline dan isi folder lokal
dijadikan snapshot terbaru. Ini menghindari konflik `add/add` ketika project diextract
ke folder baru lalu diupload ke repository yang sama.

## Production backend for all devices

Frontend sekarang otomatis memakai:

`https://mabacryptonews-production.up.railway.app/api`

Production URL memiliki prioritas di atas localStorage, sehingga laptop, HP,
tablet, browser baru, dan incognito langsung terhubung ke backend yang sama.
