from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from app.core.config import get_settings

router = APIRouter(tags=["admin-panel"])


@router.get("/admin-panel", response_class=HTMLResponse)
def admin_panel() -> str:
    settings = get_settings()
    if not settings.admin_panel_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin panel is disabled in this environment.",
        )
    return _ADMIN_PANEL_HTML


_ADMIN_PANEL_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DiscountHub Admin</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --card: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --line: #e5e7eb;
      --primary: #2563eb;
      --primary-dark: #1d4ed8;
      --danger: #dc2626;
      --success: #16a34a;
      --warning: #d97706;
      --radius: 22px;
      --shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #e0ecff 0, transparent 36rem), var(--bg);
      color: var(--text);
    }

    .page {
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.3fr 0.7fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }

    .card {
      background: rgba(255,255,255,0.9);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .hero-main { padding: 28px; }
    h1 { margin: 0; font-size: clamp(32px, 5vw, 56px); line-height: 0.95; letter-spacing: -0.04em; }
    .subtitle { margin: 14px 0 0; color: var(--muted); font-size: 17px; font-weight: 650; line-height: 1.5; max-width: 720px; }

    .status-card { padding: 22px; display: grid; gap: 12px; align-content: center; }
    .status-line { display: flex; justify-content: space-between; gap: 16px; font-weight: 800; }
    .muted { color: var(--muted); }
    .pill { display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; background: #eff6ff; color: var(--primary); font-weight: 900; font-size: 13px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--success); display: inline-block; }

    .grid { display: grid; grid-template-columns: 380px 1fr; gap: 18px; align-items: start; }
    .panel { padding: 20px; }
    .panel h2 { margin: 0 0 14px; font-size: 22px; letter-spacing: -0.02em; }
    .form-grid { display: grid; gap: 12px; }
    label { display: grid; gap: 7px; color: var(--muted); font-size: 13px; font-weight: 850; }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      background: #f9fafb;
      color: var(--text);
      border-radius: 16px;
      padding: 13px 14px;
      font: inherit;
      outline: none;
    }
    textarea { min-height: 88px; resize: vertical; }
    input:focus, textarea:focus, select:focus { border-color: #93c5fd; box-shadow: 0 0 0 4px #dbeafe; background: white; }
    .two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .checks { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .check { display: flex; align-items: center; gap: 8px; padding: 11px 12px; background: #f9fafb; border: 1px solid var(--line); border-radius: 16px; font-weight: 800; color: var(--text); }
    .check input { width: auto; }

    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 2px; }
    button {
      border: 0;
      border-radius: 16px;
      padding: 13px 16px;
      cursor: pointer;
      font: inherit;
      font-weight: 900;
      background: var(--primary);
      color: white;
      transition: transform .12s ease, background .12s ease, opacity .12s ease;
    }
    button:hover { background: var(--primary-dark); transform: translateY(-1px); }
    button.secondary { background: #eef2ff; color: var(--primary); }
    button.secondary:hover { background: #dbeafe; }
    button.danger { background: #fee2e2; color: var(--danger); }
    button.danger:hover { background: #fecaca; }
    button.ghost { background: #f3f4f6; color: var(--text); }
    button:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }

    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; justify-content: space-between; margin-bottom: 12px; }
    .toolbar-left, .toolbar-right { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    .search { min-width: min(460px, 100%); }
    .table-wrap { overflow: auto; border-radius: 18px; border: 1px solid var(--line); background: white; }
    table { width: 100%; border-collapse: collapse; min-width: 920px; }
    th, td { padding: 13px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { position: sticky; top: 0; background: #f9fafb; z-index: 1; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
    td { font-weight: 700; }
    tr:hover td { background: #f8fbff; }
    .title-cell { max-width: 270px; }
    .title-cell strong { display: block; margin-bottom: 4px; }
    .title-cell span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; line-height: 1.35; }
    .badge { display: inline-flex; padding: 6px 9px; border-radius: 999px; background: #f3f4f6; color: var(--muted); font-size: 12px; font-weight: 900; white-space: nowrap; }
    .badge.good { background: #dcfce7; color: #166534; }
    .badge.hot { background: #ffedd5; color: #9a3412; }
    .row-actions { display: flex; gap: 7px; }
    .row-actions button { padding: 8px 10px; border-radius: 12px; font-size: 12px; }

    .toast {
      position: fixed;
      left: 50%;
      bottom: 24px;
      transform: translateX(-50%);
      background: #111827;
      color: white;
      padding: 13px 16px;
      border-radius: 16px;
      font-weight: 850;
      box-shadow: var(--shadow);
      opacity: 0;
      pointer-events: none;
      transition: opacity .16s ease, transform .16s ease;
      z-index: 100;
      max-width: min(720px, calc(100vw - 32px));
    }
    .toast.show { opacity: 1; transform: translateX(-50%) translateY(-4px); }

    .danger-zone { margin-top: 18px; padding: 18px; border: 1px dashed #fecaca; border-radius: var(--radius); background: #fff7f7; }
    .danger-zone h3 { margin: 0 0 8px; color: #991b1b; }
    .danger-zone p { margin: 0 0 12px; color: #7f1d1d; font-weight: 700; line-height: 1.45; }

    .io-zone { margin-top: 18px; padding: 18px; border: 1px solid #dbeafe; border-radius: var(--radius); background: #f8fbff; }
    .io-zone h3 { margin: 0 0 8px; color: #1e3a8a; }
    .io-zone p { margin: 0 0 12px; color: var(--muted); font-weight: 700; line-height: 1.45; }
    .io-zone textarea { min-height: 150px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
    .file-input { padding: 10px; background: white; }



    .provider-list { display: grid; gap: 10px; margin-top: 12px; }
    .provider-row {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: white;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: start;
    }
    .provider-row strong { display: block; margin-bottom: 4px; }
    .provider-row span { display: block; color: var(--muted); font-size: 12px; font-weight: 750; line-height: 1.35; word-break: break-all; }
    .provider-row .row-actions { justify-content: flex-end; flex-wrap: wrap; }


    .scheduler-grid { display: grid; gap: 10px; margin-top: 12px; }
    .scheduler-line { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 14px; background: white; font-weight: 800; }
    .scheduler-line span:first-child { color: var(--muted); }
    .scheduler-message { margin-top: 10px; padding: 12px; border-radius: 14px; background: #f9fafb; border: 1px solid var(--line); color: var(--muted); font-weight: 750; line-height: 1.45; word-break: break-word; }

    @media (max-width: 920px) {
      .hero, .grid { grid-template-columns: 1fr; }
      .two, .checks { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="card hero-main">
        <span class="pill"><span class="dot"></span> Local admin panel</span>
        <h1>DiscountHub Admin</h1>
        <p class="subtitle">Manage deals in the local SQLite backend. This panel is for development and MVP testing. Production admin should use real authentication and audit logs.</p>
      </div>
      <div class="card status-card">
        <div class="status-line"><span class="muted">API</span><span id="apiStatus">Checking...</span></div>
        <div class="status-line"><span class="muted">Storage</span><span id="storageStatus">Checking...</span></div>
        <div class="status-line"><span class="muted">Deals</span><span id="dealCount">—</span></div>
        <button class="secondary" onclick="loadAll()">Refresh</button>
      </div>
    </section>

    <section class="grid">
      <aside class="card panel">
        <h2 id="formTitle">Add / edit deal</h2>
        <div class="form-grid">
          <label>Admin token
            <input id="adminToken" type="password" placeholder="dev-local-admin-token" autocomplete="off" />
          </label>
          <div class="two">
            <label>ID <input id="id" placeholder="deal_custom_002" /></label>
            <label>Platform <input id="platform" placeholder="Amazon" /></label>
          </div>
          <label>Title <input id="title" placeholder="USB-C Fast Charger 65W" /></label>
          <label>Description <textarea id="description" placeholder="Short product description"></textarea></label>
          <label>Image URL <input id="imageUrl" placeholder="https://images.unsplash.com/..." /></label>
          <div class="two">
            <label>Category <input id="category" placeholder="Electronics" /></label>
            <label>Currency <input id="currency" value="USD" /></label>
          </div>
          <div class="two">
            <label>Old price <input id="oldPrice" type="number" step="0.01" placeholder="49.99" /></label>
            <label>Current price <input id="currentPrice" type="number" step="0.01" placeholder="24.99" /></label>
          </div>
          <div class="two">
            <label>Rating <input id="rating" type="number" step="0.1" min="0" max="5" placeholder="4.6" /></label>
            <label>Review count <input id="reviewCount" type="number" min="0" placeholder="1240" /></label>
          </div>
          <label>Ships to <input id="shipsTo" placeholder="US, UZ, UK, DE" /></label>
          <label>Product URL <input id="productUrl" placeholder="https://example.com/product" /></label>
          <label>Affiliate URL <input id="affiliateUrl" placeholder="https://example.com/product?ref=discounthub" /></label>
          <div class="checks">
            <label class="check"><input id="freeShipping" type="checkbox" /> Free shipping</label>
            <label class="check"><input id="verified" type="checkbox" /> Verified</label>
            <label class="check"><input id="hotDeal" type="checkbox" /> Hot deal</label>
            <label class="check"><input id="lowestPrice" type="checkbox" /> Lowest price</label>
          </div>
          <label>Deal score <input id="dealScore" type="number" min="0" max="100" placeholder="Optional, auto if empty" /></label>
          <div class="actions">
            <button onclick="saveDeal()">Save deal</button>
            <button class="secondary" onclick="fillSample()">Fill sample</button>
            <button class="ghost" onclick="clearForm()">Clear</button>
          </div>
        </div>

        <div class="danger-zone">
          <h3>Danger zone</h3>
          <p>Reset database back to the built-in demo deals. Your custom local deals will be removed.</p>
          <button class="danger" onclick="resetDemoDeals()">Reset demo deals</button>
        </div>

        <div class="io-zone">
          <h3>Import / export</h3>
          <p>Export current deals as JSON or import a JSON file/paste. Use replace only when you want to overwrite the local database.</p>
          <div class="actions">
            <button class="secondary" onclick="exportDeals()">Export JSON</button>
            <button class="ghost" onclick="copyExportToClipboard()">Copy export</button>
          </div>
          <label style="margin-top: 12px;">Import JSON file
            <input class="file-input" id="importFile" type="file" accept="application/json,.json" onchange="readImportFile(event)" />
          </label>
          <label style="margin-top: 12px;">Import JSON text
            <textarea id="importJson" placeholder='{ "items": [ ... ], "replace": false }'></textarea>
          </label>
          <label class="check" style="margin-top: 10px;"><input id="replaceImport" type="checkbox" /> Replace database before import</label>
          <div class="actions" style="margin-top: 10px;">
            <button onclick="importDeals()">Import JSON</button>
            <button class="ghost" onclick="clearImportBox()">Clear import</button>
          </div>
        </div>

        <div class="io-zone">
          <h3>Feed URL import</h3>
          <p>Import a provider JSON feed by URL. This is the bridge to affiliate feeds and official marketplace exports.</p>
          <label>Feed URL
            <input id="feedUrl" placeholder="http://127.0.0.1:9000/provider_feed.json" />
          </label>
          <label class="check" style="margin-top: 10px;"><input id="replaceFeedImport" type="checkbox" /> Replace database before URL import</label>
          <div class="actions" style="margin-top: 10px;">
            <button onclick="importFeedUrl()">Import feed URL</button>
          </div>
        </div>

        <div class="io-zone">
          <h3>Feed providers</h3>
          <p>Save reusable feed sources and sync them later. In production this can be called by a scheduler.</p>
          <div class="two">
            <label>Provider ID <input id="providerId" placeholder="demo_feed" /></label>
            <label>Name <input id="providerName" placeholder="Demo affiliate feed" /></label>
          </div>
          <label style="margin-top: 12px;">Provider URL
            <input id="providerUrl" placeholder="http://127.0.0.1:9000/provider_feed.json" />
          </label>
          <div class="checks" style="margin-top: 10px;">
            <label class="check"><input id="providerEnabled" type="checkbox" checked /> Enabled</label>
            <label class="check"><input id="providerReplace" type="checkbox" /> Replace on sync</label>
          </div>
          <div class="actions" style="margin-top: 10px;">
            <button onclick="saveProvider()">Save provider</button>
            <button class="secondary" onclick="syncAllProviders()">Sync all enabled</button>
            <button class="ghost" onclick="loadProviders()">Reload providers</button>
            <button class="ghost" onclick="clearProviderForm()">Clear provider</button>
          </div>
          <div class="provider-list" id="providersList">
            <div class="muted">No providers loaded yet.</div>
          </div>
        </div>


        <div class="io-zone">
          <h3>Feed scheduler</h3>
          <p>Run provider sync manually or start a temporary in-process scheduler for local testing. For production, use a real cron/job runner.</p>
          <div class="two">
            <label>Interval seconds
              <input id="schedulerInterval" type="number" min="60" max="86400" value="3600" />
            </label>
            <label>Timeout seconds
              <input id="schedulerTimeout" type="number" min="3" max="60" value="20" />
            </label>
          </div>
          <label class="check" style="margin-top: 10px;"><input id="schedulerRunOnStartup" type="checkbox" /> Run once when scheduler starts</label>
          <div class="actions" style="margin-top: 10px;">
            <button class="secondary" onclick="loadSchedulerStatus()">Reload scheduler</button>
            <button onclick="runSchedulerOnce()">Run once</button>
            <button onclick="startScheduler()">Start scheduler</button>
            <button class="danger" onclick="stopScheduler()">Stop scheduler</button>
          </div>
          <div class="scheduler-grid" id="schedulerStatusBox">
            <div class="muted">Scheduler status is not loaded yet.</div>
          </div>
        </div>

        <div class="io-zone">
          <h3>Sync history</h3>
          <p>Recent provider sync attempts. Useful for checking scheduled imports and failed feed URLs.</p>
          <div class="actions" style="margin-top: 10px;">
            <button class="secondary" onclick="loadSyncRuns()">Reload history</button>
            <button class="danger" onclick="clearSyncRuns()">Clear history</button>
          </div>
          <div class="provider-list" id="syncRunsList">
            <div class="muted">No sync history loaded yet.</div>
          </div>
        </div>

      </aside>

      <section class="card panel">
        <div class="toolbar">
          <div class="toolbar-left">
            <input class="search" id="search" placeholder="Search title, platform, category..." oninput="renderDeals()" />
            <select id="platformFilter" onchange="renderDeals()"><option value="">All platforms</option></select>
          </div>
          <div class="toolbar-right">
            <button class="secondary" onclick="loadDeals()">Reload list</button>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Platform</th>
                <th>Category</th>
                <th>Price</th>
                <th>Discount</th>
                <th>Score</th>
                <th>Quality</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="dealsBody">
              <tr><td colspan="8">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </main>

  <div class="toast" id="toast"></div>

  <script>
    let deals = [];
    let providers = [];
    let syncRuns = [];
    let schedulerStatus = null;

    const el = (id) => document.getElementById(id);
    const tokenHeader = () => ({ "X-Admin-Token": el("adminToken").value.trim() });

    function showToast(message) {
      const toast = el("toast");
      toast.textContent = message;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 2600);
    }

    function setStoredToken() {
      const saved = localStorage.getItem("discounthubAdminToken");
      if (saved) el("adminToken").value = saved;
      el("adminToken").addEventListener("input", () => {
        localStorage.setItem("discounthubAdminToken", el("adminToken").value.trim());
      });
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, options);
      const text = await response.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (_) { data = text; }
      if (!response.ok) {
        const detail = data && data.detail ? data.detail : response.statusText;
        throw new Error(detail);
      }
      return data;
    }

    async function loadStatus() {
      try {
        const health = await requestJson("/health");
        el("apiStatus").textContent = health.status === "ok" ? "Online" : "Unknown";
      } catch (error) {
        el("apiStatus").textContent = "Offline";
      }

      try {
        const storage = await requestJson("/storage/status");
        el("storageStatus").textContent = storage.type + (storage.exists ? " ready" : " missing");
        el("dealCount").textContent = storage.dealCount ?? storage.deal_count ?? "—";
      } catch (error) {
        el("storageStatus").textContent = "Error";
      }
    }

    async function loadDeals() {
      try {
        const data = await requestJson("/deals?page_size=100&sort=newest");
        deals = data.items || [];
        fillPlatformFilter();
        renderDeals();
        await loadStatus();
      } catch (error) {
        el("dealsBody").innerHTML = `<tr><td colspan="8">Failed to load deals: ${escapeHtml(error.message)}</td></tr>`;
        showToast("Failed to load deals: " + error.message);
      }
    }

    async function loadAll() {
      await loadStatus();
      await loadDeals();
      await loadProviders();
      await loadSchedulerStatus();
      await loadSyncRuns();
    }

    function fillPlatformFilter() {
      const select = el("platformFilter");
      const current = select.value;
      const platforms = [...new Set(deals.map((deal) => deal.platform).filter(Boolean))].sort();
      select.innerHTML = '<option value="">All platforms</option>' + platforms.map((platform) => `<option value="${escapeAttr(platform)}">${escapeHtml(platform)}</option>`).join("");
      select.value = platforms.includes(current) ? current : "";
    }

    function renderDeals() {
      const query = el("search").value.trim().toLowerCase();
      const platform = el("platformFilter").value;
      const filtered = deals.filter((deal) => {
        const text = `${deal.title} ${deal.description} ${deal.platform} ${deal.category}`.toLowerCase();
        return (!query || text.includes(query)) && (!platform || deal.platform === platform);
      });

      if (!filtered.length) {
        el("dealsBody").innerHTML = '<tr><td colspan="8">No deals found.</td></tr>';
        return;
      }

      el("dealsBody").innerHTML = filtered.map((deal) => `
        <tr>
          <td class="title-cell"><strong>${escapeHtml(deal.title)}</strong><span>${escapeHtml(deal.id)} · ${escapeHtml((deal.description || '').slice(0, 120))}</span></td>
          <td>${escapeHtml(deal.platform)}</td>
          <td>${escapeHtml(deal.category)}</td>
          <td><strong>${escapeHtml(deal.currency)} ${formatMoney(deal.currentPrice)}</strong><br><span class="muted"><s>${escapeHtml(deal.currency)} ${formatMoney(deal.oldPrice)}</s></span></td>
          <td><span class="badge good">-${deal.discountPercent}%</span></td>
          <td><span class="badge">${deal.dealScore}/100</span></td>
          <td>${qualityBadges(deal)}</td>
          <td><div class="row-actions"><button class="secondary" onclick="editDeal('${escapeAttr(deal.id)}')">Edit</button><button class="danger" onclick="deleteDeal('${escapeAttr(deal.id)}')">Delete</button></div></td>
        </tr>`).join("");
    }

    function qualityBadges(deal) {
      const badges = [];
      if (deal.freeShipping) badges.push('<span class="badge good">Free ship</span>');
      if (deal.verified) badges.push('<span class="badge good">Verified</span>');
      if (deal.hotDeal) badges.push('<span class="badge hot">Hot</span>');
      if (deal.lowestPrice) badges.push('<span class="badge hot">Lowest</span>');
      return badges.length ? badges.join(' ') : '<span class="muted">—</span>';
    }

    function editDeal(id) {
      const deal = deals.find((item) => item.id === id);
      if (!deal) return;
      el("formTitle").textContent = "Edit deal";
      el("id").value = deal.id;
      el("title").value = deal.title || "";
      el("description").value = deal.description || "";
      el("imageUrl").value = deal.imageUrl || "";
      el("platform").value = deal.platform || "";
      el("category").value = deal.category || "";
      el("oldPrice").value = deal.oldPrice ?? "";
      el("currentPrice").value = deal.currentPrice ?? "";
      el("currency").value = deal.currency || "USD";
      el("productUrl").value = deal.productUrl || "";
      el("affiliateUrl").value = deal.affiliateUrl || "";
      el("rating").value = deal.rating ?? 0;
      el("reviewCount").value = deal.reviewCount ?? 0;
      el("shipsTo").value = (deal.shipsTo || []).join(", ");
      el("freeShipping").checked = !!deal.freeShipping;
      el("verified").checked = !!deal.verified;
      el("hotDeal").checked = !!deal.hotDeal;
      el("lowestPrice").checked = !!deal.lowestPrice;
      el("dealScore").value = deal.dealScore ?? "";
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function clearForm() {
      el("formTitle").textContent = "Add / edit deal";
      for (const id of ["id", "title", "description", "imageUrl", "platform", "category", "oldPrice", "currentPrice", "productUrl", "affiliateUrl", "rating", "reviewCount", "shipsTo", "dealScore"]) {
        el(id).value = "";
      }
      el("currency").value = "USD";
      for (const id of ["freeShipping", "verified", "hotDeal", "lowestPrice"]) el(id).checked = false;
    }

    function fillSample() {
      clearForm();
      el("id").value = "deal_custom_" + Math.floor(Math.random() * 9000 + 1000);
      el("title").value = "Travel Power Adapter";
      el("description").value = "Compact universal travel adapter with USB-C and USB-A ports.";
      el("imageUrl").value = "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=1200";
      el("platform").value = "DemoShop";
      el("category").value = "Electronics";
      el("oldPrice").value = "39.99";
      el("currentPrice").value = "19.99";
      el("currency").value = "USD";
      el("productUrl").value = "https://example.com/product/travel-adapter";
      el("affiliateUrl").value = "https://example.com/product/travel-adapter?ref=discounthub";
      el("rating").value = "4.5";
      el("reviewCount").value = "860";
      el("shipsTo").value = "US, UZ, UK, DE";
      el("freeShipping").checked = true;
      el("verified").checked = true;
      el("hotDeal").checked = true;
    }

    function buildPayload() {
      const id = el("id").value.trim();
      const title = el("title").value.trim();
      const description = el("description").value.trim();
      const imageUrl = el("imageUrl").value.trim();
      const platform = el("platform").value.trim();
      const category = el("category").value.trim();
      const oldPrice = Number(el("oldPrice").value);
      const currentPrice = Number(el("currentPrice").value);
      const productUrl = el("productUrl").value.trim();
      if (!id || !title || !description || !imageUrl || !platform || !category || !oldPrice || !currentPrice || !productUrl) {
        throw new Error("Please fill ID, title, description, image, platform, category, prices and product URL.");
      }
      const scoreRaw = el("dealScore").value.trim();
      return {
        id,
        title,
        description,
        imageUrl,
        platform,
        category,
        oldPrice,
        currentPrice,
        currency: el("currency").value.trim().toUpperCase() || "USD",
        productUrl,
        affiliateUrl: el("affiliateUrl").value.trim() || null,
        rating: Number(el("rating").value || 0),
        reviewCount: Number(el("reviewCount").value || 0),
        freeShipping: el("freeShipping").checked,
        verified: el("verified").checked,
        shipsTo: el("shipsTo").value.split(",").map((item) => item.trim().toUpperCase()).filter(Boolean),
        hotDeal: el("hotDeal").checked,
        lowestPrice: el("lowestPrice").checked,
        dealScore: scoreRaw ? Number(scoreRaw) : null,
      };
    }

    async function saveDeal() {
      try {
        const payload = buildPayload();
        await requestJson("/admin/deals", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...tokenHeader() },
          body: JSON.stringify(payload),
        });
        showToast("Deal saved successfully.");
        clearForm();
        await loadDeals();
      } catch (error) {
        showToast("Save failed: " + error.message);
      }
    }

    async function deleteDeal(id) {
      if (!confirm(`Delete ${id}?`)) return;
      try {
        await requestJson(`/admin/deals/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: tokenHeader(),
        });
        showToast("Deal deleted.");
        await loadDeals();
      } catch (error) {
        showToast("Delete failed: " + error.message);
      }
    }

    async function resetDemoDeals() {
      if (!confirm("Reset database to demo deals? Custom local deals will be removed.")) return;
      try {
        await requestJson("/admin/deals/reset-demo", {
          method: "POST",
          headers: tokenHeader(),
        });
        showToast("Database reset to demo deals.");
        clearForm();
        await loadDeals();
      } catch (error) {
        showToast("Reset failed: " + error.message);
      }
    }


    async function exportDeals() {
      try {
        const data = await requestJson("/admin/deals/export", { headers: tokenHeader() });
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const date = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
        a.href = url;
        a.download = `discounthub-deals-${date}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        showToast(`Exported ${data.total || 0} deal(s).`);
      } catch (error) {
        showToast("Export failed: " + error.message);
      }
    }

    async function copyExportToClipboard() {
      try {
        const data = await requestJson("/admin/deals/export", { headers: tokenHeader() });
        await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
        showToast(`Copied ${data.total || 0} deal(s) to clipboard.`);
      } catch (error) {
        showToast("Copy failed: " + error.message);
      }
    }

    function readImportFile(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => { el("importJson").value = String(reader.result || ""); };
      reader.onerror = () => showToast("Could not read import file.");
      reader.readAsText(file);
    }

    function clearImportBox() {
      el("importJson").value = "";
      el("replaceImport").checked = false;
      el("importFile").value = "";
    }

    async function importDeals() {
      try {
        const raw = el("importJson").value.trim();
        if (!raw) throw new Error("Paste JSON or choose a JSON file first.");
        const parsed = JSON.parse(raw);
        const items = Array.isArray(parsed) ? parsed : parsed.items;
        if (!Array.isArray(items) || !items.length) throw new Error("JSON must contain a non-empty items array.");
        const replace = el("replaceImport").checked || parsed.replace === true;
        if (replace && !confirm(`Replace database and import ${items.length} deal(s)?`)) return;
        const result = await requestJson("/admin/deals/import", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...tokenHeader() },
          body: JSON.stringify({ items, replace }),
        });
        showToast(result.message || `Imported ${items.length} deal(s).`);
        clearImportBox();
        await loadDeals();
      } catch (error) {
        showToast("Import failed: " + error.message);
      }
    }



    async function importFeedUrl() {
      try {
        const url = el("feedUrl").value.trim();
        if (!url) throw new Error("Enter feed URL first.");
        const replace = el("replaceFeedImport").checked;
        if (replace && !confirm("Replace database and import this feed URL?")) return;
        const result = await requestJson("/admin/deals/import-url", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...tokenHeader() },
          body: JSON.stringify({ url, replace }),
        });
        showToast(result.message || "Feed URL imported.");
        await loadDeals();
      } catch (error) {
        showToast("Feed URL import failed: " + error.message);
      }
    }

    async function loadProviders() {
      try {
        const data = await requestJson("/admin/feed-providers", { headers: tokenHeader() });
        providers = data.items || [];
        renderProviders();
      } catch (error) {
        el("providersList").innerHTML = `<div class="muted">Failed to load providers: ${escapeHtml(error.message)}</div>`;
      }
    }

    function renderProviders() {
      if (!providers.length) {
        el("providersList").innerHTML = '<div class="muted">No feed providers saved yet.</div>';
        return;
      }
      el("providersList").innerHTML = providers.map((provider) => `
        <div class="provider-row">
          <div>
            <strong>${escapeHtml(provider.name)} ${provider.enabled ? '<span class="badge good">enabled</span>' : '<span class="badge">disabled</span>'}</strong>
            <span>${escapeHtml(provider.id)}</span>
            <span>${escapeHtml(provider.url)}</span>
            <span>Last sync: ${provider.lastSyncAt ? escapeHtml(provider.lastSyncAt) : 'never'} · ${provider.lastStatus || '—'} · imported: ${provider.lastImportedCount || 0}</span>
            ${provider.lastMessage ? `<span>${escapeHtml(provider.lastMessage)}</span>` : ''}
          </div>
          <div class="row-actions">
            <button class="secondary" onclick="editProvider('${escapeAttr(provider.id)}')">Edit</button>
            <button class="secondary" onclick="syncProvider('${escapeAttr(provider.id)}')">Sync</button>
            <button class="danger" onclick="deleteProvider('${escapeAttr(provider.id)}')">Delete</button>
          </div>
        </div>
      `).join("");
    }

    function editProvider(id) {
      const provider = providers.find((item) => item.id === id);
      if (!provider) return;
      el("providerId").value = provider.id;
      el("providerName").value = provider.name || "";
      el("providerUrl").value = provider.url || "";
      el("providerEnabled").checked = !!provider.enabled;
      el("providerReplace").checked = !!provider.replaceOnSync;
    }

    function clearProviderForm() {
      el("providerId").value = "";
      el("providerName").value = "";
      el("providerUrl").value = "";
      el("providerEnabled").checked = true;
      el("providerReplace").checked = false;
    }

    async function saveProvider() {
      try {
        const payload = {
          id: el("providerId").value.trim(),
          name: el("providerName").value.trim(),
          url: el("providerUrl").value.trim(),
          enabled: el("providerEnabled").checked,
          replaceOnSync: el("providerReplace").checked,
        };
        if (!payload.id || !payload.name || !payload.url) throw new Error("Fill provider ID, name and URL.");
        await requestJson("/admin/feed-providers", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...tokenHeader() },
          body: JSON.stringify(payload),
        });
        showToast("Provider saved.");
        clearProviderForm();
        await loadProviders();
      } catch (error) {
        showToast("Save provider failed: " + error.message);
      }
    }

    async function syncProvider(id) {
      try {
        const result = await requestJson(`/admin/feed-providers/${encodeURIComponent(id)}/sync`, {
          method: "POST",
          headers: tokenHeader(),
        });
        showToast(result.message || "Provider synced.");
        await loadProviders();
        await loadDeals();
        await loadSyncRuns();
      } catch (error) {
        showToast("Provider sync failed: " + error.message);
        await loadProviders();
        await loadSyncRuns();
      }
    }

    async function syncAllProviders() {
      try {
        const result = await requestJson("/admin/feed-providers/sync-all", {
          method: "POST",
          headers: tokenHeader(),
        });
        showToast(result.message || "Providers synced.");
        await loadProviders();
        await loadDeals();
        await loadSyncRuns();
      } catch (error) {
        showToast("Sync all failed: " + error.message);
        await loadProviders();
        await loadSyncRuns();
      }
    }

    async function deleteProvider(id) {
      if (!confirm(`Delete feed provider ${id}?`)) return;
      try {
        await requestJson(`/admin/feed-providers/${encodeURIComponent(id)}`, {
          method: "DELETE",
          headers: tokenHeader(),
        });
        showToast("Provider deleted.");
        await loadProviders();
      } catch (error) {
        showToast("Delete provider failed: " + error.message);
      }
    }



    async function loadSchedulerStatus() {
      try {
        schedulerStatus = await requestJson("/admin/feed-providers/scheduler/status", { headers: tokenHeader() });
        renderSchedulerStatus();
      } catch (error) {
        el("schedulerStatusBox").innerHTML = `<div class="muted">Failed to load scheduler status: ${escapeHtml(error.message)}</div>`;
      }
    }

    function renderSchedulerStatus() {
      if (!schedulerStatus) {
        el("schedulerStatusBox").innerHTML = '<div class="muted">Scheduler status is not loaded yet.</div>';
        return;
      }
      el("schedulerInterval").value = schedulerStatus.intervalSeconds || 3600;
      el("schedulerTimeout").value = schedulerStatus.timeoutSeconds || 20;
      el("schedulerRunOnStartup").checked = !!schedulerStatus.runOnStartup;
      const statusBadge = schedulerStatus.enabled
        ? '<span class="badge good">running</span>'
        : '<span class="badge">stopped</span>';
      const lastStatus = schedulerStatus.lastStatus === 'ok'
        ? '<span class="badge good">ok</span>'
        : schedulerStatus.lastStatus
          ? `<span class="badge hot">${escapeHtml(schedulerStatus.lastStatus)}</span>`
          : '<span class="badge">not run</span>';
      el("schedulerStatusBox").innerHTML = `
        <div class="scheduler-line"><span>State</span><strong>${statusBadge}</strong></div>
        <div class="scheduler-line"><span>Interval</span><strong>${escapeHtml(schedulerStatus.intervalSeconds || '—')} sec</strong></div>
        <div class="scheduler-line"><span>Last status</span><strong>${lastStatus}</strong></div>
        <div class="scheduler-line"><span>Last imported</span><strong>${escapeHtml(schedulerStatus.lastImportedCount || 0)}</strong></div>
        <div class="scheduler-line"><span>Deal count</span><strong>${escapeHtml(schedulerStatus.lastDealCount ?? '—')}</strong></div>
        <div class="scheduler-line"><span>Last run</span><strong>${escapeHtml(schedulerStatus.lastRunAt || 'never')}</strong></div>
        <div class="scheduler-message">${escapeHtml(schedulerStatus.lastMessage || schedulerStatus.lastError || 'No scheduler message yet.')}</div>
      `;
    }

    function schedulerTimeoutValue() {
      const value = Number(el("schedulerTimeout").value || 20);
      return Math.min(60, Math.max(3, value));
    }

    function schedulerIntervalValue() {
      const value = Number(el("schedulerInterval").value || 3600);
      return Math.min(86400, Math.max(60, value));
    }

    async function runSchedulerOnce() {
      try {
        const timeout = schedulerTimeoutValue();
        const result = await requestJson(`/admin/feed-providers/scheduler/run-once?timeout_seconds=${encodeURIComponent(timeout)}`, {
          method: "POST",
          headers: tokenHeader(),
        });
        showToast(result.message || "Scheduler run completed.");
        await loadSchedulerStatus();
        await loadProviders();
        await loadDeals();
        await loadSyncRuns();
      } catch (error) {
        showToast("Scheduler run failed: " + error.message);
        await loadSchedulerStatus();
        await loadSyncRuns();
      }
    }

    async function startScheduler() {
      try {
        const interval = schedulerIntervalValue();
        const timeout = schedulerTimeoutValue();
        const runOnStartup = el("schedulerRunOnStartup").checked;
        schedulerStatus = await requestJson(`/admin/feed-providers/scheduler/start?interval_seconds=${encodeURIComponent(interval)}&timeout_seconds=${encodeURIComponent(timeout)}&run_on_startup=${encodeURIComponent(runOnStartup)}`, {
          method: "POST",
          headers: tokenHeader(),
        });
        renderSchedulerStatus();
        showToast("Scheduler started.");
      } catch (error) {
        showToast("Start scheduler failed: " + error.message);
      }
    }

    async function stopScheduler() {
      try {
        schedulerStatus = await requestJson("/admin/feed-providers/scheduler/stop", {
          method: "POST",
          headers: tokenHeader(),
        });
        renderSchedulerStatus();
        showToast("Scheduler stopped.");
      } catch (error) {
        showToast("Stop scheduler failed: " + error.message);
      }
    }

    async function loadSyncRuns() {
      try {
        const data = await requestJson("/admin/feed-providers/sync-runs?limit=20", { headers: tokenHeader() });
        syncRuns = data.items || [];
        renderSyncRuns();
      } catch (error) {
        el("syncRunsList").innerHTML = `<div class="muted">Failed to load sync history: ${escapeHtml(error.message)}</div>`;
      }
    }

    function renderSyncRuns() {
      if (!syncRuns.length) {
        el("syncRunsList").innerHTML = '<div class="muted">No sync history yet.</div>';
        return;
      }
      el("syncRunsList").innerHTML = syncRuns.map((run) => `
        <div class="provider-row">
          <div>
            <strong>${escapeHtml(run.providerName || run.providerId)} ${run.status === 'ok' ? '<span class="badge good">ok</span>' : `<span class="badge hot">${escapeHtml(run.status || 'error')}</span>`}</strong>
            <span>${escapeHtml(run.providerId)} · ${escapeHtml(run.startedAt || '')}</span>
            <span>Imported: ${run.importedCount || 0} · Deals: ${run.dealCount ?? '—'} · Duration: ${run.durationMs || 0} ms</span>
            <span>${escapeHtml(run.message || '')}</span>
          </div>
        </div>
      `).join("");
    }

    async function clearSyncRuns() {
      if (!confirm("Clear feed sync history?")) return;
      try {
        const result = await requestJson("/admin/feed-providers/sync-runs", {
          method: "DELETE",
          headers: tokenHeader(),
        });
        showToast(result.message || "Sync history cleared.");
        await loadSyncRuns();
      } catch (error) {
        showToast("Clear sync history failed: " + error.message);
      }
    }

    function formatMoney(value) {
      const number = Number(value || 0);
      return number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;" }[char]));
    }

    function escapeAttr(value) { return escapeHtml(value).replace(/`/g, "&#096;"); }

    setStoredToken();
    loadAll();
  </script>
</body>
</html>
"""
