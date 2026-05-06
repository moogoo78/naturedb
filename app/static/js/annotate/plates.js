// Stylized "specimen plate" SVGs — placeholder imagery in scholarly archival style.
// Ported from nature-scribe/project/plates.jsx to vanilla JS.

const PAPER = "#efe6d2";
const PAPER_SHADE = "#e2d5b4";
const INK = "#231b12";
const INK_SOFT = "#5a4a36";

const safeId = (s) => String(s).replace(/[^a-zA-Z0-9]/g, "");

function plateFrame(catalog, label, inner) {
  const id = safeId(catalog);
  return `
    <svg viewBox="0 0 320 240" preserveAspectRatio="xMidYMid slice" style="width:100%;height:100%;display:block">
      <defs>
        <pattern id="grain-${id}" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
          <rect width="4" height="4" fill="${PAPER}" />
          <circle cx="1" cy="1" r="0.4" fill="${PAPER_SHADE}" opacity="0.5" />
          <circle cx="3" cy="2" r="0.3" fill="${PAPER_SHADE}" opacity="0.4" />
        </pattern>
      </defs>
      <rect width="320" height="240" fill="url(#grain-${id})" />
      <circle cx="42" cy="38" r="14" fill="#c8a878" opacity="0.18" />
      <circle cx="280" cy="200" r="22" fill="#c8a878" opacity="0.14" />
      <circle cx="260" cy="40" r="6" fill="#a08050" opacity="0.22" />
      ${inner}
      <g transform="translate(196, 188)">
        <rect width="108" height="40" fill="#fbf5e3" stroke="${INK}" stroke-width="0.6" />
        <line x1="6" y1="12" x2="102" y2="12" stroke="${INK_SOFT}" stroke-width="0.3" />
        <line x1="6" y1="20" x2="102" y2="20" stroke="${INK_SOFT}" stroke-width="0.3" />
        <line x1="6" y1="28" x2="80" y2="28" stroke="${INK_SOFT}" stroke-width="0.3" />
        <text x="6" y="9" font-family="'Cormorant Garamond', serif" font-size="6.5" fill="${INK}" font-style="italic">${escapeXml(label)}</text>
        <text x="6" y="36" font-family="'JetBrains Mono', monospace" font-size="4.5" fill="${INK_SOFT}">${escapeXml(catalog)}</text>
      </g>
    </svg>
  `;
}

function escapeXml(s) {
  return String(s).replace(/[<>&'"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", '"': "&quot;" }[c]));
}

function leafPlate(catalog, label, color) {
  const inner = `
    <path d="M 100 210 Q 130 130 170 70" stroke="${INK}" stroke-width="1.4" fill="none" />
    <path d="M 170 70 Q 220 60 240 110 Q 250 160 200 180 Q 140 190 110 150 Q 100 110 130 90 Q 150 78 170 70 Z"
          fill="${color}" opacity="0.78" stroke="${INK}" stroke-width="0.8" />
    <path d="M 170 70 Q 175 130 175 180" stroke="${INK}" stroke-width="0.5" fill="none" opacity="0.6" />
    <path d="M 175 95 Q 200 100 225 105" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
    <path d="M 175 115 Q 200 122 230 130" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
    <path d="M 175 135 Q 200 145 225 155" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
    <path d="M 175 155 Q 195 165 215 170" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
    <path d="M 173 100 Q 150 105 130 110" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
    <path d="M 173 125 Q 145 130 122 135" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
    <path d="M 173 150 Q 145 158 120 160" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
  `;
  return plateFrame(catalog, label, inner);
}

function butterflyPlate(catalog, label, color) {
  const inner = `
    <ellipse cx="160" cy="120" rx="4" ry="44" fill="${INK}" />
    <path d="M 160 78 Q 150 60 140 56" stroke="${INK}" stroke-width="0.8" fill="none" />
    <path d="M 160 78 Q 170 60 180 56" stroke="${INK}" stroke-width="0.8" fill="none" />
    <path d="M 160 90 Q 100 60 70 100 Q 60 130 110 130 Q 150 125 160 110 Z" fill="${color}" opacity="0.85" stroke="${INK}" stroke-width="0.7" />
    <path d="M 160 90 Q 220 60 250 100 Q 260 130 210 130 Q 170 125 160 110 Z" fill="${color}" opacity="0.85" stroke="${INK}" stroke-width="0.7" />
    <path d="M 160 120 Q 110 140 100 175 Q 130 165 160 150 Z" fill="${color}" opacity="0.7" stroke="${INK}" stroke-width="0.7" />
    <path d="M 160 120 Q 210 140 220 175 Q 190 165 160 150 Z" fill="${color}" opacity="0.7" stroke="${INK}" stroke-width="0.7" />
    <circle cx="100" cy="105" r="6" fill="${INK}" opacity="0.55" />
    <circle cx="220" cy="105" r="6" fill="${INK}" opacity="0.55" />
    <circle cx="120" cy="160" r="3" fill="#7a2e1f" opacity="0.6" />
    <circle cx="200" cy="160" r="3" fill="#7a2e1f" opacity="0.6" />
  `;
  return plateFrame(catalog, label, inner);
}

function mineralPlate(catalog, label, color) {
  const inner = `
    <g transform="translate(160, 130)">
      <polygon points="-90,40 -50,-20 0,-50 60,-40 90,30 50,55 -40,60" fill="#8a7a5a" stroke="${INK}" stroke-width="0.6" />
      <polygon points="-30,30 -10,-20 10,-30 30,-15 25,25 -15,40" fill="${color}" opacity="0.85" stroke="${INK}" stroke-width="0.5" />
      <polygon points="-10,-20 10,-30 0,10 -15,5" fill="${color}" opacity="0.6" />
      <polygon points="20,10 50,-15 60,15 35,30" fill="${color}" opacity="0.78" stroke="${INK}" stroke-width="0.5" />
      <polygon points="-50,5 -25,-10 -20,20 -45,28" fill="${color}" opacity="0.7" stroke="${INK}" stroke-width="0.5" />
      <line x1="-10" y1="-20" x2="0" y2="10" stroke="#fff" stroke-width="0.6" opacity="0.5" />
      <line x1="50" y1="-15" x2="35" y2="30" stroke="#fff" stroke-width="0.5" opacity="0.5" />
    </g>
  `;
  return plateFrame(catalog, label, inner);
}

function fernPlate(catalog, label, color) {
  let fronds = "";
  for (let i = 0; i < 8; i++) {
    const y = 200 - i * 20;
    const w = 70 - i * 6;
    fronds += `<path d="M 160 ${y} Q ${160 - w / 2} ${y - 10} ${160 - w} ${y - 4}" stroke="${color}" stroke-width="1" fill="none" opacity="0.85" />`;
    fronds += `<path d="M 160 ${y} Q ${160 + w / 2} ${y - 10} ${160 + w} ${y - 4}" stroke="${color}" stroke-width="1" fill="none" opacity="0.85" />`;
    for (let j = 0; j < 6; j++) {
      const lx = 160 - (j + 1) * (w / 7);
      const rx = 160 + (j + 1) * (w / 7);
      const cy = y - 7 + j * 0.5;
      fronds += `<ellipse cx="${lx}" cy="${cy}" rx="4" ry="2.5" fill="${color}" opacity="0.7" transform="rotate(${-30 + j * 4} ${lx} ${y - 7})" />`;
      fronds += `<ellipse cx="${rx}" cy="${cy}" rx="4" ry="2.5" fill="${color}" opacity="0.7" transform="rotate(${30 - j * 4} ${rx} ${y - 7})" />`;
    }
  }
  const inner = `
    <path d="M 160 215 Q 158 140 165 70" stroke="${INK}" stroke-width="1.2" fill="none" />
    ${fronds}
  `;
  return plateFrame(catalog, label, inner);
}

function toothPlate(catalog, label, color) {
  let serrations = "";
  for (let i = 0; i < 10; i++) {
    serrations += `<path d="M ${-42 + i * 1.5} ${-50 + i * 8} l -3 2 l 3 2" stroke="${INK}" stroke-width="0.4" fill="none" />`;
    serrations += `<path d="M ${42 - i * 1.5} ${-50 + i * 8} l 3 2 l -3 2" stroke="${INK}" stroke-width="0.4" fill="none" />`;
  }
  const inner = `
    <g transform="translate(160, 130)">
      <path d="M -40 -60 Q -50 30 0 70 Q 50 30 40 -60 Q 0 -50 -40 -60 Z" fill="${color}" stroke="${INK}" stroke-width="0.7" />
      <path d="M -40 -60 Q -38 -45 -25 -50" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
      <path d="M 40 -60 Q 38 -45 25 -50" stroke="${INK}" stroke-width="0.4" fill="none" opacity="0.5" />
      ${serrations}
    </g>
  `;
  return plateFrame(catalog, label, inner);
}

function flowerPlate(catalog, label, color) {
  let petals = "";
  for (const a of [0, 60, 120, 180, 240, 300]) {
    petals += `<ellipse cx="160" cy="100" rx="22" ry="14" fill="${color}" opacity="0.78" stroke="${INK}" stroke-width="0.4" transform="rotate(${a} 160 100) translate(0 -16)" />`;
  }
  const inner = `
    <path d="M 160 215 Q 158 160 162 110" stroke="#3d5a3a" stroke-width="1.4" fill="none" />
    <ellipse cx="140" cy="170" rx="14" ry="6" fill="#3d5a3a" opacity="0.8" transform="rotate(-30 140 170)" />
    <ellipse cx="180" cy="155" rx="14" ry="6" fill="#3d5a3a" opacity="0.8" transform="rotate(30 180 155)" />
    ${petals}
    <circle cx="160" cy="100" r="10" fill="#d9b04a" stroke="${INK}" stroke-width="0.5" />
  `;
  return plateFrame(catalog, label, inner);
}

function beetlePlate(catalog, label, color) {
  let legs = "";
  for (const s of [-1, 1]) {
    legs += `<g transform="scale(${s} 1)">
      <path d="M 40 -20 q 30 -10 40 -25" stroke="${INK}" stroke-width="1.1" fill="none" />
      <path d="M 45 0 q 35 0 50 -5" stroke="${INK}" stroke-width="1.1" fill="none" />
      <path d="M 40 25 q 30 15 40 40" stroke="${INK}" stroke-width="1.1" fill="none" />
    </g>`;
  }
  const inner = `
    <g transform="translate(160, 130)">
      <ellipse cx="0" cy="-50" rx="22" ry="16" fill="${color}" stroke="${INK}" stroke-width="0.7" />
      <ellipse cx="0" cy="0" rx="48" ry="58" fill="${color}" stroke="${INK}" stroke-width="0.7" />
      <line x1="0" y1="-35" x2="0" y2="55" stroke="${INK}" stroke-width="0.7" />
      ${legs}
      <path d="M -10 -62 q -15 -20 -25 -25" stroke="${INK}" stroke-width="0.8" fill="none" />
      <path d="M 10 -62 q 15 -20 25 -25" stroke="${INK}" stroke-width="0.8" fill="none" />
      <ellipse cx="-15" cy="-10" rx="6" ry="20" fill="#fff" opacity="0.18" />
    </g>
  `;
  return plateFrame(catalog, label, inner);
}

function beePlate(catalog, label, color) {
  const inner = `
    <g transform="translate(160, 130)">
      <ellipse cx="-20" cy="-40" rx="40" ry="22" fill="#fbf5e3" opacity="0.7" stroke="${INK}" stroke-width="0.5" transform="rotate(-20 -20 -40)" />
      <ellipse cx="20" cy="-40" rx="40" ry="22" fill="#fbf5e3" opacity="0.7" stroke="${INK}" stroke-width="0.5" transform="rotate(20 20 -40)" />
      <ellipse cx="0" cy="0" rx="32" ry="46" fill="${color}" stroke="${INK}" stroke-width="0.6" />
      <path d="M -28 -20 Q 0 -28 28 -20" stroke="#d9b04a" stroke-width="9" fill="none" />
      <path d="M -30 5 Q 0 0 30 5" stroke="#d9b04a" stroke-width="9" fill="none" />
      <path d="M -25 28 Q 0 35 25 28" stroke="#d9b04a" stroke-width="7" fill="none" />
      <circle cx="0" cy="-50" r="14" fill="${color}" stroke="${INK}" stroke-width="0.6" />
    </g>
  `;
  return plateFrame(catalog, label, inner);
}

const PLATE_BY_MEDIUM = {
  leaf: leafPlate,
  butterfly: butterflyPlate,
  mineral: mineralPlate,
  fern: fernPlate,
  tooth: toothPlate,
  flower: flowerPlate,
  beetle: beetlePlate,
  bee: beePlate,
};

export function renderPlate(specimen) {
  const fn = PLATE_BY_MEDIUM[specimen.medium] || leafPlate;
  const labelText = specimen.taxon.split(" ").slice(0, 2).join(" ");
  return fn(specimen.catalog, labelText, specimen.color);
}
