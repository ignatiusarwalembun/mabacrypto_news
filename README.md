# Aurum News Intelligence

Aplikasi berita investasi + teknologi + blockchain & crypto dengan tampilan gold/white/black, dark/light mode, responsive mobile-desktop, auto summary/translation, importance scoring, filtering, dan saved news.

## Struktur

```text
golden-news-intelligence/
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
├── start-backend.bat
└── start-frontend.bat
```

## Sumber berita

Collector memakai Google News RSS search untuk 3 kelompok sumber:
- Bloomberg: query dibatasi `site:bloomberg.com`
- Kontan: query dibatasi `site:kontan.co.id`
- Google News: query investasi, teknologi, serta blockchain & crypto umum

Aplikasi menyimpan headline, ringkasan feed/hasil AI, metadata, dan link ke sumber. Aplikasi tidak mencoba membuka atau menyalin isi paywall Bloomberg.

## Fitur

- Berita investasi
- Berita teknologi
- Berita blockchain & crypto (Bitcoin, Ethereum, stablecoin, tokenisasi, Web3, dan ekosistem blockchain)
- Bloomberg / Kontan / Google News source filtering
- Terjemahan otomatis ke Bahasa Indonesia jika `OPENAI_API_KEY` dipasang
- Ringkasan otomatis
- Importance score 0-100
- Level: Normal / Perhatian / Penting / Sangat Penting
- Highlight background untuk berita penting
- Search
- Saved news
- Auto refresh backend dengan APScheduler
- Duplicate prevention di SQLite
- Dark mode + light mode
- Responsive phone / tablet / desktop
- Mobile bottom navigation

## Jalankan di Windows

### 1. Backend

Double click:

```text
start-backend.bat
```

Pertama kali script akan membuat virtual environment dan install dependency.

Lalu edit:

```text
backend/.env
```

Isi minimal:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.6-luna
PORT=5000
NEWS_REFRESH_MINUTES=20
MAX_ITEMS_PER_FEED=8
CORS_ORIGINS=*
```

Tanpa API key, aplikasi tetap bekerja menggunakan importance detector lokal/fallback, tetapi terjemahan AI tidak aktif.

### 2. Frontend

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

## Endpoint Backend

```text
GET   /api/health
GET   /api/news
POST  /api/refresh
PATCH /api/news/:id/saved
```

Contoh query:

```text
/api/news?category=technology&source=Bloomberg
/api/news?category=crypto&source=Bloomberg
/api/news?important=true
/api/news?saved=true
/api/news?search=nvidia
```

## Deploy Railway

1. Push folder project ke GitHub.
2. Buat Railway service dari repository.
3. Set Root Directory ke `backend`.
4. Railway menjalankan `Procfile`: `python app.py`.
5. Tambahkan environment variable:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL=gpt-5.6-luna`
   - `NEWS_REFRESH_MINUTES=20`
   - `MAX_ITEMS_PER_FEED=8`
   - `CORS_ORIGINS=https://DOMAIN-NETLIFY-KAMU.netlify.app`
6. Copy public Railway URL.

> Catatan: SQLite di Railway cocok untuk prototype. Jika deployment Railway tidak memakai persistent volume, database akan reset saat instance dibuat ulang. Untuk produksi jangka panjang, pindahkan storage ke database persisten.

## Deploy Netlify

Sebelum deploy, edit:

```js
// frontend/config.js
window.APP_CONFIG = {
  API_BASE_URL: "https://URL-BACKEND-RAILWAY-KAMU/api"
};
```

Lalu deploy folder `frontend` sebagai Netlify site.

## Cara importance scoring bekerja

Jika OpenAI API tersedia, AI menilai berita berdasarkan:
- dampak pasar
- dampak teknologi / blockchain
- besaran kejadian
- urgensi
- kebaruan

Level visual:

```text
0-39   Normal
40-69  Perhatian
70-84  Penting
85-100 Sangat Penting
```

Jika API tidak tersedia/error, backend otomatis memakai heuristic fallback agar aplikasi tidak mati.

## Catatan teknis Bloomberg

Versi ini tidak melakukan scraping artikel paywall. Feed/search aggregation dipakai sebagai discovery layer dan tombol pada card membuka sumber asli. Jika nanti memiliki lisensi Bloomberg machine-readable feed, collector dapat diganti ke feed resmi tanpa mengubah UI utama.
