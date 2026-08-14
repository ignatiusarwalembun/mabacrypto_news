# MabaCrypto News

MabaCrypto News adalah web aggregator berita untuk **Investment**, **Technology**, dan **Blockchain & Crypto** dengan frontend HTML/CSS/Vanilla JavaScript serta backend Flask + SQLite.

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
│   ├── database.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── routes/
│   ├── services/
│   └── data/
├── railway.toml
├── netlify.toml
├── auto-upload-github.bat
├── .gitignore
└── README.md
```

## Environment backend

| Variable | Default | Production recommendation |
|---|---|---|
| `PORT` | `5000` | Railway mengisi otomatis |
| `DATABASE_PATH` | `backend/data/news.db` | `/app/data/news.db` dengan Railway Volume di `/app/data` |
| `NEWS_REFRESH_MINUTES` | `20` | `20` |
| `CORS_ORIGINS` | `*` | Domain Netlify, atau `*` selama pengujian |
| `DISABLE_SCHEDULER` | `0` | `0` |
| `LOG_LEVEL` | `INFO` | `INFO` |

---

# A. TEST LOCAL

### 1. Jalankan backend

Buka terminal di folder project:

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Test di browser:

```text
http://localhost:5000/api/health
```

Harus menghasilkan JSON dengan `"ok": true`.

Test root:

```text
http://localhost:5000/
```

### 2. Jalankan frontend lokal

Buka terminal kedua dari folder project:

```bat
cd frontend
python -m http.server 8080
```

Buka:

```text
http://localhost:8080
```

Saat hostname adalah `localhost` atau `127.0.0.1`, frontend otomatis memakai `http://localhost:5000/api`.

---

# B. UPLOAD GITHUB

Repository target sudah dikunci ke:

```text
https://github.com/ignatiusarwalembun/mabacrypto_news.git
```

Cara paling sederhana:

1. Pastikan Git for Windows sudah terpasang dan login GitHub sudah aktif.
2. Double click `auto-upload-github.bat`.
3. BAT akan fetch `origin/main`, memakai remote sebagai baseline, mempertahankan snapshot folder lokal sebagai versi terbaru, melakukan `git add -A`, commit, lalu push.
4. BAT juga mencoba membersihkan state rebase/merge lama sebelum upload.

---

# C. DEPLOY RAILWAY

1. Di Railway pilih **New Project → Deploy from GitHub repo**.
2. Pilih repository `mabacrypto_news`.
3. Railway membaca `railway.toml` dari root project.
4. Tambahkan environment variables:

```text
DATABASE_PATH=/app/data/news.db
NEWS_REFRESH_MINUTES=20
CORS_ORIGINS=*
```

5. Tambahkan Railway Volume dan mount ke:

```text
/app/data
```

6. Deploy backend.

Start command sudah disiapkan:

```text
cd backend && gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

---

# D. TEST RAILWAY /api/health

**Jangan lanjut ke Netlify sebelum tahap ini berhasil.**

Buka:

```text
https://DOMAIN-RAILWAY/api/health
```

Harus menghasilkan response seperti:

```json
{
  "ok": true,
  "service": "MabaCrypto News API"
}
```

Lalu test:

```text
https://DOMAIN-RAILWAY/api/news
```

Jika database masih kosong, scheduler akan menjalankan refresh otomatis beberapa detik setelah backend hidup. Frontend juga memicu refresh sekali jika daftar berita masih kosong.

---

# E. MASUKKAN DOMAIN RAILWAY KE PRODUCTION CONFIG

`frontend/config.js` saat project ini dibuat sudah berisi:

```text
https://mabacryptonews-production.up.railway.app/api
```

Jika Railway project yang dipakai memang menggunakan domain tersebut, **tidak perlu mengubah source code apa pun**.

Jika Railway memberikan domain baru yang berbeda, ubah hanya nilai `API_BASE_URL` di `frontend/config.js` ke:

```text
https://DOMAIN-BARU.up.railway.app/api
```

Frontend production tidak memakai localStorage untuk koneksi backend.

---

# F. PUSH UPDATE

Jika domain Railway berubah dan `config.js` telah disesuaikan, double click lagi:

```text
auto-upload-github.bat
```

---

# G. DEPLOY NETLIFY

1. Di Netlify pilih **Add new site → Import an existing project**.
2. Hubungkan GitHub repository `mabacrypto_news`.
3. `netlify.toml` di root sudah menetapkan publish directory ke `frontend`.
4. Tidak ada build command karena frontend adalah HTML/CSS/Vanilla JS.
5. Deploy.

---

# H. TEST LAPTOP

Dari laptop:

1. Buka domain Netlify.
2. Pastikan status menjadi **BACKEND AKTIF**.
3. Pastikan berita muncul.
4. Coba filter kategori, source, search, theme, dan save news.
5. Refresh browser. Saved news tetap tersimpan karena status save berada di SQLite backend.

---

# I. TEST HP

Dari HP menggunakan domain Netlify yang sama:

1. Jangan mengatur backend secara manual.
2. Website otomatis memakai `API_BASE_URL` production dari `config.js`.
3. Pastikan status **BACKEND AKTIF**.
4. Pastikan tidak ada horizontal scroll.
5. Buka menu mobile dan test seluruh navigation.
6. Test save news dan buka menu **TERSIMPAN**.
7. Test juga browser incognito untuk memastikan koneksi backend tetap otomatis.

## Endpoint API

```text
GET   /
GET   /api/health
GET   /api/news
POST  /api/refresh
PATCH /api/news/:id/saved
```

Contoh PATCH:

```json
{
  "saved": true
}
```

## Catatan sumber berita

Project tidak melakukan bypass paywall dan tidak mengambil full article Bloomberg/Kontan. Google News RSS dipakai sebagai discovery source. Link artikel dicoba didecode ke publisher original menggunakan `googlenewsdecoder`; jika decoding gagal, discovery link Google News tetap dipakai sehingga user masih diarahkan ke artikel publisher melalui Google News.

Translation memakai layanan non-LLM melalui `deep-translator`. Jika translation gagal, artikel tetap disimpan dan teks original menjadi fallback.
