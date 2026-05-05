# Herbarium Specimen Label Transcription Prompt

A copy-and-paste prompt for any multimodal AI chat (Claude, ChatGPT, Gemini) that returns structured JSON matching the `/admin/records` quick-edit form fields.

## How to use

1. Open an AI chat that supports image input.
2. Copy the **Prompt** block below and paste it as your message.
3. Attach the specimen image (high resolution preferred — 2048px or larger).
4. Send. Paste the returned JSON into the quick-edit form (each field name maps 1:1 to a form field).

---

## Prompt

````
You are transcribing a herbarium specimen label from a photograph. Output ONE JSON object that matches the schema below — no prose, no markdown fences, no commentary.

Rules:
- Transcribe text exactly as written: preserve original spelling, capitalization, Chinese characters, Latin diacritics, and line context.
- Use null when a field is not present on the label.
- Use the literal string "[...]" inside a value for runs of text that are visible but illegible.
- Do not interpret, translate, normalize, or guess. If unsure, prefer null.
- If the same information appears in multiple languages on the label, prefer the original language as written; do not merge.

Schema:
{
  "verbatim_collector":        string | null,    // Primary collector name(s) as written
  "companion_text":            string | null,    // Co-collectors / 隨同採集者, as written
  "field_number":              string | null,    // Field / collection number (採集號); keep prefixes like "TPM-"
  "collect_date_year":         integer | null,   // 4-digit year, e.g. 1923
  "collect_date_month":        integer | null,   // 1–12
  "collect_date_day":          integer | null,   // 1–31
  "verbatim_collect_date":     string | null,    // Date string exactly as written, e.g. "14 Sept. 1923"
  "verbatim_scientific_name":  string | null,    // Scientific name on the label, as written, including author abbreviations
  "verbatim_locality":         string | null,    // Locality / habitat description as written, line breaks replaced with " / "
  "altitude":                  number | null,    // Elevation in meters. If a range is given, the lower bound. If unitless and clearly meters, use it. If feet, convert to meters and round to integer.
  "altitude2":                 number | null,    // Upper bound of elevation range; null if single value
  "verbatim_longitude":        string | null,    // Longitude as written (DMS, decimal, or other), no normalization
  "verbatim_latitude":         string | null,    // Latitude as written
  "longitude_decimal":         number | null,    // Decimal degrees; negative for W. Compute from DMS if only DMS is given. Round to 6 decimals.
  "latitude_decimal":          number | null,    // Decimal degrees; negative for S. Round to 6 decimals.
  "identifier_1": {
    "verbatim_identifier":      string | null,   // Person who made the FIRST identification
    "verbatim_date":            string | null,   // Date of first identification, as written
    "verbatim_identification":  string | null    // The taxon name written for the first identification
  } | null,
  "identifier_2": {
    "verbatim_identifier":      string | null,   // Subsequent identifier; null if only one identification visible
    "verbatim_date":            string | null,
    "verbatim_identification":  string | null
  } | null,
  "other_text_on_label":       string | null,    // Anything else on the label not captured above: host plant, soil, associated species, project codes, references, accession stamps, etc.
  "transcriber_notes":         string | null,    // Your notes about confidence, multiple labels visible, parts torn off, ambiguous handwriting. English or Chinese OK.
  "ai_model":                  string,           // Your model family/name as you self-identify, e.g. "Claude Sonnet", "GPT-4o", "Gemini 2.5"
  "ai_version":                string,           // Your version / build identifier, e.g. "4.6", "claude-sonnet-4-5-20250929", "2024-11-20"
  "ai_date":                   string            // Today's date in ISO format YYYY-MM-DD when this transcription was generated
}

Edge cases:
- If only the year is on the label: set collect_date_year and verbatim_collect_date; leave month/day null.
- If a date range is given (e.g. "10–14 Sept 1923"): use the FIRST date for the structured year/month/day, and put the full range in verbatim_collect_date.
- If only DMS coordinates are present: fill verbatim_longitude/verbatim_latitude AND compute longitude_decimal/latitude_decimal.
- If only decimal coordinates are present: fill longitude_decimal/latitude_decimal AND leave verbatim_longitude/verbatim_latitude with the original written form.
- Multiple labels on one sheet (original + annotation slip): treat the largest/oldest as primary; put annotation-slip identifications into identifier_1 / identifier_2 by date order; mention the multi-label situation in transcriber_notes.
- Stamped accession numbers, herbarium codes (e.g. "HAST"), and barcodes go in other_text_on_label, not field_number.

Output the JSON object only.
````

---

## Example output

For a label reading:

> Quercus alba L.
> Berkshire Co., Mass.
> 14 Sept. 1923, alt. 350 m
> E.M. Holloway, № 412
> det. J. Smith 1965 — Quercus alba L.

```json
{
  "verbatim_collector": "E.M. Holloway",
  "companion_text": null,
  "field_number": "412",
  "collect_date_year": 1923,
  "collect_date_month": 9,
  "collect_date_day": 14,
  "verbatim_collect_date": "14 Sept. 1923",
  "verbatim_scientific_name": "Quercus alba L.",
  "verbatim_locality": "Berkshire Co., Mass.",
  "altitude": 350,
  "altitude2": null,
  "verbatim_longitude": null,
  "verbatim_latitude": null,
  "longitude_decimal": null,
  "latitude_decimal": null,
  "identifier_1": {
    "verbatim_identifier": "J. Smith",
    "verbatim_date": "1965",
    "verbatim_identification": "Quercus alba L."
  },
  "identifier_2": null,
  "other_text_on_label": null,
  "transcriber_notes": null,
  "ai_model": "Claude Sonnet",
  "ai_version": "4.6",
  "ai_date": "2026-05-06"
}
```

---

## Field mapping (JSON → quick-edit form)

| JSON key | Form input id |
|---|---|
| `verbatim_collector` | `quick-verbatim_collector` |
| `companion_text` | `quick-companion_text` |
| `field_number` | `quick-field_number` |
| `collect_date_year` / `_month` / `_day` | `quick-collect_date_year` / `_month` / `_day` |
| `verbatim_collect_date` | `quick-verbatim_collect_date` |
| `verbatim_scientific_name` | `quick-quick__verbatim_scientific_name` |
| `verbatim_locality` | `quick-verbatim_locality` |
| `altitude`, `altitude2` | `quick-altitude`, `quick-altitude2` |
| `verbatim_longitude`, `verbatim_latitude` | `quick-verbatim_longitude`, `quick-verbatim_latitude` |
| `longitude_decimal`, `latitude_decimal` | `quick-decimal_longitude`, `quick-decimal_latitude` |
| `identifier_1.*` | `quick-quick__id1_verbatim_identifier` / `_date` / `_identification` |
| `identifier_2.*` | `quick-quick__id2_verbatim_identifier` / `_date` / `_identification` |
| `other_text_on_label` | `quick-quick__other_text_on_label` |
| `transcriber_notes` | `quick-quick__user_note` |

A future version of this page may auto-fill the form from a pasted JSON blob.
