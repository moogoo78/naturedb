// Explorer view — faceted filtering, search, sort, and specimen card grid.

import { renderPlate } from "./plates.js";

const STATUS_LABEL = {
  verified: { label: "Verified", className: "verified" },
  "in-review": { label: "In review", className: "review" },
  "needs-help": { label: "Needs help", className: "help" },
};

const HISTOGRAM = [3, 5, 8, 6, 9, 12, 7, 10, 14, 11, 8, 6, 4, 5, 3, 2];

let currentState = null;
let currentRoot = null;
let currentCallbacks = null;

function defaultState() {
  return {
    selectedKingdoms: new Set(),
    selectedFamilies: new Set(),
    selectedStatuses: new Set(),
    completeness: [0, 100],
    search: "",
    sort: "recent",
    view: "grid",
  };
}

function renderCompletenessBar(value) {
  const segs = 5;
  const filled = Math.round((value / 100) * segs);
  let bars = "";
  for (let i = 0; i < segs; i++) {
    bars += `<span class="seg ${i < filled ? "filled" : ""}"></span>`;
  }
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
  const idTail = specimen.id.split("-").slice(-1)[0];
  const yearStr = (specimen.collected || "").slice(0, 4);
  const localityHead = (specimen.locality || "").split(",")[0];
  const pendingHtml = specimen.pending > 0
    ? `<span class="pending">· ${specimen.pending} pending</span>`
    : "";
  return `
    <article class="card" data-id="${escapeAttr(specimen.id)}">
      <div class="card-plate">
        ${renderPlate(specimen)}
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

function escapeHtml(s) {
  return String(s ?? "").replace(/[<>&"']/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

function applyFilters(specimens, state) {
  const q = state.search.trim().toLowerCase();
  let result = specimens.filter((s) => {
    if (state.selectedKingdoms.size && !state.selectedKingdoms.has(s.kingdom)) return false;
    if (state.selectedFamilies.size && !state.selectedFamilies.has(s.family)) return false;
    if (state.selectedStatuses.size && !state.selectedStatuses.has(s.status)) return false;
    if (s.completeness < state.completeness[0] || s.completeness > state.completeness[1]) return false;
    if (q) {
      const hay = `${s.taxon} ${s.common} ${s.locality} ${s.collector}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  if (state.sort === "completeness-asc") result.sort((a, b) => a.completeness - b.completeness);
  else if (state.sort === "completeness-desc") result.sort((a, b) => b.completeness - a.completeness);
  else if (state.sort === "catalog") result.sort((a, b) => a.catalog.localeCompare(b.catalog));
  return result;
}

function activeFiltersCount(state) {
  return state.selectedKingdoms.size + state.selectedFamilies.size + state.selectedStatuses.size +
    (state.completeness[0] !== 0 || state.completeness[1] !== 100 ? 1 : 0);
}

function renderRail(specimens, facets, state) {
  const activeCount = activeFiltersCount(state);
  const kingdomRows = facets.kingdom.map((k) => {
    const count = specimens.filter((s) => s.kingdom === k).length;
    const checked = state.selectedKingdoms.has(k);
    return `
      <label class="facet-row">
        <input type="checkbox" data-facet="kingdom" data-value="${escapeAttr(k)}" ${checked ? "checked" : ""}>
        <span class="facet-label">${escapeHtml(k)}</span>
        <span class="facet-count">${count}</span>
      </label>
    `;
  }).join("");

  const familyRows = facets.family.slice(0, 7).map((f) => {
    const count = specimens.filter((s) => s.family === f).length;
    const checked = state.selectedFamilies.has(f);
    return `
      <label class="facet-row">
        <input type="checkbox" data-facet="family" data-value="${escapeAttr(f)}" ${checked ? "checked" : ""}>
        <span class="facet-label">${escapeHtml(f)}</span>
        <span class="facet-count">${count || "—"}</span>
      </label>
    `;
  }).join("");

  const regionRows = facets.region.slice(0, 5).map((r) => `
    <label class="facet-row">
      <input type="checkbox" disabled>
      <span class="facet-label">${escapeHtml(r)}</span>
      <span class="facet-count">—</span>
    </label>
  `).join("");

  const histogramBars = HISTOGRAM.map((h) => `<span class="hist-bar" style="height:${h * 4}px"></span>`).join("");

  const statusRows = facets.status.map((s) => {
    const checked = state.selectedStatuses.has(s.key);
    return `
      <label class="facet-row">
        <input type="checkbox" data-facet="status" data-value="${escapeAttr(s.key)}" ${checked ? "checked" : ""}>
        <span class="facet-label">${escapeHtml(s.label)}</span>
        <span class="facet-count">${s.count}</span>
      </label>
    `;
  }).join("");

  const cMin = state.completeness[0];
  const cMax = state.completeness[1];
  const cLeft = cMin;
  const cRight = 100 - cMax;

  return `
    <aside class="rail">
      <div class="rail-head">
        <h2 class="rail-title">Refine</h2>
        ${activeCount > 0 ? `<button class="clear-btn" id="clear-filters">Clear (${activeCount})</button>` : ""}
      </div>

      <div class="facet-group" data-group="kingdom">
        <button class="facet-head" type="button"><span>Kingdom</span><span class="facet-chev">−</span></button>
        <div class="facet-body">${kingdomRows}</div>
      </div>

      <div class="facet-group" data-group="family">
        <button class="facet-head" type="button"><span>Family</span><span class="facet-chev">−</span></button>
        <div class="facet-body">${familyRows}<button class="more-btn" type="button">+ 24 more families</button></div>
      </div>

      <div class="facet-group" data-group="region">
        <button class="facet-head" type="button"><span>Region</span><span class="facet-chev">−</span></button>
        <div class="facet-body">${regionRows}<button class="more-btn" type="button">+ 11 more regions</button></div>
      </div>

      <div class="facet-group" data-group="date">
        <button class="facet-head" type="button"><span>Date collected</span><span class="facet-chev">−</span></button>
        <div class="facet-body">
          <div class="facet-range">
            <div class="facet-range-head"><span>Year range</span><span class="facet-count">1859–2014</span></div>
            <div class="range-track"><div class="range-fill" style="left:${((1859 - 1850) / (2025 - 1850)) * 100}%;right:${100 - ((2014 - 1850) / (2025 - 1850)) * 100}%"></div></div>
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
            <div class="facet-range-head"><span>Score</span><span class="facet-count">${cMin}–${cMax}</span></div>
            <div class="range-track"><div class="range-fill" style="left:${cLeft}%;right:${cRight}%"></div></div>
          </div>
          <div class="facet-quick">
            <button type="button" data-quick="0,50">Low (&lt; 50%)</button>
            <button type="button" data-quick="50,80">Mid</button>
            <button type="button" data-quick="80,100">High</button>
          </div>
        </div>
      </div>

      <div class="facet-group" data-group="handwritten">
        <button class="facet-head" type="button"><span>Has handwritten label</span><span class="facet-chev">−</span></button>
        <div class="facet-body">
          <label class="facet-row"><input type="checkbox" disabled><span class="facet-label">Untranscribed</span><span class="facet-count">9</span></label>
          <label class="facet-row"><input type="checkbox" disabled><span class="facet-label">Partial</span><span class="facet-count">4</span></label>
          <label class="facet-row"><input type="checkbox" disabled><span class="facet-label">Verified</span><span class="facet-count">3</span></label>
        </div>
      </div>
    </aside>
  `;
}

function renderResultBar(filtered, total, state) {
  const chips = [];
  for (const k of state.selectedKingdoms) {
    chips.push(`<button class="chip" data-chip-facet="kingdom" data-chip-value="${escapeAttr(k)}">${escapeHtml(k)} <span class="chip-x">×</span></button>`);
  }
  for (const f of state.selectedFamilies) {
    chips.push(`<button class="chip" data-chip-facet="family" data-chip-value="${escapeAttr(f)}">${escapeHtml(f)} <span class="chip-x">×</span></button>`);
  }
  for (const s of state.selectedStatuses) {
    chips.push(`<button class="chip" data-chip-facet="status" data-chip-value="${escapeAttr(s)}">${escapeHtml(s)} <span class="chip-x">×</span></button>`);
  }

  return `
    <div class="result-bar">
      <div class="result-count">
        <span class="bignum">${filtered}</span>
        <span class="tinytext">specimens · ${total} total</span>
      </div>
      <div class="active-chips">${chips.join("")}</div>
      <div class="result-help">Showing specimens that need community attention first</div>
    </div>
  `;
}

function renderToolbar(state) {
  return `
    <div class="explorer-toolbar">
      <div class="search-wrap">
        <span class="search-icon">⌕</span>
        <input class="search" id="explorer-search" placeholder="Search taxa, collectors, places…" value="${escapeAttr(state.search)}">
        <span class="search-hint">⌘K</span>
      </div>
      <div class="toolbar-right">
        <div class="seg" id="view-seg">
          <button type="button" data-view="grid" class="${state.view === "grid" ? "on" : ""}">Plates</button>
          <button type="button" data-view="list" class="${state.view === "list" ? "on" : ""}">List</button>
          <button type="button" data-view="map" class="${state.view === "map" ? "on" : ""}">Map</button>
        </div>
        <select class="select" id="explorer-sort">
          <option value="recent" ${state.sort === "recent" ? "selected" : ""}>Recently updated</option>
          <option value="catalog" ${state.sort === "catalog" ? "selected" : ""}>Catalog №</option>
          <option value="completeness-asc" ${state.sort === "completeness-asc" ? "selected" : ""}>Least complete first</option>
          <option value="completeness-desc" ${state.sort === "completeness-desc" ? "selected" : ""}>Most complete first</option>
        </select>
      </div>
    </div>
  `;
}

function renderGrid(filtered, view) {
  if (view === "map") {
    return `<div class="grid map">Map view coming soon</div>`;
  }
  const cards = filtered.map(renderCard).join("");
  return `<div class="grid ${view === "list" ? "list" : ""}">${cards}</div>`;
}

function rerenderResults(specimens) {
  const filtered = applyFilters(specimens, currentState);
  const main = currentRoot.querySelector(".main");
  if (!main) return;
  main.querySelector(".result-bar")?.remove();
  main.querySelector(".grid")?.remove();
  main.insertAdjacentHTML("beforeend", renderResultBar(filtered.length, specimens.length, currentState));
  main.insertAdjacentHTML("beforeend", renderGrid(filtered, currentState.view));

  // Update clear button visibility/count without re-rendering the rail.
  const railHead = currentRoot.querySelector(".rail-head");
  if (railHead) {
    const existing = railHead.querySelector("#clear-filters");
    const count = activeFiltersCount(currentState);
    if (count > 0) {
      if (existing) {
        existing.textContent = `Clear (${count})`;
      } else {
        railHead.insertAdjacentHTML("beforeend", `<button class="clear-btn" id="clear-filters">Clear (${count})</button>`);
      }
    } else if (existing) {
      existing.remove();
    }
  }
  // Update the completeness range head text and the fill positions.
  const cMin = currentState.completeness[0], cMax = currentState.completeness[1];
  const completenessGroup = currentRoot.querySelector('[data-group="completeness"]');
  if (completenessGroup) {
    const head = completenessGroup.querySelector(".facet-range-head .facet-count");
    if (head) head.textContent = `${cMin}–${cMax}`;
    const fill = completenessGroup.querySelector(".range-fill");
    if (fill) {
      fill.style.left = `${cMin}%`;
      fill.style.right = `${100 - cMax}%`;
    }
  }
}

function debounce(fn, ms) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function attachExplorerEvents(specimens) {
  const root = currentRoot;

  // Facet checkboxes — event delegation on the rail.
  root.querySelector(".rail")?.addEventListener("change", (e) => {
    const t = e.target;
    if (!(t instanceof HTMLInputElement) || t.type !== "checkbox") return;
    const facet = t.dataset.facet;
    const value = t.dataset.value;
    if (!facet || !value) return;
    const set = facet === "kingdom" ? currentState.selectedKingdoms
      : facet === "family" ? currentState.selectedFamilies
      : facet === "status" ? currentState.selectedStatuses
      : null;
    if (!set) return;
    if (t.checked) set.add(value); else set.delete(value);
    rerenderResults(specimens);
  });

  // Facet group collapse on header click.
  root.querySelector(".rail")?.addEventListener("click", (e) => {
    const head = e.target.closest(".facet-head");
    if (!head) return;
    const group = head.parentElement;
    const body = group.querySelector(".facet-body");
    const chev = head.querySelector(".facet-chev");
    const collapsed = body.style.display === "none";
    body.style.display = collapsed ? "" : "none";
    if (chev) chev.textContent = collapsed ? "−" : "+";
  });

  // Completeness quick buttons.
  root.querySelector(".rail")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-quick]");
    if (!btn) return;
    const [a, b] = btn.dataset.quick.split(",").map(Number);
    currentState.completeness = [a, b];
    rerenderResults(specimens);
  });

  // Clear filters.
  root.querySelector(".rail")?.addEventListener("click", (e) => {
    if (e.target.id !== "clear-filters") return;
    currentState.selectedKingdoms.clear();
    currentState.selectedFamilies.clear();
    currentState.selectedStatuses.clear();
    currentState.completeness = [0, 100];
    currentState.search = "";
    // Rerender the whole shell to reset checkboxes.
    rerenderShell(specimens, currentRoot.dataset.facets ? JSON.parse(currentRoot.dataset.facets) : null);
  });

  // Search.
  const searchInput = root.querySelector("#explorer-search");
  if (searchInput) {
    const onSearch = debounce(() => {
      currentState.search = searchInput.value;
      rerenderResults(specimens);
    }, 80);
    searchInput.addEventListener("input", onSearch);
  }

  // Sort.
  root.querySelector("#explorer-sort")?.addEventListener("change", (e) => {
    currentState.sort = e.target.value;
    rerenderResults(specimens);
  });

  // View toggle.
  root.querySelector("#view-seg")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-view]");
    if (!btn) return;
    currentState.view = btn.dataset.view;
    root.querySelectorAll("#view-seg button").forEach((b) => b.classList.toggle("on", b === btn));
    rerenderResults(specimens);
  });

  // Card click → open annotation.
  root.querySelector(".main")?.addEventListener("click", (e) => {
    const card = e.target.closest(".card");
    if (!card) return;
    const id = card.dataset.id;
    if (id && currentCallbacks?.onOpenAnnotation) {
      const specimen = specimens.find((s) => s.id === id);
      if (specimen) currentCallbacks.onOpenAnnotation(specimen);
    }
  });

  // Active chip remove.
  root.querySelector(".main")?.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-chip-facet]");
    if (!chip) return;
    const facet = chip.dataset.chipFacet;
    const value = chip.dataset.chipValue;
    const set = facet === "kingdom" ? currentState.selectedKingdoms
      : facet === "family" ? currentState.selectedFamilies
      : facet === "status" ? currentState.selectedStatuses
      : null;
    if (set) {
      set.delete(value);
      // Uncheck the corresponding checkbox in the rail.
      const cb = root.querySelector(`input[data-facet="${facet}"][data-value="${CSS.escape(value)}"]`);
      if (cb) cb.checked = false;
      rerenderResults(specimens);
    }
  });
}

function rerenderShell(specimens, facets) {
  const filtered = applyFilters(specimens, currentState);
  currentRoot.innerHTML = `
    <div class="explorer">
      ${renderRail(specimens, facets, currentState)}
      <main class="main">
        ${renderToolbar(currentState)}
        ${renderResultBar(filtered.length, specimens.length, currentState)}
        ${renderGrid(filtered, currentState.view)}
      </main>
    </div>
  `;
  currentRoot.dataset.facets = JSON.stringify(facets);
  attachExplorerEvents(specimens);
}

export function renderExplorer(root, { specimens, facets }, callbacks) {
  currentRoot = root;
  currentCallbacks = callbacks;
  if (!currentState) currentState = defaultState();
  rerenderShell(specimens, facets);
}

export function resetExplorerState() {
  currentState = null;
}
