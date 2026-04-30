// Annotation view — image left, annotation panel right.

import { renderPlate } from "./plates.js";

const STATUS_LABEL = {
  verified: { label: "Verified", className: "verified" },
  "in-review": { label: "In review", className: "review" },
  "needs-help": { label: "Needs help", className: "help" },
};

const RECENT_ANNOTATORS = [
  { i: "EM", n: "Eliza Marsh", w: "2 hours ago", what: "transcribed label" },
  { i: "JT", n: "Joaquim Torres", w: "yesterday", what: "added trait: glabrous" },
  { i: "AK", n: "Anika Kaur", w: "3 days ago", what: "verified locality" },
];

const TRAITS = [
  { k: "Leaf shape", v: "obovate", s: "verified" },
  { k: "Margin", v: "lobed", s: "verified" },
  { k: "Color (dry)", v: "olive", s: "pending" },
  { k: "Petiole", v: "1.4 cm", s: "verified" },
  { k: "Texture", v: "glabrous", s: "pending" },
  { k: "Condition", v: "fair, foxing", s: "verified" },
];

function escapeHtml(s) {
  return String(s ?? "").replace(/[<>&"']/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

function renderCompletenessBar(value) {
  const segs = 5;
  const filled = Math.round((value / 100) * segs);
  let bars = "";
  for (let i = 0; i < segs; i++) bars += `<span class="seg ${i < filled ? "filled" : ""}"></span>`;
  return `<div class="completeness"><span class="completeness-label">${value}%</span><div class="completeness-bar">${bars}</div></div>`;
}

function renderStatusBadge(status) {
  const s = STATUS_LABEL[status];
  if (!s) return "";
  return `<span class="status-badge ${s.className}">${s.label}</span>`;
}

function renderFieldRow({ label, value, status, contributor, emptyText, customValueHtml }) {
  status = status || "empty";
  const valueHtml = customValueHtml
    ? customValueHtml
    : value
      ? `<span class="value-text">${escapeHtml(value)}</span>`
      : `<span class="value-empty">${escapeHtml(emptyText || "— not yet annotated —")}</span>`;
  const meta = contributor
    ? `<div class="field-meta">
        <span class="contributor-dot"></span>
        <span>${escapeHtml(contributor.name)}</span>
        <span class="dot">·</span>
        <span>${escapeHtml(contributor.when)}</span>
        ${status === "verified" ? `<span class="dot">·</span><span>verified by 3</span>` : ""}
      </div>`
    : "";
  const primaryAction = value ? "Suggest edit" : "Annotate";
  const flagBtn = value ? `<button class="ghost-btn alert" type="button">Flag</button>` : "";
  return `
    <div class="field-row status-${status}">
      <div class="field-label"><span class="field-marker"></span><span>${escapeHtml(label)}</span></div>
      <div class="field-value">${valueHtml}${meta}</div>
      <div class="field-actions">
        <button class="ghost-btn" type="button">${primaryAction}</button>
        ${flagBtn}
      </div>
    </div>
  `;
}

function renderSection({ title, count, hint, body }) {
  return `
    <section class="annot-section">
      <header class="annot-section-head">
        <h3>${escapeHtml(title)}</h3>
        ${count ? `<span class="annot-count">${escapeHtml(count)}</span>` : `<span class="annot-count"></span>`}
        <span class="annot-chev">−</span>
      </header>
      ${hint ? `<p class="section-hint">${escapeHtml(hint)}</p>` : ""}
      <div class="annot-section-body">${body}</div>
    </section>
  `;
}

function renderMiniMap() {
  return `
    <svg viewBox="0 0 280 140" class="minimap">
      <rect width="280" height="140" fill="#efe6d2" />
      <path d="M 0 80 Q 30 70 60 78 Q 90 90 120 82 Q 150 70 180 78 Q 220 90 280 80 L 280 140 L 0 140 Z" fill="#d8c89e" stroke="#5a4a36" stroke-width="0.6" />
      <path d="M 30 30 Q 60 20 90 28 Q 120 38 100 50 Q 70 55 40 48 Z" fill="#d8c89e" stroke="#5a4a36" stroke-width="0.4" />
      <g transform="translate(248, 22)">
        <circle r="14" fill="none" stroke="#5a4a36" stroke-width="0.4" />
        <polygon points="0,-12 3,0 0,12 -3,0" fill="#5a4a36" opacity="0.8" />
        <text y="-16" text-anchor="middle" font-size="6" font-family="'Cormorant Garamond', serif" fill="#231b12">N</text>
      </g>
      <g transform="translate(98, 76)">
        <circle r="8" fill="#7a2e1f" opacity="0.2" />
        <circle r="4" fill="#7a2e1f" stroke="#231b12" stroke-width="0.5" />
      </g>
      <text x="106" y="74" font-size="6" font-family="'Cormorant Garamond', serif" font-style="italic" fill="#231b12">Berkshire Co.</text>
      <line x1="0" y1="40" x2="280" y2="40" stroke="#5a4a36" stroke-width="0.2" stroke-dasharray="2 2" opacity="0.6" />
      <line x1="0" y1="100" x2="280" y2="100" stroke="#5a4a36" stroke-width="0.2" stroke-dasharray="2 2" opacity="0.6" />
      <line x1="93" y1="0" x2="93" y2="140" stroke="#5a4a36" stroke-width="0.2" stroke-dasharray="2 2" opacity="0.6" />
      <line x1="186" y1="0" x2="186" y2="140" stroke="#5a4a36" stroke-width="0.2" stroke-dasharray="2 2" opacity="0.6" />
    </svg>
  `;
}

function renderImageViewer(specimen, region, zoom) {
  const regionOverlay = region === "label"
    ? `<div class="region-overlay" style="left:59%;top:76%;width:36%;height:18%">
         <div class="region-frame"></div>
         <div class="region-tag">Selected: handwritten label</div>
       </div>`
    : "";
  return `
    <div class="image-viewer">
      <div class="viewer-tabs" id="viewer-tabs">
        <button type="button" data-region="full" class="${region === "full" ? "on" : ""}">Full plate</button>
        <button type="button" data-region="label" class="${region === "label" ? "on" : ""}">Herbarium label</button>
        <button type="button" data-region="specimen" class="${region === "specimen" ? "on" : ""}">Specimen</button>
        <button type="button" data-region="verso" class="${region === "verso" ? "on" : ""}">Verso</button>
      </div>
      <div class="viewer-stage">
        <div class="viewer-image" style="transform:scale(${zoom})">
          ${renderPlate(specimen)}
          ${regionOverlay}
        </div>
        <div class="viewer-corner">
          <div class="caption-cat">${escapeHtml(specimen.catalog)}</div>
          <div class="caption-tax">${escapeHtml(specimen.taxon)}</div>
        </div>
      </div>
      <div class="viewer-controls">
        <div class="zoom-group">
          <button type="button">−</button>
          <span class="zoom-label">${Math.round(zoom * 100)}%</span>
          <button type="button">+</button>
          <span class="ctl-sep"></span>
          <button type="button">Fit</button>
          <button type="button">1:1</button>
          <button type="button">↻</button>
        </div>
        <div class="ctl-right">
          <button type="button" class="ctl-btn">⤓ Download IIIF</button>
          <button type="button" class="ctl-btn">Compare with similar</button>
          <button type="button" class="ctl-btn">Open in lightbox</button>
        </div>
      </div>
    </div>
  `;
}

function renderImageRail(specimen) {
  const thumbs = [0, 1, 2].map((i) => `<div class="thumb ${i === 0 ? "on" : ""}">${renderPlate(specimen)}</div>`).join("");
  const annotators = RECENT_ANNOTATORS.map((a) => `
    <div class="annot-line">
      <div class="avatar">${escapeHtml(a.i)}</div>
      <div>
        <div class="annot-name">${escapeHtml(a.n)}</div>
        <div class="annot-what">${escapeHtml(a.what)}</div>
      </div>
      <div class="annot-when">${escapeHtml(a.w)}</div>
    </div>
  `).join("");
  return `
    <div class="image-rail">
      <div class="rail-section">
        <div class="rail-section-title">Specimen plate</div>
        <div class="thumb-row">${thumbs}</div>
      </div>
      <div class="rail-section">
        <div class="rail-section-title">Recent annotators</div>
        <div class="annot-stack">${annotators}</div>
      </div>
    </div>
  `;
}

function renderIdentificationSection(specimen) {
  const body = [
    renderFieldRow({ label: "Scientific name", value: specimen.taxon, status: "verified",
      contributor: { name: "Dr. F. Caldera", when: "2 yrs ago" } }),
    renderFieldRow({ label: "Common name", value: specimen.common, status: "pending",
      contributor: { name: "Eliza Marsh", when: "2 hrs ago" } }),
    renderFieldRow({ label: "Type specimen?", status: "empty" }),
  ].join("");
  return renderSection({ title: "Identification", count: "3 fields",
    hint: "Help confirm or refine the taxonomic identification.", body });
}

function renderDateSection(specimen) {
  const body = [
    renderFieldRow({ label: "Date collected", value: specimen.collected, status: "verified",
      contributor: { name: "Joaquim Torres", when: "1 yr ago" } }),
    renderFieldRow({ label: "Date accessioned", status: "empty" }),
  ].join("");
  return renderSection({ title: "Date", count: "2 fields", body });
}

function renderLocalitySection(specimen) {
  const coordsCustom = `<span class="value-empty">— click map to set —</span>`;
  const body = [
    renderFieldRow({ label: "Place name", value: specimen.locality, status: "pending",
      contributor: { name: "Anika Kaur", when: "3 days ago" } }),
    renderFieldRow({ label: "Coordinates", status: "empty", customValueHtml: coordsCustom }),
    `<div class="map-card">${renderMiniMap()}<div class="map-legend"><span>Inferred from "${escapeHtml((specimen.locality || "").split(",")[0])}". Click to refine.</span></div></div>`,
    renderFieldRow({ label: "Elevation (m)", status: "empty" }),
    renderFieldRow({ label: "Habitat", status: "empty" }),
  ].join("");
  return renderSection({ title: "Locality", count: "4 fields",
    hint: "Drop a pin on the map or paste coordinates.", body });
}

function renderHandwrittenSection() {
  const body = `
    <div class="transcribe-card">
      <div class="transcribe-source">
        <div class="source-tag">As written</div>
        <div class="source-text">
          <span class="hand">Quercus alba L.</span><br>
          <span class="hand small">Berkshire Co., Mass.</span><br>
          <span class="hand small">14 Sept. 1923</span><br>
          <span class="hand small">E.M. Holloway, № 412</span>
        </div>
      </div>
      <div class="transcribe-arrow">→</div>
      <div class="transcribe-target">
        <div class="source-tag">Transcribed</div>
        <textarea class="transcribe-input">Quercus alba L.
Berkshire Co., Mass.
14 Sept. 1923
E.M. Holloway, № 412</textarea>
        <div class="transcribe-actions">
          <button type="button" class="primary-btn">Save transcription</button>
          <span class="confidence">2 of 3 transcribers agree</span>
        </div>
      </div>
    </div>
  `;
  return renderSection({ title: "Handwritten label", count: "transcription", body });
}

function renderTraitsSection() {
  const chips = TRAITS.map((t) => `
    <div class="trait-chip status-${t.s}">
      <span class="trait-k">${escapeHtml(t.k)}</span>
      <span class="trait-v">${escapeHtml(t.v)}</span>
    </div>
  `).join("");
  const body = `<div class="trait-cluster">${chips}<button type="button" class="trait-add">+ add trait</button></div>`;
  return renderSection({ title: "Traits", count: "6 tagged", body });
}

function renderFlagsSection() {
  const body = `
    <div class="flag-card">
      <div class="flag-head">
        <span class="flag-tag">Possible misidentification</span>
        <span class="flag-when">flagged 4 days ago</span>
      </div>
      <div class="flag-body">
        <em>"Leaf lobing matches Quercus bicolor more than Q. alba — would welcome a curator's eye."</em>
      </div>
      <div class="flag-foot">
        <span class="contributor-dot"></span>
        <span>Anika Kaur</span>
        <span class="dot">·</span>
        <button type="button" class="ghost-btn">Reply (2)</button>
        <button type="button" class="ghost-btn">Resolve</button>
      </div>
    </div>
    <button type="button" class="raise-flag">⚑ Raise a new flag</button>
  `;
  return renderSection({ title: "Flags & corrections", count: "1 open", body });
}

function renderNotesSection() {
  const body = `
    <textarea class="notes-input" placeholder="Free-text observations: condition, prior misclassifications, references…"></textarea>
    <div class="notes-foot">
      <span class="tinytext">Markdown supported. Visible to all contributors.</span>
      <button type="button" class="primary-btn">Post note</button>
    </div>
  `;
  return renderSection({ title: "Notes", body });
}

export function renderAnnotation(root, specimen, callbacks) {
  const region = "full";
  const zoom = 1;

  root.innerHTML = `
    <div class="annot-view">
      <div class="annot-breadcrumb">
        <button class="link" id="back-to-explorer" type="button">← Back to explorer</button>
        <span class="crumb-sep">›</span>
        <span>${escapeHtml(specimen.kingdom)}</span>
        <span class="crumb-sep">›</span>
        <span>${escapeHtml(specimen.family)}</span>
        <span class="crumb-sep">›</span>
        <span class="crumb-current">${escapeHtml(specimen.catalog)}</span>
        <div class="crumb-spacer"></div>
        <button class="ctl-btn ghost" type="button">‹ Prev</button>
        <button class="ctl-btn ghost" type="button">Next ›</button>
      </div>

      <div class="annot-stage">
        <div class="annot-image-pane">
          <div id="image-viewer-mount">${renderImageViewer(specimen, region, zoom)}</div>
          ${renderImageRail(specimen)}
        </div>

        <aside class="annot-panel">
          <header class="panel-head">
            <div>
              <div class="panel-cat">${escapeHtml(specimen.catalog)}</div>
              <h1 class="panel-tax">${escapeHtml(specimen.taxon)}</h1>
              <div class="panel-common">${escapeHtml(specimen.common)}</div>
            </div>
            <div class="panel-meta">
              ${renderCompletenessBar(specimen.completeness)}
              ${renderStatusBadge(specimen.status)}
            </div>
          </header>

          <nav class="panel-tabs" id="panel-tabs">
            <button type="button" data-tab="annotate" class="on">Annotate <span class="tab-count">${specimen.pending}</span></button>
            <button type="button" data-tab="history">History <span class="tab-count">${specimen.annotations}</span></button>
            <button type="button" data-tab="discuss">Discuss <span class="tab-count">2</span></button>
          </nav>

          <div class="panel-scroll">
            ${renderIdentificationSection(specimen)}
            ${renderDateSection(specimen)}
            ${renderLocalitySection(specimen)}
            ${renderHandwrittenSection()}
            ${renderTraitsSection()}
            ${renderFlagsSection()}
            ${renderNotesSection()}
          </div>

          <footer class="panel-foot">
            <div class="foot-stat">
              <div class="foot-num">+12</div>
              <div class="foot-lbl">your contributions this week</div>
            </div>
            <button type="button" class="primary-btn big">Submit annotations</button>
          </footer>
        </aside>
      </div>
    </div>
  `;

  attachAnnotationEvents(root, specimen, callbacks);
}

function attachAnnotationEvents(root, specimen, callbacks) {
  // Back to explorer.
  root.querySelector("#back-to-explorer")?.addEventListener("click", () => {
    callbacks?.onBack?.();
  });

  // Section collapse.
  root.querySelector(".panel-scroll")?.addEventListener("click", (e) => {
    const head = e.target.closest(".annot-section-head");
    if (!head) return;
    const section = head.parentElement;
    const body = section.querySelector(".annot-section-body");
    const hint = section.querySelector(".section-hint");
    const chev = head.querySelector(".annot-chev");
    const collapsed = body.style.display === "none";
    body.style.display = collapsed ? "" : "none";
    if (hint) hint.style.display = collapsed ? "" : "none";
    if (chev) chev.textContent = collapsed ? "−" : "+";
  });

  // Viewer tabs (region selection).
  root.querySelector("#viewer-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-region]");
    if (!btn) return;
    const region = btn.dataset.region;
    const mount = root.querySelector("#image-viewer-mount");
    if (mount) mount.innerHTML = renderImageViewer(specimen, region, 1);
  });

  // Panel tabs (visual-only in v1).
  root.querySelector("#panel-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-tab]");
    if (!btn) return;
    root.querySelectorAll("#panel-tabs button").forEach((b) => b.classList.toggle("on", b === btn));
  });
}
