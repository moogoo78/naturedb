// Entry module: fetch live data from the Nature-Scribe API, route between
// Explorer and Annotation views via URL hash, drive pagination + filter state.

import { renderExplorer } from "./explorer.js";
import { renderAnnotation } from "./annotation.js";

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

let collections = [];     // [{id, label, count}]
let mockDataset = null;   // for the annotation view fallback

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

async function loadMock() {
  if (mockDataset) return mockDataset;
  const res = await fetch(mockUrl, { credentials: "same-origin" });
  mockDataset = res.ok ? await res.json() : { specimens: [], facets: {} };
  return mockDataset;
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

function setNavActive(screen) {
  document.querySelectorAll("#topnav button[data-screen]").forEach((b) => {
    b.classList.toggle("on", b.dataset.screen === screen);
  });
}

const explorerCallbacks = {
  onParamsChanged: async (next) => {
    Object.assign(explorerState, next);
    // Any non-page change resets to page 1.
    if (!("page" in next)) explorerState.page = 1;
    await renderExplorerNow();
  },
  onOpenAnnotation: (specimen) => {
    location.hash = specimen.id;
  },
};

async function renderExplorerNow() {
  const page = await loadSpecimensPage();
  renderExplorer(root, {
    collections,
    specimens: page.items,
    pagination: { page: page.page, perPage: page.per_page, total: page.total },
    state: explorerState,
    mockFacets: mockDataset?.facets,
  }, explorerCallbacks);
}

async function showExplorer() {
  setNavActive("explorer");
  await renderExplorerNow();
}

function showAnnotation(specimen) {
  setNavActive("annotation");
  renderAnnotation(root, specimen, {
    onBack: () => {
      history.replaceState(null, "", location.pathname + location.search);
      resolveScreen();
    },
  });
}

function findMockById(id) {
  return mockDataset?.specimens?.find((s) => s.id === id) || null;
}

async function resolveScreen() {
  const hash = location.hash.replace(/^#/, "");
  if (hash) {
    const specimen = findMockById(hash);
    if (specimen) { showAnnotation(specimen); return; }
    history.replaceState(null, "", location.pathname + location.search);
  }
  await showExplorer();
}

window.addEventListener("hashchange", resolveScreen);

document.querySelector("#topnav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-screen]");
  if (!btn) return;
  const screen = btn.dataset.screen;
  if (screen === "explorer") {
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    resolveScreen();
  } else if (screen === "annotation") {
    const current = location.hash.replace(/^#/, "");
    if (!current && mockDataset?.specimens?.length) {
      location.hash = mockDataset.specimens[1]?.id || mockDataset.specimens[0].id;
    }
  }
});

(async () => {
  try {
    await Promise.all([loadCollections(), loadMock()]);
    await resolveScreen();
  } catch (err) {
    root.innerHTML = `<div style="padding:48px;font-family:var(--serif);color:var(--oxblood)">Failed to load: ${err.message}</div>`;
    console.error(err);
  }
})();
