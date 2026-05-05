// AI label reader panel for the transcription modal.
// Mounts inside the image-rail (see renderImageRail in annotation.js) when
// FEATURE_AI_LABEL is on. State is per-modal-session: history is cleared on
// modal close; persisted draft re-hydrates from specimen.ai_extraction.

const LS_KEY_BACKEND = "ai_label_backend";

function escapeHtml(s) {
  return String(s ?? "").replace(/[<>&"']/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// One-time health check at module load. Result cached on window so multiple
// modal opens reuse it without re-fetching.
let _healthPromise = null;
function getHealth() {
  if (_healthPromise) return _healthPromise;
  const root = document.getElementById("annotate-root");
  const apiBase = root?.dataset?.apiBase || "/api/v1/scribe";
  _healthPromise = fetch(`${apiBase}/ai/health`, { credentials: "same-origin" })
    .then((r) => r.ok ? r.json() : { feature: false, remote_available: false })
    .catch(() => ({ feature: false, remote_available: false }));
  return _healthPromise;
}

export function isAiFeatureEnabled() {
  const root = document.getElementById("annotate-root");
  return root?.dataset?.featureAiLabel === "1";
}

export function defaultBackend() {
  // localStorage > data attribute > "remote"
  try {
    const saved = localStorage.getItem(LS_KEY_BACKEND);
    if (saved === "api" || saved === "remote") return saved;
  } catch (_) { /* ignore */ }
  const root = document.getElementById("annotate-root");
  return root?.dataset?.aiDefaultBackend || "remote";
}

export function makeAiState(specimen) {
  const initial = specimen?.ai_extraction || null;
  return {
    backend: defaultBackend(),
    draftText: initial ? initial.text : "",
    initialMeta: initial,    // { text, model, backend, ms, created_at } | null
    history: [],             // { backend, model, ms, cached, at }[]
    inflight: false,
    error: null,
  };
}

export function renderAiPanel(specimen, aiState) {
  if (!isAiFeatureEnabled()) return "";

  const initial = aiState.initialMeta;
  const initialNote = initial
    ? `<div class="ai-initial-meta">${_("Loaded from")} ${escapeHtml(initial.backend)} · ${escapeHtml(initial.model)} · ${escapeHtml(initial.created_at || "")}</div>`
    : "";

  const historyHtml = aiState.history.length
    ? `<div class="ai-history">
        <div class="ai-history-title">${_("Recent attempts")}</div>
        ${aiState.history.map((h) => `
          <div class="ai-history-row ${h.cached ? "cached" : ""}">
            <span>${escapeHtml(h.backend)}</span>
            <span class="dot">·</span>
            <span>${escapeHtml(h.model)}</span>
            <span class="dot">·</span>
            <span>${h.cached ? _("cached") : `${h.ms}${_("ms")}`}</span>
          </div>
        `).join("")}
      </div>`
    : "";

  const errorHtml = aiState.error
    ? `<div class="ai-error-banner">${escapeHtml(aiState.error)}</div>`
    : "";

  const reReadHtml = aiState.draftText
    ? `<button type="button" class="ai-reread-btn" id="ai-reread-btn" ${aiState.inflight ? "disabled" : ""}>${_("Re-read")}</button>`
    : "";

  return `
    <div class="rail-section ai-panel">
      <div class="rail-section-title">${_("AI label reader")}</div>
      <div class="ai-controls">
        <label class="ai-backend-row">
          <span>${_("Backend")}:</span>
          <select class="ai-backend-select" id="ai-backend-select">
            <option value="api" ${aiState.backend === "api" ? "selected" : ""}>${_("Anthropic API")}</option>
            <option value="remote" ${aiState.backend === "remote" ? "selected" : ""} class="js-remote-option">${_("Remote (Claude session)")}</option>
          </select>
        </label>
        <button type="button" class="ai-read-btn" id="ai-read-btn" ${aiState.inflight ? "disabled" : ""}>
          ${aiState.inflight ? _("Reading…") : _("Read label")}
        </button>
        ${reReadHtml}
      </div>
      ${errorHtml}
      <div class="ai-draft-label">${_("AI draft — verify before using")}</div>
      <textarea class="ai-draft-textarea" id="ai-draft-textarea"
                placeholder="${escapeAttr(_("AI draft — verify before using"))}"
                rows="6">${escapeHtml(aiState.draftText)}</textarea>
      ${initialNote}
      ${historyHtml}
    </div>
  `;
}

async function callAi(specimen, aiState, { force }) {
  const root = document.getElementById("annotate-root");
  const apiBase = root.dataset.apiBase;
  const url = `${apiBase}/units/${specimen.id}/ai/label`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      backend: aiState.backend,
      image_size: "2048",
      force,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = data.error || `HTTP ${res.status}`;
    throw new Error(err);
  }
  return data;
}

export function attachAiPanelEvents(host, specimen, aiState, rerenderPanel) {
  if (!isAiFeatureEnabled()) return;

  // Apply health check: disable Remote option if worker unreachable
  getHealth().then((h) => {
    if (h && h.remote_available === false) {
      const opt = host.querySelector(".js-remote-option");
      if (opt) {
        opt.disabled = true;
        opt.textContent = `${_("Remote (Claude session)")} — ${_("Remote backend unavailable")}`;
      }
      // If user's saved pref was "remote" but it's down, fall back to API
      if (aiState.backend === "remote") {
        aiState.backend = "api";
        const sel = host.querySelector("#ai-backend-select");
        if (sel) sel.value = "api";
      }
    }
  });

  // Backend selector → state + localStorage
  host.querySelector("#ai-backend-select")?.addEventListener("change", (e) => {
    aiState.backend = e.target.value;
    try { localStorage.setItem(LS_KEY_BACKEND, aiState.backend); } catch (_) {}
  });

  // Textarea edit → state (does NOT touch the form panel)
  host.querySelector("#ai-draft-textarea")?.addEventListener("input", (e) => {
    aiState.draftText = e.target.value;
  });

  // Read label button
  const doRead = async (force) => {
    if (aiState.inflight) return;
    if (force && aiState.backend === "api" && aiState.draftText) {
      const ok = window.confirm(_("Re-reading on the API backend will incur a billable call. Continue?"));
      if (!ok) return;
    }
    aiState.inflight = true;
    aiState.error = null;
    rerenderPanel();
    try {
      const data = await callAi(specimen, aiState, { force });
      aiState.draftText = data.text || "";
      aiState.history.unshift({
        backend: data.backend,
        model: data.model,
        ms: data.ms,
        cached: !!data.cached,
        at: new Date().toISOString(),
      });
    } catch (e) {
      aiState.error = `${_("Failed to read label")}: ${e.message}`;
    } finally {
      aiState.inflight = false;
      rerenderPanel();
    }
  };

  host.querySelector("#ai-read-btn")?.addEventListener("click", () => doRead(false));
  host.querySelector("#ai-reread-btn")?.addEventListener("click", () => doRead(true));
}
