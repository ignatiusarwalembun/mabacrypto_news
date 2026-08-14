const API = window.APP_CONFIG?.API_BASE_URL || "/api";

const state = {
  view: "home",
  category: "all",
  source: "all",
  search: "",
  items: [],
  debounce: null,
};

const els = {
  newsGrid: document.getElementById("newsGrid"),
  empty: document.getElementById("emptyState"),
  resultCount: document.getElementById("resultCount"),
  source: document.getElementById("sourceSelect"),
  search: document.getElementById("searchInput"),
  refresh: document.getElementById("refreshBtn"),
  theme: document.getElementById("themeBtn"),
  toast: document.getElementById("toast"),
  sectionTitle: document.getElementById("sectionTitle"),
  sectionKicker: document.getElementById("sectionKicker"),
  totalNews: document.getElementById("totalNews"),
  importantCount: document.getElementById("importantCount"),
  techCount: document.getElementById("techCount"),
  investCount: document.getElementById("investCount"),
  cryptoCount: document.getElementById("cryptoCount"),
};

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;"
  }[char]));
}

function levelLabel(level) {
  return {
    "very-important": "Sangat Penting",
    "important": "Penting",
    "attention": "Perhatian",
    "normal": "Normal",
  }[level] || "Normal";
}

function timeAgo(iso) {
  if (!iso) return "Waktu tidak tersedia";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Waktu tidak tersedia";
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "baru saja";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} menit lalu`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} jam lalu`;
  const days = Math.floor(hours / 24);
  return `${days} hari lalu`;
}

function cardTemplate(item) {
  const level = item.importance_level || "normal";
  const publisher = item.publisher || item.source;
  const title = item.title_id || item.title_original;
  const summary = item.summary_id || item.summary_original || "Ringkasan belum tersedia.";
  return `
    <article class="news-card" data-level="${escapeHtml(level)}">
      <div class="card-top">
        <span class="badge ${escapeHtml(level)}">${escapeHtml(levelLabel(level))}</span>
        <span class="score"><strong>${Number(item.importance_score || 0)}</strong>/100</span>
      </div>

      <h3>${escapeHtml(title)}</h3>
      <p class="news-summary">${escapeHtml(summary)}</p>
      ${item.importance_reason ? `<p class="importance-reason">${escapeHtml(item.importance_reason)}</p>` : ""}

      <div class="card-bottom">
        <div class="meta">
          <strong>${escapeHtml(item.source)}${publisher !== item.source ? ` · ${escapeHtml(publisher)}` : ""}</strong>
          <span>${escapeHtml({technology: "Teknologi", investment: "Investasi", crypto: "Blockchain & Crypto"}[item.category] || item.category)} · ${escapeHtml(timeAgo(item.published_at))}</span>
        </div>
        <div class="card-actions">
          <button class="card-btn ${item.is_saved ? "saved" : ""}" data-save="${escapeHtml(item.id)}" aria-label="Simpan berita">
            <svg viewBox="0 0 24 24"><path class="bookmark-path" d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z"/></svg>
          </button>
          <a class="card-btn" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" aria-label="Buka sumber asli">
            <svg viewBox="0 0 24 24"><path d="M14 5h5v5M10 14 19 5M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6"/></svg>
          </a>
        </div>
      </div>
    </article>`;
}


function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function updateHeader(stats = {}) {
  els.totalNews.textContent = stats.total ?? 0;
  els.importantCount.textContent = stats.important ?? 0;
  els.techCount.textContent = stats.technology ?? 0;
  els.investCount.textContent = stats.investment ?? 0;
  els.cryptoCount.textContent = stats.crypto ?? 0;
}

function updateSectionText() {
  const map = {
    home: ["LATEST SIGNALS", "Berita terbaru"],
    investment: ["MARKET SIGNALS", "Berita investasi"],
    technology: ["TECH SIGNALS", "Perkembangan teknologi"],
    crypto: ["BLOCKCHAIN & CRYPTO SIGNALS", "Berita blockchain & crypto"],
    important: ["HIGH PRIORITY", "Berita penting"],
    saved: ["YOUR READING LIST", "Berita tersimpan"],
  };
  [els.sectionKicker.textContent, els.sectionTitle.textContent] = map[state.view] || map.home;
}

function buildQuery() {
  const params = new URLSearchParams({ limit: "100" });
  if (state.view === "investment") params.set("category", "investment");
  else if (state.view === "technology") params.set("category", "technology");
  else if (state.view === "crypto") params.set("category", "crypto");
  else if (state.category !== "all") params.set("category", state.category);

  if (state.view === "important") params.set("important", "true");
  if (state.view === "saved") params.set("saved", "true");
  if (state.source !== "all") params.set("source", state.source);
  if (state.search) params.set("search", state.search);
  return params;
}

async function loadNews() {
  updateSectionText();
  els.resultCount.textContent = "Memuat berita…";
  els.empty.hidden = true;
  try {
    const response = await fetch(`${API}/news?${buildQuery().toString()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    state.items = data.items || [];
    updateHeader(data.stats || {});
    renderNews();
  } catch (error) {
    state.items = [];
    renderNews();
    showToast("Backend belum terhubung. Jalankan backend Flask dulu.");
    console.error(error);
  }
}

function renderNews() {
  els.newsGrid.innerHTML = state.items.map(cardTemplate).join("");
  els.resultCount.textContent = `${state.items.length} berita`;
  els.newsGrid.hidden = state.items.length === 0;
  els.empty.hidden = state.items.length !== 0;

  document.querySelectorAll("[data-save]").forEach(btn => {
    btn.addEventListener("click", () => toggleSave(btn.dataset.save));
  });
}

async function toggleSave(id) {
  const item = state.items.find(n => n.id === id);
  if (!item) return;
  const next = !Boolean(item.is_saved);
  try {
    const response = await fetch(`${API}/news/${id}/saved`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_saved: next }),
    });
    if (!response.ok) throw new Error("save failed");
    item.is_saved = next ? 1 : 0;
    if (state.view === "saved" && !next) state.items = state.items.filter(n => n.id !== id);
    renderNews();
    showToast(next ? "Berita disimpan." : "Berita dihapus dari tersimpan.");
  } catch (error) {
    showToast("Gagal menyimpan berita.");
  }
}

async function refreshNews() {
  els.refresh.classList.add("loading");
  try {
    const response = await fetch(`${API}/refresh`, { method: "POST" });
    if (!response.ok) throw new Error("refresh failed");
    const data = await response.json();
    if (data.last_error) throw new Error(data.last_error);
    showToast(`Refresh selesai · ${data.last_count || 0} artikel diproses.`);
    await loadNews();
  } catch (error) {
    showToast("Refresh gagal. Cek koneksi backend atau feed berita.");
  } finally {
    els.refresh.classList.remove("loading");
  }
}

function setView(view) {
  state.view = view;
  if (["investment", "technology", "crypto", "important", "saved"].includes(view)) {
    state.category = "all";
    document.querySelectorAll(".filter-chip").forEach(c => c.classList.toggle("active", c.dataset.category === "all"));
  }
  document.querySelectorAll("[data-view]").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
  window.scrollTo({ top: document.querySelector(".controls").offsetTop - 24, behavior: "smooth" });
  loadNews();
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("mabacrypto-news-theme", theme);
  document.querySelector('meta[name="theme-color"]').setAttribute("content", theme === "dark" ? "#080808" : "#f6f4ee");
}

document.querySelectorAll("[data-view]").forEach(btn => btn.addEventListener("click", () => setView(btn.dataset.view)));
document.querySelectorAll(".filter-chip").forEach(btn => btn.addEventListener("click", () => {
  state.view = "home";
  state.category = btn.dataset.category;
  document.querySelectorAll(".filter-chip").forEach(c => c.classList.toggle("active", c === btn));
  document.querySelectorAll("[data-view]").forEach(nav => nav.classList.toggle("active", nav.dataset.view === "home"));
  loadNews();
}));

els.source.addEventListener("change", () => { state.source = els.source.value; loadNews(); });
els.search.addEventListener("input", () => {
  clearTimeout(state.debounce);
  state.debounce = setTimeout(() => { state.search = els.search.value.trim(); loadNews(); }, 350);
});
els.refresh.addEventListener("click", refreshNews);
els.theme.addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));

applyTheme(localStorage.getItem("mabacrypto-news-theme") || "dark");
loadNews();
