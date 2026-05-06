// Explorer view — server-driven specimen grid.
//
// The Institution/Collection facet is the only active filter wired to the API.
// Other rail facet groups remain rendered for layout parity but are inert in
// this iteration (they don't mutate state or trigger refetches).

import { renderPlate } from "./plates.js";

const STATUS_LABEL = {
  verified: { label: "Verified", className: "verified" },
  "in-review": { label: "In review", className: "review" },
  "needs-help": { label: "Needs help", className: "help" },
};

const HISTOGRAM = [3, 5, 8, 6, 9, 12, 7, 10, 14, 11, 8, 6, 4, 5, 3, 2];

let currentRoot = null;
let currentCallbacks = null;
let currentView = "grid"; // "grid" | "list" — local UI state, no refetch on change

function escapeHtml(s) {
  return String(s ?? "").replace(/[<>&"']/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

function renderCompletenessBar(value) {
  const segs = 5;
  const filled = Math.round((value / 100) * segs);
  let bars = "";
  for (let i = 0; i < segs; i++) bars += `<span class="seg ${i < filled ? "filled" : ""}"></span>`;
  return `
    <div class="completeness">
      <span class="completeness-label">${value}%</span>
      <div class="completeness-bar">${bars}</div>
    </div>
  `;
}

function renderStatusBadge(status) {
  const s = STATUS_LABEL[status];
  if (!s) return "";
  return `<span class="status-badge ${s.className}">${s.label}</span>`;
}

function renderCard(specimen) {
  const idTail = (specimen.catalog || specimen.id).split(/[\s\-·]/).pop();
  const yearStr = (specimen.collected || "").slice(0, 4);
  const localityHead = (specimen.locality || "").split(",")[0];
  const pendingHtml = specimen.pending > 0
    ? `<span class="pending">· ${specimen.pending} pending</span>`
    : "";
  const plateHtml = specimen.cover_url
    ? `<img class="card-image" src="${escapeAttr(specimen.cover_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
    : renderPlate(specimen);
  return `
    <article class="card" data-id="${escapeAttr(specimen.id)}">
      <div class="card-plate">
        ${plateHtml}
        <div class="card-corner-stamp">№ ${escapeHtml(idTail)}</div>
      </div>
      <div class="card-body">
        <div class="card-row-top">
          <span class="card-catalog">${escapeHtml(specimen.catalog)}</span>
          ${renderStatusBadge(specimen.status)}
        </div>
        <h3 class="card-taxon">${escapeHtml(specimen.taxon)}</h3>
        <div class="card-common">${escapeHtml(specimen.common)}</div>
        <div class="card-meta">
          <span>${escapeHtml(specimen.family)}</span>
          <span class="dot">·</span>
          <span>${escapeHtml(yearStr)}</span>
          <span class="dot">·</span>
          <span>${escapeHtml(localityHead)}</span>
        </div>
        <div class="card-foot">
          ${renderCompletenessBar(specimen.completeness)}
          <div class="card-annot">
            <span class="annot-num">${specimen.annotations}</span>
            <span class="annot-label">annotations</span>
            ${pendingHtml}
          </div>
        </div>
      </div>
    </article>
  `;
}

function renderInstitutionFacet(collections, selectedId) {
  const allRow = `
    <label class="facet-row">
      <input type="radio" name="scribe-collection" data-collection-id="" ${selectedId == null ? "checked" : ""}>
      <span class="facet-label">All collections</span>
    </label>
  `;
  const rows = collections.map((c) => {
    const [org, sub] = c.label.split(":");
    const display = sub
      ? `<span class="facet-org">${escapeHtml(org)}</span><span class="facet-sub">${escapeHtml(sub)}</span>`
      : `<span class="facet-org solo">${escapeHtml(org)}</span>`;
    return `
      <label class="facet-row">
        <input type="radio" name="scribe-collection" data-collection-id="${c.id}" ${selectedId === c.id ? "checked" : ""}>
        <span class="facet-label">${display}</span>
        <span class="facet-count">${c.count.toLocaleString()}</span>
      </label>
    `;
  }).join("");
  return `
    <div class="facet-group" data-group="institution">
      <button class="facet-head" type="button"><span>Institution / Collection</span><span class="facet-chev">−</span></button>
      <div class="facet-body">${allRow}${rows}</div>
    </div>
  `;
}

function renderInertFacets(facets) {
  const f = facets || { kingdom: [], family: [], region: [], status: [] };
  const kingdomRows = (f.kingdom || []).map((k) => `
    <label class="facet-row inert">
      <input type="checkbox" disabled>
      <span class="facet-label">${escapeHtml(k)}</span>
      <span class="facet-count">—</span>
    </label>
  `).join("");
  const familyRows = (f.family || []).slice(0, 7).map((fam) => `
    <label class="facet-row inert">
      <input type="checkbox" disabled>
      <span class="facet-label">${escapeHtml(fam)}</span>
      <span class="facet-count">—</span>
    </label>
  `).join("");
  const regionRows = (f.region || []).slice(0, 5).map((r) => `
    <label class="facet-row inert">
      <input type="checkbox" disabled>
      <span class="facet-label">${escapeHtml(r)}</span>
      <span class="facet-count">—</span>
    </label>
  `).join("");
  const statusRows = (f.status || []).map((s) => `
    <label class="facet-row inert">
      <input type="checkbox" disabled>
      <span class="facet-label">${escapeHtml(s.label)}</span>
      <span class="facet-count">${s.count}</span>
    </label>
  `).join("");
  const histogramBars = HISTOGRAM.map((h) => `<span class="hist-bar" style="height:${h * 4}px"></span>`).join("");

  return `
    <div class="facet-group" data-group="kingdom">
      <button class="facet-head" type="button"><span>Kingdom</span><span class="facet-chev">−</span></button>
      <div class="facet-body">${kingdomRows}</div>
    </div>

    <div class="facet-group" data-group="family">
      <button class="facet-head" type="button"><span>Family</span><span class="facet-chev">−</span></button>
      <div class="facet-body">${familyRows}</div>
    </div>

    <div class="facet-group" data-group="region">
      <button class="facet-head" type="button"><span>Region</span><span class="facet-chev">−</span></button>
      <div class="facet-body">${regionRows}</div>
    </div>

    <div class="facet-group" data-group="date">
      <button class="facet-head" type="button"><span>Date collected</span><span class="facet-chev">−</span></button>
      <div class="facet-body">
        <div class="facet-range">
          <div class="facet-range-head"><span>Year range</span><span class="facet-count">1859–2014</span></div>
          <div class="range-track"><div class="range-fill" style="left:5%;right:5%"></div></div>
        </div>
        <div class="facet-histogram">${histogramBars}</div>
      </div>
    </div>

    <div class="facet-group" data-group="status">
      <button class="facet-head" type="button"><span>Annotation status</span><span class="facet-chev">−</span></button>
      <div class="facet-body">${statusRows}</div>
    </div>

    <div class="facet-group" data-group="completeness">
      <button class="facet-head" type="button"><span>Completeness</span><span class="facet-chev">−</span></button>
      <div class="facet-body">
        <div class="facet-range">
          <div class="facet-range-head"><span>Score</span><span class="facet-count">0–100</span></div>
          <div class="range-track"><div class="range-fill" style="left:0%;right:0%"></div></div>
        </div>
      </div>
    </div>

    <div class="facet-group" data-group="handwritten">
      <button class="facet-head" type="button"><span>Has handwritten label</span><span class="facet-chev">−</span></button>
      <div class="facet-body">
        <label class="facet-row inert"><input type="checkbox" disabled><span class="facet-label">Untranscribed</span><span class="facet-count">—</span></label>
        <label class="facet-row inert"><input type="checkbox" disabled><span class="facet-label">Partial</span><span class="facet-count">—</span></label>
      </div>
    </div>
  `;
}

function renderRail(collections, selectedId, mockFacets) {
  return `
    <aside class="rail">
      <div class="rail-head">
        <h2 class="rail-title">Refine</h2>
      </div>
      ${renderInstitutionFacet(collections, selectedId)}
      ${renderInertFacets(mockFacets)}
    </aside>
  `;
}

function renderResultBar(pagination, selectedLabel) {
  const start = (pagination.page - 1) * pagination.perPage + 1;
  const end = Math.min(pagination.page * pagination.perPage, pagination.total);
  const range = pagination.total ? `${start.toLocaleString()}–${end.toLocaleString()}` : "0";
  return `
    <div class="result-bar">
      <div class="result-count">
        <span class="bignum">${pagination.total.toLocaleString()}</span>
        <span class="tinytext">specimens · showing ${range}</span>
      </div>
      ${selectedLabel ? `<div class="active-chips"><span class="chip">${escapeHtml(selectedLabel)}</span></div>` : ""}
    </div>
  `;
}

function renderToolbar(state) {
  return `
    <div class="explorer-toolbar">
      <div class="search-wrap">
        <span class="search-icon">⌕</span>
        <input class="search" id="explorer-search" placeholder="Search taxa, collectors, places…" value="${escapeAttr(state.q)}">
        <span class="search-hint">⌘K</span>
      </div>
      <div class="toolbar-right">
        <div class="seg" id="view-seg">
          <button type="button" data-view="grid" class="${currentView === "grid" ? "on" : ""}">Card</button>
          <button type="button" data-view="list" class="${currentView === "list" ? "on" : ""}">List</button>
        </div>
        <select class="select" id="explorer-sort">
          <option value="recent" ${state.sort === "recent" ? "selected" : ""}>Recently updated</option>
          <option value="catalog" ${state.sort === "catalog" ? "selected" : ""}>Catalog №</option>
        </select>
      </div>
    </div>
  `;
}

function renderGrid(specimens) {
  if (!specimens.length) {
    return `<div class="grid empty">No specimens match the current filters.</div>`;
  }
  const cls = currentView === "list" ? "grid list" : "grid";
  return `<div class="${cls}">${specimens.map(renderCard).join("")}</div>`;
}

function renderPagination(pagination) {
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.perPage));
  const onFirst = pagination.page <= 1;
  const onLast = pagination.page >= totalPages;
  return `
    <nav class="pagination">
      <button type="button" id="page-prev" ${onFirst ? "disabled" : ""}>‹ Prev</button>
      <span class="page-indicator">
        Page
        <input
          type="number"
          id="page-input"
          class="page-input"
          min="1"
          max="${totalPages}"
          step="1"
          value="${pagination.page}"
          aria-label="Jump to page">
        of <span class="page-total">${totalPages.toLocaleString()}</span>
      </span>
      <button type="button" id="page-next" ${onLast ? "disabled" : ""}>Next ›</button>
    </nav>
  `;
}

function debounce(fn, ms) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function attachEvents(props, callbacks) {
  const root = currentRoot;

  // Institution / Collection radio.
  root.querySelector(".rail")?.addEventListener("change", (e) => {
    const t = e.target;
    if (!(t instanceof HTMLInputElement) || t.name !== "scribe-collection") return;
    const raw = t.dataset.collectionId;
    const collectionId = raw ? Number(raw) : null;
    callbacks.onParamsChanged({ collectionId });
  });

  // Inert facet groups: still allow header-click collapse for layout parity.
  root.querySelector(".rail")?.addEventListener("click", (e) => {
    const head = e.target.closest(".facet-head");
    if (!head) return;
    const body = head.parentElement.querySelector(".facet-body");
    const chev = head.querySelector(".facet-chev");
    const collapsed = body.style.display === "none";
    body.style.display = collapsed ? "" : "none";
    if (chev) chev.textContent = collapsed ? "−" : "+";
  });

  // Search.
  const searchInput = root.querySelector("#explorer-search");
  if (searchInput) {
    const onSearch = debounce(() => {
      callbacks.onParamsChanged({ q: searchInput.value });
    }, 250);
    searchInput.addEventListener("input", onSearch);
  }

  // Sort.
  root.querySelector("#explorer-sort")?.addEventListener("change", (e) => {
    callbacks.onParamsChanged({ sort: e.target.value });
  });

  // View toggle — purely UI; toggles classes without refetching.
  root.querySelector("#view-seg")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-view]");
    if (!btn) return;
    currentView = btn.dataset.view === "list" ? "list" : "grid";
    root.querySelectorAll("#view-seg button").forEach((b) => b.classList.toggle("on", b === btn));
    const grid = root.querySelector(".grid");
    if (grid) grid.classList.toggle("list", currentView === "list");
  });

  // Pagination.
  root.querySelector("#page-prev")?.addEventListener("click", () => {
    if (props.pagination.page > 1) callbacks.onParamsChanged({ page: props.pagination.page - 1 });
  });
  root.querySelector("#page-next")?.addEventListener("click", () => {
    const totalPages = Math.max(1, Math.ceil(props.pagination.total / props.pagination.perPage));
    if (props.pagination.page < totalPages) callbacks.onParamsChanged({ page: props.pagination.page + 1 });
  });

  // Pagination input — jump to page on Enter or blur.
  const pageInput = root.querySelector("#page-input");
  if (pageInput) {
    const totalPages = Math.max(1, Math.ceil(props.pagination.total / props.pagination.perPage));
    const submit = () => {
      const raw = parseInt(pageInput.value, 10);
      if (Number.isNaN(raw)) {
        pageInput.value = props.pagination.page;
        return;
      }
      const target = Math.min(Math.max(1, raw), totalPages);
      if (target !== props.pagination.page) {
        callbacks.onParamsChanged({ page: target });
      } else {
        pageInput.value = target;  // normalize clamped/no-op input
      }
    };
    pageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); submit(); }
    });
    pageInput.addEventListener("blur", submit);
  }

  // Card click → annotation view.
  root.querySelector(".main")?.addEventListener("click", (e) => {
    const card = e.target.closest(".card");
    if (!card) return;
    const id = card.dataset.id;
    const specimen = props.specimens.find((s) => s.id === id);
    if (specimen && callbacks.onOpenAnnotation) callbacks.onOpenAnnotation(specimen);
  });
}

export function renderExplorer(root, props, callbacks) {
  currentRoot = root;
  currentCallbacks = callbacks;

  const { collections, specimens, pagination, state, mockFacets } = props;
  const selected = collections.find((c) => c.id === state.collectionId);
  const selectedLabel = selected ? selected.label : null;

  root.innerHTML = `
    <div class="explorer">
      ${renderRail(collections, state.collectionId, mockFacets)}
      <main class="main">
        ${renderToolbar(state)}
        ${renderResultBar(pagination, selectedLabel)}
        ${renderGrid(specimens)}
        ${renderPagination(pagination)}
      </main>
    </div>
  `;
  attachEvents(props, callbacks);
}

export function resetExplorerState() {
  // No-op: state lives in app.js now.
}
