# Plan: Merge Habitat/Environment Tab with Geological Context

## Current State

### Admin Record Form Tab Structure (`app/templates/admin/record-form.html`)

- **"出現紀錄" (Occurrence) tab** -- contains geological context as a collapsible toggle section (`#toggle-geological-context`) buried at the bottom of location fields (around line 146-170)
- **"棲地/環境" (Habitat/Environment) tab** (`data-tab="assertion"`) -- contains only record assertions (dynamic key-value fields from `AssertionType`)
- These are two separate tabs but both describe environmental/contextual conditions of the specimen

### Key Code References
- Tab navigation: `record-form.html:46-57`
- Geological context toggle inside Occurrence tab: `record-form.html:146-170`
- Assertion tab content: `record-form.html:197-205`

## Problem

Geological context and habitat/environment assertions are conceptually related -- both describe "where and under what conditions was this specimen found?" -- but they're split across two different tabs. The geological context is hidden behind a collapsible toggle inside the Occurrence tab, making it hard to discover.

## Research: How Other Systems Handle This

### Arctos

Arctos **separates habitat and geology into different layers of the data hierarchy**, not different UI tabs:

- **Geological Context = Locality Attributes** (attached to the **Locality**, the place)
  - **Chronostratigraphy** (hierarchical): Eon > Era > Period > Epoch > Age > Subage
  - **Lithostratigraphy** (hierarchical): Group > Formation > Member > Bed
  - **Biostratigraphy**: biostratigraphic zone (controlled vocabulary)
  - **Biochronology**: biochron (Land Mammal Ages, etc.)
  - **Informal** variants for regional/non-standard terms
  - Each attribute carries a **determiner**, **date**, **method**, and **remarks** -- treating geology as a determination, same as taxonomy

- **Habitat = Collecting Event / Specimen-Event** (attached to the **Event**, the act of collecting)
  - Describes conditions at the time of collection (e.g., "limestone outcrop", "spruce bark microhabitat")
  - Specimen-specific habitat in the **Habitat field**; shared event-level data in **Event Attributes**

- **Key distinction**: Geology = property of the **place** (doesn't change between visits); Habitat = property of the **event** (can change over time at the same place)

Sources:
- [Locality Attributes - Arctos Handbook](https://handbook.arctosdb.org/documentation/localityattributes.html)
- [Record Event - Arctos Handbook](https://handbook.arctosdb.org/documentation/specimen-event.html)
- [Collecting Event - Arctos Handbook](https://handbook.arctosdb.org/documentation/collecting-event.html)

### Symbiota

Symbiota keeps habitat and geology as **separate sections within the same occurrence editor**, aligned with Darwin Core field groupings:

- **Habitat/Substrate** (on the main occurrence form)
  - **Habitat** -- free text: "Wet areas along a small stream in chaparral"
  - **Substrate** -- free text: mostly for lichen/bryophyte specimens

- **Paleontology Fields** (separate section, only visible for paleo-enabled collections)
  - **Chronostratigraphy**: Eon > Era > Period > Epoch > Stage > Local Stage
  - **Intervals**: Early Interval, Late Interval (mapped to ICS Time Scale)
  - **Lithostratigraphy**: Group > Formation > Member > Bed
  - **Biostratigraphy**: Biozone
  - **Other**: Taxon Environment (marine, lacustrine, etc.), Lithology, Absolute Age, Storage Age, Element, Slide Properties
  - **Remarks**: `stratigraphicRemarks` for non-standard values ("Tertiary", "Upper Mio?")

- **Key distinction**: Both live on the same record (occurrence level), but paleo fields only appear for collections that enable them. Separation is visual/organizational, not structural.

Sources:
- [Symbiota Occurrence Data Fields](https://symbiota.org/symbiota-occurrence-data-fields-2/)
- [Paleo Fields - Pteridophyte Collections Consortium](https://pteridophytes.berkeley.edu/paleo-fields/)
- [Manage fossil specimens using Symbiota](https://paleo-data.github.io/how-to-guides/manage-data-about-specimens-using-symbiota)

### Comparison

| | Arctos | Symbiota | NatureDB (current) |
|---|---|---|---|
| **Geology lives on** | Locality (shared across specimens) | Occurrence (per specimen) | Record (per specimen) |
| **Habitat lives on** | Collecting Event | Occurrence (same level as geology) | Record assertions |
| **Separation** | Different data layers | Different form sections, same record | Different tabs |
| **Geology visibility** | Always available via Locality Attributes | Only on paleo-enabled collections | Collapsible toggle in Occurrence tab |

**NatureDB is closest to Symbiota's approach** -- both store geological context per-record, not per-locality. Symbiota validates the merge plan: habitat and geological context coexist on the same record but in visually distinct sections, with paleo fields conditional on collection type.

## Proposed Change

Merge geological context fields and habitat assertions into a single tab with a more abstract category name.

### Tab Name Options

| Name | Pros | Cons |
|------|------|------|
| **「採集環境」** (Collection Environment) | Intuitive for curators, works for both fossil and non-fossil collections | Slightly broad |
| **「環境脈絡」** (Environmental Context) | Maps to DwC "Event" context, formally correct | "脈絡" may feel overly technical |
| **「棲地與地質」** (Habitat & Geology) | Explicit, no ambiguity | Longer, doesn't generalize well for non-fossil collections |

**Recommendation:** Use **「採集環境」** (Collection Environment) -- intuitive, works whether the collection has geological context or not.

### Implementation Steps

1. **Remove geological context toggle from Occurrence tab**
   - Remove the collapsible `#toggle-geological-context` section from inside the Occurrence tab (lines ~146-170)

2. **Rename the assertion tab**
   - Change tab nav label from `棲地/環境` to `採集環境`
   - Update `data-tab` attribute from `assertion` to something like `environment` (optional, cosmetic)

3. **Add geological context fields to the merged tab**
   - Inside the renamed tab, add two visual sections using fieldset legends:
     - **Section 1:** `棲地/環境` (Habitat assertions) -- existing dynamic assertion fields
     - **Section 2:** `地質脈絡` (Geological Context) -- moved geological context fields (geochronologic, biostratigraphic, lithostratigraphic, formation, member, bed)
   - The geological context section should only render when the collection has geological context enabled (fossil collections)

4. **Update JavaScript**
   - The toggle button JS for `#toggle-geological-context-btn` can be removed since the section will be directly visible in its own tab
   - Assertion loading JS may need tab ID updates if `data-tab` changes

### Trade-offs

- **Breaking spatial grouping:** Geological context is currently next to location fields in the Occurrence tab. Moving it breaks that physical proximity, but the conceptual grouping in a dedicated tab is arguably better for discoverability.
- **Mixed field types:** Assertions are collection-specific and dynamic, while geological context has a fixed schema. Use separate fieldset legends to visually distinguish them.
- **Non-fossil collections:** The merged tab will show only assertions (no geological context section). The tab name "採集環境" still makes sense in this case.

### No Changes Needed

- Backend (`helpers.py`, `admin.py`) -- no changes to data handling, only template restructuring
- `_inc_specimen_geological_context.html` (public-facing) -- unaffected, this is admin-only
- Database models -- no schema changes

## Future Consideration

Arctos's approach of making geology a **locality-level** property (shared across specimens from the same site) is architecturally more correct -- geology doesn't change between collecting visits to the same site. This could be a future refactor for NatureDB but is not a blocker for the current UI merge.
