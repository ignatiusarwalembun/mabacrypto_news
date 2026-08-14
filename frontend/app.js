(() => {
  "use strict";

  const config = window.APP_CONFIG || {};
  const isLocal = ["localhost", "127.0.0.1", ""].includes(window.location.hostname);
  const API_BASE = (isLocal ? config.LOCAL_API_BASE_URL : config.API_BASE_URL || "").replace(/\/$/, "");

  const state = {
    allNews: [],
    stats: {},
    refresh: {},
    nav: "HOME",
    category: "SEMUA",
    source: "SEMUA",
    search: "",
    initialRefreshAttempted: false,
  };

  const el = {
    newsGrid: document.getElementById("newsGrid"),
    loading: document.getElementById("loadingMessage"),
    error: document.getElementById("errorMessage"),
    empty: document.getElementById("emptyMessage"),
    statusDot: document.getElementById("statusDot"),
    backendStatus: document.getElementById("backendStatus"),
    statusDetail: document.getElementById("statusDetail"),
    search: document.getElementById("searchInput"),
    source: document.getElementById("sourceFilter"),
    resultCount: document.getElementById("resultCount"),
    viewTitle: document.getElementById("viewTitle"),
    viewEyebrow: document.getElementById("viewEyebrow"),
    template: document.getElementById("newsCardTemplate"),
    mobileMenu: document.getElementById("mobileMenu"),
    mobileMenuButton: document.getElementById("mobileMenuButton"),
    themeToggle: document.getElementById("themeToggle"),
    statTotal: document.getElementById("statTotal"),
    statImportant: document.getElementById("statImportant"),
    statTechnology: document.getElementById("statTechnology"),
    statInvestment: document.getElementById("statInvestment"),
    statCrypto: document.getElementById("statCrypto"),
  };

  function api(path) {
    if (!API_BASE) throw new Error("API_BASE_URL belum dikonfigurasi.");
    return `${API_BASE}${path}`;
  }

  function setStatus(kind, title, detail) {
    el.statusDot.className = `status-dot status-${kind}`;
    el.backendStatus.textContent = title;
    el.statusDetail.textContent = detail;
  }

  async function request(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 25000);
    try {
      const response = await fetch(api(path), {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || data.message || `HTTP ${response.status}`);
      }
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  async function checkHealth() {
    setStatus("checking", "MEMERIKSA BACKEND", "Menghubungkan ke API...");
    try {
      const data = await request("/health", { timeoutMs: 9000 });
      if (!data.ok) throw new Error("Healthcheck tidak valid.");
      setStatus("active", "BACKEND AKTIF", "API MabaCrypto News terhubung.");
      return true;
    } catch (error) {
      setStatus("error", "BACKEND TIDAK TERHUBUNG", "Backend MabaCrypto News sedang tidak tersedia.");
      showError(`Backend MabaCrypto News sedang tidak tersedia. ${error.message}`);
      return false;
    }
  }

  function showLoading(show) {
    el.loading.hidden = !show;
  }

  function showError(message = "") {
    el.error.textContent = message;
    el.error.hidden = !message;
  }

  function formatDate(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "Waktu tidak tersedia";
    return new Intl.DateTimeFormat("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function currentNews() {
    const query = state.search.trim().toLowerCase();
    return state.allNews.filter((item) => {
      if (state.nav === "INVESTASI" && item.category !== "Investment") return false;
      if (state.nav === "TEKNOLOGI" && item.category !== "Technology") return false;
      if (state.nav === "BLOCKCHAIN & CRYPTO" && item.category !== "Blockchain & Crypto") return false;
      if (state.nav === "PENTING" && Number(item.importance_score) < 70) return false;
      if (state.nav === "TERSIMPAN" && !item.saved) return false;
      if (state.category !== "SEMUA" && item.category !== state.category) return false;
      if (state.source !== "SEMUA" && item.source !== state.source) return false;
      if (query) {
        const haystack = `${item.title} ${item.summary} ${item.publisher}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });
  }

  function updateViewHeading() {
    const map = {
      HOME: ["LATEST", "Berita Terbaru"],
      INVESTASI: ["CATEGORY", "Investasi"],
      TEKNOLOGI: ["CATEGORY", "Teknologi"],
      "BLOCKCHAIN & CRYPTO": ["CATEGORY", "Blockchain & Crypto"],
      PENTING: ["PRIORITY", "Berita Penting"],
      TERSIMPAN: ["SAVED", "Berita Tersimpan"],
    };
    const [eyebrow, title] = map[state.nav] || map.HOME;
    el.viewEyebrow.textContent = eyebrow;
    el.viewTitle.textContent = title;
  }

  function updateStats(stats = {}) {
    el.statTotal.textContent = stats.total || 0;
    el.statImportant.textContent = stats.important || 0;
    el.statTechnology.textContent = stats.technology || 0;
    el.statInvestment.textContent = stats.investment || 0;
    el.statCrypto.textContent = stats.crypto || 0;
  }

  function applyRefreshStatus(refresh = {}) {
    const errors = refresh.source_errors || {};
    const errorCount = Object.keys(errors).length;
    if (refresh.running) {
      setStatus("loading", "MENGAMBIL BERITA", "Backend sedang memperbarui feed.");
    } else if (errorCount > 0) {
      setStatus("loading", "FEED BERMASALAH", `${errorCount} feed bermasalah; feed lain tetap digunakan.`);
    } else {
      setStatus("active", "BACKEND AKTIF", "API terhubung dan siap digunakan.");
    }
  }

  function renderNews() {
    const items = currentNews();
    el.newsGrid.replaceChildren();
    el.resultCount.textContent = `${items.length} berita`;
    el.empty.hidden = items.length !== 0;
    updateViewHeading();

    for (const item of items) {
      const fragment = el.template.content.cloneNode(true);
      const card = fragment.querySelector(".news-card");
      const level = item.importance_level || "NORMAL";
      if (level === "PENTING") card.classList.add("level-important");
      if (level === "SANGAT PENTING") card.classList.add("level-critical");

      fragment.querySelector(".source-label").textContent = item.source;
      fragment.querySelector(".publisher-label").textContent = item.publisher;
      fragment.querySelector(".importance-badge").textContent = level;
      fragment.querySelector(".category-label").textContent = item.category;
      fragment.querySelector(".published-label").textContent = formatDate(item.published_at);
      fragment.querySelector(".news-title").textContent = item.title;
      fragment.querySelector(".news-summary").textContent = item.summary;
      fragment.querySelector(".score-value").textContent = `${item.importance_score}/100`;

      const saveButton = fragment.querySelector(".save-btn");
      saveButton.textContent = item.saved ? "TERSIMPAN" : "SIMPAN";
      saveButton.classList.toggle("saved", Boolean(item.saved));
      saveButton.addEventListener("click", () => toggleSaved(item.id, !item.saved, saveButton));

      const link = fragment.querySelector(".source-link");
      link.href = item.original_url;

      el.newsGrid.appendChild(fragment);
    }
  }

  async function loadNews({ refreshIfEmpty = false } = {}) {
    showError("");
    showLoading(true);
    try {
      const data = await request("/news");
      state.allNews = Array.isArray(data.news) ? data.news : [];
      state.stats = data.stats || {};
      state.refresh = data.refresh || {};
      updateStats(state.stats);
      applyRefreshStatus(state.refresh);
      renderNews();

      if (refreshIfEmpty && state.allNews.length === 0 && !state.initialRefreshAttempted) {
        state.initialRefreshAttempted = true;
        await refreshNews();
      }
    } catch (error) {
      setStatus("error", "BACKEND TIDAK TERHUBUNG", "Backend MabaCrypto News sedang tidak tersedia.");
      showError(`Backend MabaCrypto News sedang tidak tersedia. ${error.message}`);
    } finally {
      showLoading(false);
    }
  }

  async function refreshNews() {
    setStatus("loading", "MENGAMBIL BERITA", "Mengambil berita terbaru...");
    showLoading(true);
    try {
      await request("/refresh", { method: "POST", body: "{}", timeoutMs: 120000 });
      await loadNews({ refreshIfEmpty: false });
    } catch (error) {
      showError(`Feed bermasalah. ${error.message}`);
      setStatus("loading", "FEED BERMASALAH", "Sebagian atau seluruh feed gagal diperbarui.");
    } finally {
      showLoading(false);
    }
  }

  async function toggleSaved(id, nextValue, button) {
    button.disabled = true;
    try {
      const data = await request(`/news/${id}/saved`, {
        method: "PATCH",
        body: JSON.stringify({ saved: nextValue }),
      });
      const index = state.allNews.findIndex((item) => item.id === id);
      if (index >= 0) state.allNews[index] = data.news;
      renderNews();
    } catch (error) {
      showError(`Gagal menyimpan berita. ${error.message}`);
    } finally {
      button.disabled = false;
    }
  }

  function setNav(nav) {
    state.nav = nav;
    document.querySelectorAll("[data-nav]").forEach((button) => {
      button.classList.toggle("active", button.dataset.nav === nav);
    });
    el.mobileMenu.hidden = true;
    el.mobileMenuButton.setAttribute("aria-expanded", "false");
    renderNews();
  }

  function setCategory(category) {
    state.category = category;
    document.querySelectorAll("[data-category]").forEach((button) => {
      button.classList.toggle("active", button.dataset.category === category);
    });
    renderNews();
  }

  function initTheme() {
    const saved = localStorage.getItem("mabacrypto_theme") || "dark";
    document.documentElement.dataset.theme = saved;
    el.themeToggle.textContent = saved === "light" ? "☀" : "☾";
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("mabacrypto_theme", next);
    el.themeToggle.textContent = next === "light" ? "☀" : "☾";
  }

  function bindEvents() {
    document.querySelectorAll("[data-nav]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        setNav(button.dataset.nav);
      });
    });

    document.querySelectorAll("[data-category]").forEach((button) => {
      button.addEventListener("click", () => setCategory(button.dataset.category));
    });

    let searchTimer;
    el.search.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.search = el.search.value;
        renderNews();
      }, 120);
    });

    el.source.addEventListener("change", () => {
      state.source = el.source.value;
      renderNews();
    });

    el.mobileMenuButton.addEventListener("click", () => {
      const isOpen = !el.mobileMenu.hidden;
      el.mobileMenu.hidden = isOpen;
      el.mobileMenuButton.setAttribute("aria-expanded", String(!isOpen));
    });

    el.themeToggle.addEventListener("click", toggleTheme);
  }

  async function init() {
    initTheme();
    bindEvents();
    const healthy = await checkHealth();
    if (healthy) await loadNews({ refreshIfEmpty: true });
  }

  init();
})();
