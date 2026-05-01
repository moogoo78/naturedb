// Entry module: fetch live data from the Nature-Scribe API and render the
// Explorer. Card click opens the Annotation view as a modal overlay above the
// Explorer (no URL routing — modal is in-page DOM only).

import { renderExplorer } from "./explorer.js";
import { openAnnotationModal, closeAnnotationModal } from "./annotation.js";

const root = document.getElementById("annotate-root");
const apiBase = root.dataset.apiBase;
const mockUrl = root.dataset.mockUrl;

const explorerState = {
  collectionId: null,
  q: "",
  sort: "recent",
  page: 1,
  perPage: 50,
};

let collections = [];
let mockFacets = null;
let currentSpecimens = [];

async function api(path, params) {
  const url = new URL(apiBase + path, location.origin);
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== null && v !== undefined && v !== "") url.searchParams.set(k, v);
  }
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`${url.pathname} → HTTP ${res.status}`);
  return await res.json();
}

async function loadCollections() {
  const data = await api("/collections");
  collections = data.items || [];
}

async function loadMockFacets() {
  // Mock facets only feed the inert rail groups (kingdom/family/region/status).
  try {
    const res = await fetch(mockUrl, { credentials: "same-origin" });
    if (res.ok) mockFacets = (await res.json()).facets;
  } catch { /* non-fatal */ }
}

async function loadSpecimensPage() {
  return await api("/specimens", {
    collection_id: explorerState.collectionId,
    q: explorerState.q,
    sort: explorerState.sort,
    page: explorerState.page,
    per_page: explorerState.perPage,
  });
}

const explorerCallbacks = {
  onParamsChanged: async (next) => {
    Object.assign(explorerState, next);
    if (!("page" in next)) explorerState.page = 1;
    await renderExplorerNow();
  },
  onOpenAnnotation: (specimen) => {
    const index = currentSpecimens.findIndex((s) => s.id === specimen.id);
    openAnnotationModal(specimen, { onClose: () => {} }, { specimens: currentSpecimens, index });
  },
};

async function renderExplorerNow() {
  const page = await loadSpecimensPage();
  currentSpecimens = page.items;
  renderExplorer(root, {
    collections,
    specimens: page.items,
    pagination: { page: page.page, perPage: page.per_page, total: page.total },
    state: explorerState,
    mockFacets,
  }, explorerCallbacks);
}

// Topnav: Explore is the only working screen; Annotate is a hint to open
// a specimen card. Closing any open modal returns the user to the explorer.
document.querySelector("#topnav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-screen]");
  if (!btn) return;
  if (btn.dataset.screen === "explorer") closeAnnotationModal();
});

(async () => {
  try {
    await Promise.all([loadCollections(), loadMockFacets()]);
    await renderExplorerNow();
  } catch (err) {
    root.innerHTML = `<div style="padding:48px;color:var(--oxblood)">Failed to load: ${err.message}</div>`;
    console.error(err);
  }
})();
