// Entry module: fetch mock data, route between Explorer and Annotation views
// based on URL hash, and orchestrate transitions.

import { renderExplorer } from "./explorer.js";
import { renderAnnotation } from "./annotation.js";

const root = document.getElementById("annotate-root");
const dataUrl = root.dataset.staticUrl;

let dataset = null;

async function loadDataset() {
  if (dataset) return dataset;
  const res = await fetch(dataUrl, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`Failed to load specimens.mock.json: ${res.status}`);
  dataset = await res.json();
  return dataset;
}

function findById(id) {
  return dataset.specimens.find((s) => s.id === id) || null;
}

function setNavActive(screen) {
  document.querySelectorAll("#topnav button[data-screen]").forEach((b) => {
    b.classList.toggle("on", b.dataset.screen === screen);
  });
}

function showExplorer() {
  setNavActive("explorer");
  renderExplorer(root, dataset, {
    onOpenAnnotation: (specimen) => {
      // Update hash; the hashchange listener will trigger the transition.
      location.hash = specimen.id;
    },
  });
}

function showAnnotation(specimen) {
  setNavActive("annotation");
  renderAnnotation(root, specimen, {
    onBack: () => {
      // Clear hash; hashchange listener handles the transition.
      history.replaceState(null, "", location.pathname + location.search);
      resolveScreen();
    },
  });
}

function resolveScreen() {
  const hash = location.hash.replace(/^#/, "");
  if (hash) {
    const specimen = findById(hash);
    if (specimen) {
      showAnnotation(specimen);
      return;
    }
    // Unknown id — clear hash and fall through to explorer.
    history.replaceState(null, "", location.pathname + location.search);
  }
  showExplorer();
}

window.addEventListener("hashchange", resolveScreen);

// Topnav: Explore clears hash; Annotate opens the first specimen if none active.
document.querySelector("#topnav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-screen]");
  if (!btn) return;
  const screen = btn.dataset.screen;
  if (screen === "explorer") {
    if (location.hash) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    resolveScreen();
  } else if (screen === "annotation") {
    const current = location.hash.replace(/^#/, "");
    if (!current && dataset?.specimens?.length) {
      location.hash = dataset.specimens[1]?.id || dataset.specimens[0].id;
    }
  }
});

(async () => {
  try {
    await loadDataset();
    resolveScreen();
  } catch (err) {
    root.innerHTML = `<div style="padding:48px;font-family:var(--serif);color:var(--oxblood)">Failed to load specimens: ${err.message}</div>`;
    console.error(err);
  }
})();
