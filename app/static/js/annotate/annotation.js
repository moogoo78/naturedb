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

// Map button label (px tier) → S3 filename suffix.
const SIZE_TO_SUFFIX = { "1024": "m", "2048": "l", "4096": "o" };
const DEFAULT_SIZE = "1024";

function urlForSize(coverUrl, sizeLabel) {
  if (!coverUrl) return null;
  const suffix = SIZE_TO_SUFFIX[sizeLabel] || "m";
  return coverUrl.replace(/-[smlo]\.jpg$/i, `-${suffix}.jpg`);
}

function renderImageViewer(specimen) {
  const initialUrl = urlForSize(specimen.cover_url, DEFAULT_SIZE);
  const imgHtml = initialUrl
    ? `<img id="viewer-img" class="viewer-cover" src="${escapeAttr(initialUrl)}" alt="" referrerpolicy="no-referrer" draggable="false">`
    : renderPlate(specimen);
  const sizeButtons = ["1024", "2048", "4096"].map((px) => `
    <button type="button" data-size="${px}" class="${px === DEFAULT_SIZE ? "on" : ""}" ${specimen.cover_url ? "" : "disabled"} title="Load ${px}px image">${px}<span class="size-unit">px</span></button>
  `).join("");
  return `
    <div class="image-viewer">
      <div class="viewer-tabs" id="viewer-tabs">
        <span class="viewer-tabs-label" aria-hidden="true">Image resolution</span>
        <div class="size-group" role="group" aria-label="Image resolution">
          ${sizeButtons}
        </div>
      </div>
      <div class="viewer-stage" id="viewer-stage">
        <div class="viewer-image" id="viewer-image">
          ${imgHtml}
        </div>
        <div class="viewer-corner">
          <div class="caption-cat">${escapeHtml(specimen.catalog)}</div>
          <div class="caption-tax">${escapeHtml(specimen.taxon)}</div>
        </div>
      </div>
      <div class="viewer-controls">
        <div class="zoom-group">
          <button type="button" id="zoom-out">−</button>
          <span class="zoom-label" id="zoom-label">100%</span>
          <button type="button" id="zoom-in">+</button>
          <span class="ctl-sep"></span>
          <button type="button" id="zoom-reset">Fit</button>
        </div>
        <div class="ctl-right">
          <button type="button" class="ctl-btn">⤓ Download</button>
        </div>
      </div>
    </div>
  `;
}

function renderImageRail(specimen) {
  const thumbInner = specimen.cover_url
    ? `<img class="thumb-cover" src="${escapeAttr(specimen.cover_url)}" alt="" referrerpolicy="no-referrer">`
    : renderPlate(specimen);
  const thumbs = [0, 1, 2].map((i) => `<div class="thumb ${i === 0 ? "on" : ""}">${thumbInner}</div>`).join("");
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

function renderSubgroup(title, rowsHtml) {
  return `
    <div class="annot-subgroup">
      <div class="annot-subgroup-title">${escapeHtml(title)}</div>
      ${rowsHtml}
    </div>
  `;
}

let collectorCache = null;
let countryCache = null;

async function loadCollectors() {
  if (collectorCache) return collectorCache;
  const url = new URL("/api/v1/people", location.origin);
  url.searchParams.set("filter", JSON.stringify({ is_collector: 1 }));
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    if (res.ok) {
      const data = await res.json();
      collectorCache = (data.items || []).map(p => ({
        id: p.id,
        name: p.display_name || p.full_name || p.full_name_en || `Person ${p.id}`,
      }));
    }
  } catch (e) {
    console.error("Failed to load collectors:", e);
  }
  return collectorCache || [];
}

// Named-area area_class_ids: 7=country, 8=adm1, 9=adm2, 10=adm3
const AREA_CLASS = { country: 7, adm1: 8, adm2: 9, adm3: 10 };

function shapeArea(a) {
  return { id: a.id, name: a.display_name || a.name_en || a.name || `Area ${a.id}` };
}

async function loadCountries() {
  if (countryCache) return countryCache;
  const url = new URL("/api/v1/named-areas", location.origin);
  url.searchParams.set("filter", JSON.stringify({ area_class_id: AREA_CLASS.country }));
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    if (res.ok) {
      const data = await res.json();
      countryCache = (data.data || []).map(shapeArea);
    }
  } catch (e) {
    console.error("Failed to load countries:", e);
  }
  return countryCache || [];
}

async function loadAreaChildren(parentId, areaClassId) {
  const url = new URL("/api/v1/named-areas", location.origin);
  url.searchParams.set("filter", JSON.stringify({ area_class_id: areaClassId, parent_id: parentId }));
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    if (res.ok) {
      const data = await res.json();
      return (data.data || []).map(shapeArea);
    }
  } catch (e) {
    console.error("Failed to load area children:", e);
  }
  return [];
}

function renderCollectorRow(specimen, collectors) {
  const value = specimen.collector_name;
  const collectorId = specimen.collector_id;
  const options = (collectors || []).map((c) =>
    `<option value="${escapeAttr(c.id)}" ${collectorId === c.id ? "selected" : ""}>${escapeHtml(c.name)}</option>`
  ).join("");
  const valueHtml = value
    ? `<span class="value-text">${escapeHtml(value)}</span>`
    : `<select class="field-select collector-select" aria-label="Collector">
        <option value="">— select person —</option>
        ${options}
      </select>`;
  return renderFieldRow({
    label: "Collector",
    value,
    status: value ? "verified" : "empty",
    customValueHtml: valueHtml,
  });
}

function renderYmdRow(specimen) {
  const y = specimen.collect_date_year ?? "";
  const m = specimen.collect_date_month ?? "";
  const d = specimen.collect_date_day ?? "";
  const allValid = y && m && d;
  const status = allValid ? "verified" : (y || m || d ? "pending" : "empty");
  const mapped = specimen.collect_date
    ? `<div class="field-meta"><span class="dot">↳</span><span>maps to <code>${escapeHtml(specimen.collect_date)}</code></span></div>`
    : (allValid ? `` : `<div class="field-meta tinytext">All three fields required to map to <code>collect_date</code>.</div>`);
  const monthOptions = ["", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((opt) => {
    const v = String(opt);
    const sel = String(m) === v ? " selected" : "";
    const label = opt === "" ? "MM" : v;
    return `<option value="${escapeAttr(v)}"${sel}>${escapeHtml(label)}</option>`;
  }).join("");
  const customValueHtml = `
    <div class="ymd-inputs">
      <input type="text" inputmode="numeric" placeholder="YYYY" value="${escapeAttr(y)}" class="ymd-y" aria-label="Year">
      <span class="ymd-sep">-</span>
      <select class="ymd-m" aria-label="Month">${monthOptions}</select>
      <span class="ymd-sep">-</span>
      <input type="text" inputmode="numeric" placeholder="DD" value="${escapeAttr(d)}" class="ymd-d" aria-label="Day">
    </div>
    ${mapped}
  `;
  return renderFieldRow({
    label: "Collect date",
    value: allValid ? `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}` : "",
    status,
    customValueHtml,
  });
}

function renderEventSection(specimen, collectors) {
  const personRows = [
    renderCollectorRow(specimen, collectors),
    renderFieldRow({ label: "Verbatim collector", value: specimen.verbatim_collector,
      status: specimen.verbatim_collector ? "pending" : "empty" }),
    renderFieldRow({ label: "Companion text", value: specimen.companion_text,
      status: specimen.companion_text ? "pending" : "empty" }),
  ].join("");

  const dateRows = [
    renderFieldRow({ label: "Verbatim collect date", value: specimen.verbatim_collect_date,
      status: specimen.verbatim_collect_date ? "pending" : "empty" }),
    renderYmdRow(specimen),
  ].join("");

  const body = [
    renderSubgroup("Person", personRows),
    renderFieldRow({ label: "Field number", value: specimen.field_number,
      status: specimen.field_number ? "verified" : "empty" }),
    renderSubgroup("Date", dateRows),
  ].join("");

  return renderSection({ title: "Event", count: "6 fields",
    hint: "Who collected the specimen, when, and any field notes.", body });
}

function renderIdentificationSection(specimen) {
  const body = [
    renderFieldRow({ label: "Scientific name", value: specimen.taxon,
      status: specimen.taxon ? "verified" : "empty" }),
    renderFieldRow({ label: "Verbatim identification", value: specimen.verbatim_identification,
      status: specimen.verbatim_identification ? "pending" : "empty" }),
  ].join("");
  return renderSection({ title: "Identification", count: "2 fields",
    hint: "Help confirm or refine the taxonomic identification.", body });
}

// DMS ↔ decimal degree conversion (used by coord auto-convert).
function decimalToDMS(decimal, dirPos, dirNeg) {
  const v = parseFloat(decimal);
  if (decimal === "" || decimal == null || isNaN(v)) return { d: "", m: "", s: "", dir: "" };
  const abs = Math.abs(v);
  const d = Math.floor(abs);
  const mFloat = (abs - d) * 60;
  const m = Math.floor(mFloat);
  const s = ((mFloat - m) * 60).toFixed(2);
  const dir = v >= 0 ? dirPos : dirNeg;
  return { d, m, s, dir };
}

function dmsToDecimal(d, m, s, dir) {
  const D = parseFloat(d) || 0;
  const M = parseFloat(m) || 0;
  const S = parseFloat(s) || 0;
  if (D === 0 && M === 0 && S === 0) return "";
  let dec = D + M / 60 + S / 3600;
  if (dir === "S" || dir === "W") dec = -dec;
  return dec.toFixed(6);
}

function renderCoordRow(specimen, axis) {
  const decimal = specimen[`${axis}_decimal`] ?? "";
  const verbatim = specimen[`verbatim_${axis}`] ?? "";
  const dirs = axis === "longitude" ? ["E", "W"] : ["N", "S"];
  const maxDeg = axis === "longitude" ? 180 : 90;
  const dms = decimalToDMS(decimal, dirs[0], dirs[1]);
  const customValueHtml = `
    <div class="coord-inputs">
      <input type="text" inputmode="decimal" class="coord-decimal" data-axis="${axis}" placeholder="decimal" value="${escapeAttr(decimal)}">
    </div>
    <div class="coord-inputs coord-dms">
      <input type="number" class="coord-d" data-axis="${axis}" placeholder="°" min="0" max="${maxDeg}" value="${escapeAttr(dms.d)}">
      <span class="coord-sep">°</span>
      <input type="number" class="coord-m" data-axis="${axis}" placeholder="'" min="0" max="59" value="${escapeAttr(dms.m)}">
      <span class="coord-sep">'</span>
      <input type="number" class="coord-s" data-axis="${axis}" step="0.01" placeholder='"' min="0" max="59.99" value="${escapeAttr(dms.s)}">
      <span class="coord-sep">"</span>
      <select class="coord-dir" data-axis="${axis}">
        <option value="">-</option>
        <option value="${dirs[0]}" ${dms.dir === dirs[0] ? "selected" : ""}>${dirs[0]}</option>
        <option value="${dirs[1]}" ${dms.dir === dirs[1] ? "selected" : ""}>${dirs[1]}</option>
      </select>
    </div>
    ${verbatim ? `<div class="field-meta tinytext">verbatim: ${escapeHtml(verbatim)}</div>` : ""}
  `;
  return renderFieldRow({
    label: axis === "longitude" ? "Longitude" : "Latitude",
    value: decimal,
    status: decimal ? "verified" : "empty",
    customValueHtml,
  });
}

function renderNamedAreaSelect(label, value, axisKey, options, placeholder) {
  const opts = (options || []).map((a) =>
    `<option value="${escapeAttr(a.id)}">${escapeHtml(a.name)}</option>`
  ).join("");
  const ph = placeholder || "— select —";
  const customValueHtml = `<select class="field-select named-area-select" data-area="${escapeAttr(axisKey)}" aria-label="${escapeAttr(label)}">
      <option value="">${escapeHtml(ph)}</option>
      ${opts}
    </select>`;
  return renderFieldRow({
    label,
    value,
    status: value ? "verified" : "empty",
    customValueHtml,
  });
}

function renderAltitudeRow(specimen) {
  const a1 = specimen.altitude ?? "";
  const a2 = specimen.altitude2 ?? "";
  const customValueHtml = `
    <div class="alt-inputs">
      <input type="number" class="alt-1" placeholder="from" value="${escapeAttr(a1)}">
      <span class="alt-sep">—</span>
      <input type="number" class="alt-2" placeholder="to" value="${escapeAttr(a2)}">
      <span class="alt-unit">m</span>
    </div>
  `;
  const display = a1 ? (a2 ? `${a1} — ${a2} m` : `${a1} m`) : "";
  return renderFieldRow({
    label: "Altitude",
    value: display,
    status: a1 ? "verified" : "empty",
    customValueHtml,
  });
}

function renderLocalitySection(specimen, countries) {
  const placeRows = [
    renderFieldRow({ label: "Locality text", value: specimen.locality_text,
      status: specimen.locality_text ? "verified" : "empty" }),
    renderFieldRow({ label: "Verbatim locality", value: specimen.verbatim_locality,
      status: specimen.verbatim_locality ? "pending" : "empty" }),
  ].join("");

  const coordRows = [
    renderCoordRow(specimen, "longitude"),
    renderCoordRow(specimen, "latitude"),
  ].join("");

  const adminRows = [
    renderNamedAreaSelect("Country", specimen.country, "country", countries, "— select country —"),
    renderNamedAreaSelect("Admin area 1", specimen.adm1, "adm1", [], "— select country first —"),
    renderNamedAreaSelect("Admin area 2", specimen.adm2, "adm2", [], "— select adm1 first —"),
    renderNamedAreaSelect("Admin area 3", specimen.adm3, "adm3", [], "— select adm2 first —"),
  ].join("");

  const body = [
    placeRows,
    renderSubgroup("Coordinates", coordRows),
    renderSubgroup("Administrative area", adminRows),
    renderAltitudeRow(specimen),
  ].join("");

  return renderSection({ title: "Locality", count: "9 fields",
    hint: "Where the specimen was collected. Decimal and DMS auto-convert.", body });
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

const MODAL_HOST_ID = "annot-modal-host";
let keyListener = null;
let panMoveListener = null;
let panUpListener = null;
let modalState = null;  // { host, specimen, callbacks, navContext, collectors }

function renderAnnotationBody(specimen, navContext, collectors, countries) {
  const hasPrev = !!(navContext && navContext.index > 0);
  const hasNext = !!(navContext && navContext.index < (navContext.specimens.length - 1));
  const navMeta = navContext
    ? `<span class="crumb-nav-meta">${navContext.index + 1} / ${navContext.specimens.length}</span>`
    : "";
  return `
    <div class="annot-view annot-view-modal">
      <div class="annot-breadcrumb">
        <button class="link" id="back-to-explorer" type="button">← Back to explorer</button>
        <span class="crumb-sep">›</span>
        <span>${escapeHtml(specimen.kingdom)}</span>
        <span class="crumb-sep">›</span>
        <span>${escapeHtml(specimen.family)}</span>
        <span class="crumb-sep">›</span>
        <span class="crumb-current">${escapeHtml(specimen.catalog)}</span>
        <div class="crumb-spacer"></div>
        ${navMeta}
        <button class="ctl-btn ghost" type="button" id="nav-prev" ${hasPrev ? "" : "disabled"} title="Previous specimen (←)">‹ Prev</button>
        <button class="ctl-btn ghost" type="button" id="nav-next" ${hasNext ? "" : "disabled"} title="Next specimen (→)">Next ›</button>
      </div>

      <div class="annot-stage">
        <div class="annot-image-pane">
          ${renderImageViewer(specimen)}
          ${renderImageRail(specimen)}
        </div>

        <aside class="annot-panel">
          <header class="panel-head">
            <div>
              <div class="panel-cat-label">Catalog Number</div>
              <h1 class="panel-tax">${specimen.collection_label ? `<span class="panel-tax-marker">${escapeHtml(specimen.collection_label.split(":")[0])}</span>` : ""}${escapeHtml(specimen.catalog || "—")}</h1>
              <div class="panel-uid">id · ${escapeHtml(specimen.id)}</div>
              <div class="panel-common"><em>${escapeHtml(specimen.taxon)}</em>${specimen.common ? ` · ${escapeHtml(specimen.common)}` : ""}</div>
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
            ${renderEventSection(specimen, collectors)}
            ${renderIdentificationSection(specimen)}
            ${renderLocalitySection(specimen, countries)}
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
}

export async function openAnnotationModal(specimen, callbacks, navContext) {
  closeAnnotationModal();  // ensure no stale instance

  const host = document.createElement("div");
  host.id = MODAL_HOST_ID;
  host.className = "annot-modal-backdrop";
  host.innerHTML = `
    <div class="annot-modal" role="dialog" aria-modal="true" aria-label="Specimen annotation">
      <button type="button" class="annot-modal-close" id="annot-modal-close" aria-label="Close">×</button>
      <div class="annot-modal-body"></div>
    </div>
  `;
  document.body.appendChild(host);
  document.body.classList.add("annot-modal-open");

  const [collectors, countries] = await Promise.all([loadCollectors(), loadCountries()]);
  modalState = { host, specimen, callbacks, navContext, collectors, countries };
  attachOuterEvents();
  renderModalContent();
}

export function closeAnnotationModal(callbacks) {
  const host = document.getElementById(MODAL_HOST_ID);
  if (host) host.remove();
  document.body.classList.remove("annot-modal-open");
  if (keyListener) {
    document.removeEventListener("keydown", keyListener);
    keyListener = null;
  }
  if (panMoveListener) {
    document.removeEventListener("mousemove", panMoveListener);
    panMoveListener = null;
  }
  if (panUpListener) {
    document.removeEventListener("mouseup", panUpListener);
    panUpListener = null;
  }
  const cb = callbacks || modalState?.callbacks;
  modalState = null;
  cb?.onClose?.();
}

function navigateTo(delta) {
  if (!modalState?.navContext) return;
  const { specimens, index } = modalState.navContext;
  const next = index + delta;
  if (next < 0 || next >= specimens.length) return;
  modalState.specimen = specimens[next];
  modalState.navContext = { specimens, index: next };
  renderModalContent();
}

function isFormFocused(target) {
  const tag = (target?.tagName || "").toUpperCase();
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target?.isContentEditable === true;
}

function attachOuterEvents() {
  const { host, callbacks } = modalState;
  const close = () => closeAnnotationModal(callbacks);

  // Close button.
  host.querySelector("#annot-modal-close")?.addEventListener("click", close);

  // Backdrop click (but not clicks inside the modal panel).
  host.addEventListener("click", (e) => {
    if (e.target === host) close();
  });

  // Keyboard: ESC to close, Arrow Left/Right to navigate (skip when typing in a form input).
  keyListener = (e) => {
    if (e.key === "Escape") return close();
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    if (isFormFocused(e.target)) return;
    e.preventDefault();
    navigateTo(e.key === "ArrowLeft" ? -1 : 1);
  };
  document.addEventListener("keydown", keyListener);
}

function renderModalContent() {
  const { host, specimen, callbacks, navContext, collectors, countries } = modalState;

  // Tear down stale pan listeners before re-binding (image element is replaced).
  if (panMoveListener) document.removeEventListener("mousemove", panMoveListener);
  if (panUpListener) document.removeEventListener("mouseup", panUpListener);

  const body = host.querySelector(".annot-modal-body");
  body.innerHTML = renderAnnotationBody(specimen, navContext, collectors, countries);

  // Reset modal scroll on navigation.
  host.scrollTop = 0;

  attachInnerEvents(host, specimen, callbacks);
}

function attachInnerEvents(host, specimen, callbacks) {
  const close = () => closeAnnotationModal(callbacks);

  // Back-to-explorer link in breadcrumb closes the modal.
  host.querySelector("#back-to-explorer")?.addEventListener("click", close);

  // Breadcrumb prev/next.
  host.querySelector("#nav-prev")?.addEventListener("click", () => navigateTo(-1));
  host.querySelector("#nav-next")?.addEventListener("click", () => navigateTo(1));

  // Section collapse.
  host.querySelector(".panel-scroll")?.addEventListener("click", (e) => {
    const head = e.target.closest(".annot-section-head");
    if (!head) return;
    const section = head.parentElement;
    const sectionBody = section.querySelector(".annot-section-body");
    const hint = section.querySelector(".section-hint");
    const chev = head.querySelector(".annot-chev");
    const collapsed = sectionBody.style.display === "none";
    sectionBody.style.display = collapsed ? "" : "none";
    if (hint) hint.style.display = collapsed ? "" : "none";
    if (chev) chev.textContent = collapsed ? "−" : "+";
  });

  // Coordinate auto-convert: decimal ↔ DMS for both axes.
  const dirsFor = (axis) => axis === "longitude" ? ["E", "W"] : ["N", "S"];
  host.querySelectorAll(".coord-decimal").forEach((input) => {
    input.addEventListener("input", (e) => {
      const axis = e.target.dataset.axis;
      const [pos, neg] = dirsFor(axis);
      const dms = decimalToDMS(e.target.value, pos, neg);
      const q = (sel) => host.querySelector(`${sel}[data-axis="${axis}"]`);
      if (q(".coord-d")) q(".coord-d").value = dms.d;
      if (q(".coord-m")) q(".coord-m").value = dms.m;
      if (q(".coord-s")) q(".coord-s").value = dms.s;
      if (q(".coord-dir")) q(".coord-dir").value = dms.dir;
    });
  });
  host.querySelectorAll(".coord-d, .coord-m, .coord-s, .coord-dir").forEach((input) => {
    input.addEventListener("input", (e) => {
      const axis = e.target.dataset.axis;
      const q = (sel) => host.querySelector(`${sel}[data-axis="${axis}"]`);
      const dec = dmsToDecimal(q(".coord-d").value, q(".coord-m").value, q(".coord-s").value, q(".coord-dir").value);
      if (q(".coord-decimal")) q(".coord-decimal").value = dec;
    });
  });

  // Cascading named-area dropdowns (country → adm1 → adm2 → adm3).
  const setSelectOptions = (sel, items, placeholder) => {
    if (!sel) return;
    sel.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>` +
      items.map((i) => `<option value="${escapeAttr(i.id)}">${escapeHtml(i.name)}</option>`).join("");
  };
  const areaSel = (key) => host.querySelector(`[data-area="${key}"]`);
  const cascadeFrom = async (parentKey, parentValue) => {
    const map = {
      country: { child: "adm1", classId: AREA_CLASS.adm1, downstream: ["adm2", "adm3"] },
      adm1: { child: "adm2", classId: AREA_CLASS.adm2, downstream: ["adm3"] },
      adm2: { child: "adm3", classId: AREA_CLASS.adm3, downstream: [] },
    };
    const cfg = map[parentKey];
    if (!cfg) return;
    const childSel = areaSel(cfg.child);
    if (!parentValue) {
      setSelectOptions(childSel, [], `— select ${parentKey} first —`);
    } else {
      const items = await loadAreaChildren(parentValue, cfg.classId);
      setSelectOptions(childSel, items, "— select —");
    }
    cfg.downstream.forEach((k, idx) => {
      const placeholder = idx === 0 ? `— select ${cfg.child} first —` : "—";
      setSelectOptions(areaSel(k), [], placeholder);
    });
  };
  ["country", "adm1", "adm2"].forEach((key) => {
    areaSel(key)?.addEventListener("change", (e) => cascadeFrom(key, e.target.value));
  });

  // === Image viewer: resolution buttons + wheel zoom + drag pan ===
  const stage = host.querySelector("#viewer-stage");
  const imageEl = host.querySelector("#viewer-image");
  const imgEl = host.querySelector("#viewer-img");
  const labelEl = host.querySelector("#zoom-label");

  let scale = 1, tx = 0, ty = 0;
  let panning = false, sx = 0, sy = 0;

  const applyTransform = () => {
    if (!imageEl) return;
    imageEl.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    if (labelEl) labelEl.textContent = `${Math.round(scale * 100)}%`;
  };
  const reset = () => { scale = 1; tx = 0; ty = 0; applyTransform(); };
  const setZoom = (target) => {
    scale = Math.min(Math.max(0.5, target), 5);
    applyTransform();
  };

  stage?.addEventListener("wheel", (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(scale + delta);
  }, { passive: false });

  stage?.addEventListener("mousedown", (e) => {
    if (!imgEl) return;
    e.preventDefault();
    panning = true;
    sx = e.clientX - tx;
    sy = e.clientY - ty;
    stage.classList.add("grabbing");
  });
  panMoveListener = (e) => {
    if (!panning) return;
    tx = e.clientX - sx;
    ty = e.clientY - sy;
    applyTransform();
  };
  panUpListener = () => {
    if (!panning) return;
    panning = false;
    stage?.classList.remove("grabbing");
  };
  document.addEventListener("mousemove", panMoveListener);
  document.addEventListener("mouseup", panUpListener);

  host.querySelector("#zoom-in")?.addEventListener("click", () => setZoom(scale + 0.2));
  host.querySelector("#zoom-out")?.addEventListener("click", () => setZoom(scale - 0.2));
  host.querySelector("#zoom-reset")?.addEventListener("click", reset);

  // Resolution selector — swap the <img> src in place; zoom/pan state preserved.
  host.querySelector("#viewer-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-size]");
    if (!btn || !imgEl) return;
    const size = btn.dataset.size;
    const url = urlForSize(specimen.cover_url, size);
    if (url) imgEl.src = url;
    host.querySelectorAll("#viewer-tabs button").forEach((b) => b.classList.toggle("on", b === btn));
  });

  // Panel tabs (visual-only in v1).
  host.querySelector("#panel-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-tab]");
    if (!btn) return;
    host.querySelectorAll("#panel-tabs button").forEach((b) => b.classList.toggle("on", b === btn));
  });
}
