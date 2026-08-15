(function () {
  "use strict";

  const config = window.APP_CONFIG;
  const state = {
    allNews: [],
    stats: { total: 0, important: 0, technology: 0, investment: 0, crypto: 0 },
    view: "home",
    category: "all",
    source: "all",
    query: "",
    loading: true,
    refresh: null
  };

  const els = {
    newsList: document.getElementById("newsList"),
    loadingText: document.getElementById("loadingText"),
    messageBox: document.getElementById("messageBox"),
    backendStatus: document.getElementById("backendStatus"),
    refreshButton: document.getElementById("refreshButton"),
    searchInput: document.getElementById("searchInput"),
    sourceFilter: document.getElementById("sourceFilter"),
    viewTitle: document.getElementById("viewTitle"),
    resultCount: document.getElementById("resultCount"),
    statTotal: document.getElementById("statTotal"),
    statImportant: document.getElementById("statImportant"),
    statTechnology: document.getElementById("statTechnology"),
    statInvestment: document.getElementById("statInvestment"),
    statCrypto: document.getElementById("statCrypto"),
    themeToggle: document.getElementById("themeToggle"),
    menuButton: document.getElementById("menuButton"),
    menuClose: document.getElementById("menuClose"),
    mobileMenu: document.getElementById("mobileMenu")
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function validUrl(value) {
    try {
      const url = new URL(value);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
    } catch (_) {
      return "#";
    }
  }

  function formatDate(value) {
    try {
      const date = new Date(value);
      return new Intl.DateTimeFormat("id-ID", {
        dateStyle: "medium",
        timeStyle: "short"
      }).format(date);
    } catch (_) {
      return value || "Waktu tidak tersedia";
    }
  }

  function setStatus(label, type) {
    els.backendStatus.textContent = label;
    els.backendStatus.className = `status-pill status-${type}`;
  }

  function showMessage(text) {
    els.messageBox.hidden = !text;
    els.messageBox.textContent = text || "";
  }

  function renderStats() {
    els.statTotal.textContent = state.stats.total || 0;
    els.statImportant.textContent = state.stats.important || 0;
    els.statTechnology.textContent = state.stats.technology || 0;
    els.statInvestment.textContent = state.stats.investment || 0;
    els.statCrypto.textContent = state.stats.crypto || 0;
  }

  function deriveStatus(refresh) {
    if (!refresh) {
      setStatus("BACKEND AKTIF", "good");
      return;
    }
    const sourceValues = Object.values(refresh.sources || {});
    const failed = sourceValues.some((item) => !item.ok);
    if (failed || refresh.partial_failure) setStatus("FEED BERMASALAH", "warn");
    else setStatus("BACKEND AKTIF", "good");
  }

  async function loadNews({ quiet = false } = {}) {
    state.loading = true;
    if (!quiet) {
      els.loadingText.hidden = false;
      els.loadingText.textContent = "Mengambil berita...";
      setStatus("MENGAMBIL BERITA", "neutral");
    }
    showMessage("");

    try {
      const response = await fetch(`${config.API_BASE_URL}/news?limit=500`, {
        headers: { Accept: "application/json" },
        cache: "no-store"
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "API error");

      state.allNews = Array.isArray(data.news) ? data.news : [];
      state.stats = data.stats || state.stats;
      state.refresh = data.refresh || null;
      renderStats();
      deriveStatus(state.refresh);
      render();
    } catch (error) {
      setStatus("BACKEND TIDAK TERHUBUNG", "bad");
      showMessage("Backend MabaCrypto News sedang tidak tersedia.");
      state.allNews = [];
      render();
    } finally {
      state.loading = false;
      els.loadingText.hidden = true;
    }
  }

  async function refreshNews() {
    els.refreshButton.disabled = true;
    els.refreshButton.textContent = "Mengambil...";
    setStatus("MENGAMBIL BERITA", "neutral");
    showMessage("");
    try {
      const response = await fetch(`${config.API_BASE_URL}/refresh`, {
        method: "POST",
        headers: { Accept: "application/json" }
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok && !data.refresh) throw new Error(data.error || `HTTP ${response.status}`);
      state.refresh = data.refresh || null;
      await loadNews({ quiet: true });
      deriveStatus(state.refresh);
    } catch (_) {
      setStatus("BACKEND TIDAK TERHUBUNG", "bad");
      showMessage("Backend MabaCrypto News sedang tidak tersedia.");
    } finally {
      els.refreshButton.disabled = false;
      els.refreshButton.textContent = "Refresh";
    }
  }

  function filteredNews() {
    const query = state.query.trim().toLowerCase();
    return state.allNews.filter((item) => {
      if (state.view === "saved" && !item.saved) return false;
      if (state.view === "important" && Number(item.importance_score) < 70) return false;
      if (state.category !== "all" && item.category !== state.category) return false;
      if (state.source !== "all" && item.source !== state.source) return false;
      if (query) {
        const haystack = [item.title, item.summary, item.publisher, item.source, item.category]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });
  }

  function cardClass(item) {
    const score = Number(item.importance_score || 0);
    if (score >= 85) return "news-card critical";
    if (score >= 70) return "news-card important";
    return "news-card";
  }

  function renderCard(item) {
    const safeLink = validUrl(item.original_url);
    return `
      <article class="${cardClass(item)}" data-news-id="${Number(item.id)}">
        <div class="card-top">
          <div class="meta-chips">
            <span class="meta-chip">${escapeHtml(item.category)}</span>
            <span class="meta-chip">${escapeHtml(item.source)}</span>
            <span class="meta-chip score">${escapeHtml(item.importance_level)} · ${Number(item.importance_score)}/100</span>
          </div>
          <button class="save-button ${item.saved ? "saved" : ""}" type="button" data-save-id="${Number(item.id)}" aria-pressed="${Boolean(item.saved)}">
            ${item.saved ? "TERSIMPAN" : "SIMPAN"}
          </button>
        </div>
        <h3 class="news-title">${escapeHtml(item.title)}</h3>
        <p class="news-summary">${escapeHtml(item.summary)}</p>
        <div class="card-footer">
          <div class="publisher-line">${escapeHtml(item.publisher)} · ${escapeHtml(formatDate(item.published_at))}${item.translated ? " · Terjemahan Indonesia" : ""}</div>
          <a class="original-link" href="${escapeHtml(safeLink)}" target="_blank" rel="noopener noreferrer">BUKA SUMBER →</a>
        </div>
      </article>`;
  }

  function render() {
    const items = filteredNews();
    els.resultCount.textContent = `${items.length} berita`;
    const titles = {
      home: "Berita terbaru",
      investment: "Berita investasi",
      technology: "Berita teknologi",
      crypto: "Blockchain & Crypto",
      important: "Berita penting",
      saved: "Berita tersimpan"
    };
    els.viewTitle.textContent = titles[state.view] || "Berita terbaru";

    if (!items.length && !state.loading) {
      els.newsList.innerHTML = `<div class="empty-state">Tidak ada berita yang cocok dengan filter ini.</div>`;
      return;
    }
    els.newsList.innerHTML = items.map(renderCard).join("");
  }

  async function toggleSaved(id) {
    const item = state.allNews.find((entry) => Number(entry.id) === Number(id));
    if (!item) return;
    const next = !item.saved;
    try {
      const response = await fetch(`${config.API_BASE_URL}/news/${id}/saved`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ saved: next })
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      item.saved = next;
      render();
    } catch (_) {
      showMessage("Status berita tersimpan gagal diperbarui. Coba lagi.");
    }
  }

  function setView(view) {
    state.view = view;
    const categoryMap = {
      home: "all",
      investment: "Investment",
      technology: "Technology",
      crypto: "Blockchain & Crypto",
      important: "all",
      saved: "all"
    };
    state.category = categoryMap[view] || "all";

    document.querySelectorAll("[data-nav]").forEach((button) => {
      button.classList.toggle("active", button.dataset.nav === view);
    });
    document.querySelectorAll("[data-category]").forEach((button) => {
      button.classList.toggle("active", button.dataset.category === state.category);
    });
    closeMenu();
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openMenu() {
    els.mobileMenu.classList.add("open");
    els.mobileMenu.setAttribute("aria-hidden", "false");
    els.menuButton.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }

  function closeMenu() {
    els.mobileMenu.classList.remove("open");
    els.mobileMenu.setAttribute("aria-hidden", "true");
    els.menuButton.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("mabacrypto_theme", theme);
    els.themeToggle.textContent = theme === "dark" ? "☼" : "☾";
    document.querySelector('meta[name="theme-color"]').setAttribute("content", theme === "dark" ? "#090909" : "#f5f2e9");
  }

  document.addEventListener("click", (event) => {
    const nav = event.target.closest("[data-nav]");
    if (nav) {
      event.preventDefault();
      setView(nav.dataset.nav);
      return;
    }
    const category = event.target.closest("[data-category]");
    if (category) {
      state.category = category.dataset.category;
      state.view = "home";
      document.querySelectorAll("[data-category]").forEach((button) => button.classList.toggle("active", button === category));
      document.querySelectorAll("[data-nav]").forEach((button) => button.classList.toggle("active", button.dataset.nav === "home"));
      render();
      return;
    }
    const save = event.target.closest("[data-save-id]");
    if (save) toggleSaved(save.dataset.saveId);
  });

  els.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value || "";
    render();
  });
  els.sourceFilter.addEventListener("change", (event) => {
    state.source = event.target.value;
    render();
  });
  els.refreshButton.addEventListener("click", refreshNews);
  els.themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
  });
  els.menuButton.addEventListener("click", openMenu);
  els.menuClose.addEventListener("click", closeMenu);
  els.mobileMenu.addEventListener("click", (event) => {
    if (event.target === els.mobileMenu) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });

  applyTheme(localStorage.getItem("mabacrypto_theme") || "dark");
  loadNews();
})();
