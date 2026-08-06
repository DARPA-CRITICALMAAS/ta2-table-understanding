# Geolocation Extraction Output → GeoChem/MinMod Compliant JSON-LD

Covers the review of `2020_Frenzel_etal.geolocated.jsonld` / `2024_Denisova_etal.geolocated.jsonld`. Decision taken: **Option 2** — the multi-candidate/`is_selected` geolocation output is pipeline-internal working data. It gets collapsed down to a single, MinMod-shaped `mo:LocationInfo` per site before it's emitted as ontology-facing JSON-LD; no new `LocationInfoCandidate`-style class is added.

---

## Part 1 — Ontology fixes made (`geochem_v1.1.ttl` / `geochem_v1.1.shacl.ttl`)

These were bugs in the ontology, not just the data, discovered by comparing our re-declared classes against what the live MinMod KG actually stores (queried `https://minmod.isi.edu/sparql` directly).

| Fix | Detail |
|---|---|
| Added `mo:CandidateEntity` class | `source` (required), `confidence` (required, `[0,1]`), `observed_name` (optional), `normalized_uri` (optional) — `subClassOf mo:MatchInfo`. Confirmed live: 3.4M instances, the *only* `*Candidate`-shaped type actually used in production. |
| `mo:country`, `mo:state_or_province`, `mo:crs` range changed | Was `mo:CountryCandidate` / `mo:StateOrProvinceCandidate` / `mo:CoordinateReferenceSystemCandidate` → now `mo:CandidateEntity`, matching live data. |
| Removed `mo:CountryCandidate`, `mo:StateOrProvinceCandidate`, `mo:CoordinateReferenceSystemCandidate` from re-declaration | Zero live instances of any of these; the typed-subclass pattern was declared upstream but never adopted by the ETL/API. Still reachable via `owl:imports` if the upstream ontology keeps them — we just stopped re-declaring/depending on them. |
| Added SHACL shapes `:CandidateEntityShape`, `:LocationInfoShape` | Enforce the above; validated with `pyshacl` against both conforming and violating examples. |
| `owl:versionInfo` bumped | `1.1.0` → `1.1.1` in both files. |

**Not fixed, flagged for follow-up:** `mo:CommodityCandidate`, `mo:DepositTypeCandidate`, `mo:MaterialFormCandidate`, `mo:ResourceReserveCategoryCandidate`, `mo:UnitCandidate` are very likely equally dead in production (same generic-`CandidateEntity` pattern), but that wasn't confirmed field-by-field — separate pass. Also, `mo:CandidateEntity` isn't declared in the upstream `ta2-minmod-kg/schema/ontology.ttl` either; our re-declaration here is a local stopgap, not a substitute for fixing it there.

---

## Part 2 — Target JSON-LD shape

```json
{
  "@context": {
    "@vocab": "https://geochemistry.isi.edu/ontology/",
    "geochem": "https://geochemistry.isi.edu/ontology/",
    "mo": "https://minmod.isi.edu/ontology/",
    "res": "https://geochemistry.isi.edu/resource/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "geo": "http://www.opengis.net/ont/geosparql#",
    "name": { "@id": "rdfs:label" },
    "location_info": { "@id": "mo:location_info" },
    "location": { "@id": "mo:location", "@type": "geo:wktLiteral" },
    "country": { "@id": "mo:country" },
    "state_or_province": { "@id": "mo:state_or_province" },
    "crs": { "@id": "mo:crs" },
    "location_source": { "@id": "mo:location_source" },
    "location_description": { "@id": "mo:location_description" },
    "source": { "@id": "mo:source" },
    "confidence": { "@id": "mo:confidence", "@type": "xsd:decimal" },
    "observed_name": { "@id": "mo:observed_name" },
    "normalized_uri": { "@id": "mo:normalized_uri", "@type": "@id" },
    "reference": { "@id": "mo:reference" },
    "document": { "@id": "mo:document", "@type": "@id" },
    "property": { "@id": "mo:property", "@type": "xsd:anyURI" },
    "evidence_quote": { "@id": "geochem:evidence_quote" },
    "has_mineral_site": { "@id": "geochem:has_mineral_site", "@type": "@id", "@container": "@list" }
  },
  "@id": "https://doi.org/10.1007/s00126-023-01217-4",
  "@type": "geochem:MineralResourcePaper",
  "paper_title": "...",
  "paper_doi": "10.1007/s00126-023-01217-4",
  "paper_url": "https://doi.org/10.1007/s00126-023-01217-4",
  "has_mineral_site": [
    {
      "@id": "https://geochemistry.isi.edu/resource/2024-denisova-etal/abm",
      "@type": "mo:MineralSite",
      "name": "ABM",
      "location_info": {
        "@type": "mo:LocationInfo",
        "location": "POINT (-85.90663 36.22426)",
        "location_source": "mindat",
        "location_description": "Elmwood Mine, Carthage, Smith County, Tennessee, USA (https://www.mindat.org/loc-4125.html)",
        "country": [
          { "@type": "mo:CandidateEntity", "observed_name": "USA", "source": "mindat", "confidence": 0.9 }
        ],
        "state_or_province": [
          { "@type": "mo:CandidateEntity", "observed_name": "Tennessee", "source": "mindat", "confidence": 0.9 }
        ]
      },
      "reference": [
        {
          "@type": "mo:Reference",
          "document": "https://doi.org/10.1007/s00126-023-01217-4",
          "property": "https://minmod.isi.edu/ontology/location_info",
          "evidence_quote": "The ABM deposit is a bimodal-felsic, replacement-style volcanogenic massive sulfide deposit (VMS) ... Yukon, Canada."
        }
      ]
    }
  ]
}
```

Two things worth calling out:
- `location_info` is a **single object**, not a list — matches `mo:MineralSite.location_info: Optional[LocationInfo]` in production (`minmodkg/models/kg/mineral_site.py:73`). If every candidate was rejected, omit `location_info` from the site entirely rather than emitting an empty object.
- `reference` here is `mo:reference` (the pre-existing MinMod property — its domain already covers `mo:MineralSite`), **not** our newer `:reference` (that one is Sample/Analysis/Element-only, unrelated to this).

---

## Part 3 — Field-by-field mapping

| Extraction-output field | Disposition | Target |
|---|---|---|
| `location_info` (list of candidates) | **Collapse** to the one where `metadata.is_selected == true` | `mo:location_info` → single `mo:LocationInfo` (or omitted, if the selected candidate is a rejection) |
| `@type: "LocationInfo"` | **Fix namespace** | `"@type": "mo:LocationInfo"` |
| `location: {latitude, longitude}` | **Reshape** | `mo:location`, WKT string `"POINT (<lon> <lat>)"`, note longitude first |
| `country: ["USA"]` (bare string) | **Reshape** | `mo:country` → `[{ "@type": "mo:CandidateEntity", "observed_name": "USA", "source": <candidate.source>, "confidence": <candidate.confidence> }]` |
| `state_or_province: ["Tennessee"]` | **Reshape** | Same pattern, `mo:state_or_province` |
| `source` (e.g. `"mindat"`) | **Move down one level, and reuse for two things**: (a) copied onto each `country`/`state_or_province` `CandidateEntity.source`, since the same geocoding step produced both; (b) also becomes `mo:location_source` directly on `LocationInfo` (already means exactly "method used to obtain the deposit location", `geochem_v1.1.ttl:838-843`) | `mo:CandidateEntity.source` + `mo:LocationInfo.location_source` |
| `confidence` | Same move as `source` | `mo:CandidateEntity.confidence` on each country/state_or_province entity |
| `metadata.observed_name` | **Move**, direct field match | `mo:observed_name` on the same `CandidateEntity` |
| `metadata.normalized_uri` | **Do not put on the country/state `CandidateEntity`** — it identifies the external gazetteer *place record* (a mindat/Google Maps page), not a canonical Country/StateOrProvince entity. Putting it on `mo:country`'s `CandidateEntity.normalized_uri` would claim a mindat URL *is* a Country, which is wrong. No canonical country/state entity-linking happened in this data at all — leave `normalized_uri` absent (it's optional) rather than fabricate one. | Fold into `mo:location_description` instead, as free text: `"<observed_name> (<normalized_uri>)"` |
| `metadata.country`, `metadata.is_selected` | **Drop.** Redundant once collapsed — selection already happened by construction, and `metadata.country` duplicates the top-level `country` field. | — |
| `metadata.formatted_address` | **Drop**, or fold into `location_description` if you want to keep it (optional, your call — no dedicated slot exists) | — / `mo:location_description` |
| `metadata.reasoning` (per-candidate, LLM-generated) | **Drop from the graph.** Only the winning candidate survives collapse; the reasoning for *why* is pipeline audit trail, not paper evidence — see decision note below. | pipeline logs, not JSON-LD |
| `paper_doi` (repeated on each `LocationInfo`) | **Drop.** Existed to tag which paper each of several candidates came from; redundant once there's one `LocationInfo` per site and the paper linkage already exists via `MineralResourcePaper → has_mineral_site`. | — |
| `deposit_site_name` | **Drop.** Redundant with the `MineralSite`'s own `name`. | — |
| `crs` (currently always `null` in the sample data) | Same pattern as `country`/`state_or_province` if ever populated: a `CandidateEntity`, not a bare value | `mo:crs` |
| `paper_id` (on the `MineralResourcePaper` node) | **Drop.** Collides with the `:paper_id` we added for per-field extraction provenance (domain `mo:Reference`) — reusing it here mistypes the paper node. `paper_doi` already uniquely identifies the paper, so there's nothing to replace it with. | — |
| `evidence_excerpt` (site-level, verbatim paper text) | **Keep, route through the Reference pattern.** This is exactly what `:evidence_quote` was built for — genuine, verbatim supporting text. | `mo:reference → mo:Reference → :evidence_quote`, `mo:property` = `mo:location_info`'s URI |
| `rejection_confidence`, `selector_reasoning` (site-level) | **Drop from the graph** — see decision note below | pipeline logs, not JSON-LD |
| Whole `metadata` object as a JSON-LD `@vocab`-scoped field | **Delete the wrapper entirely.** Its two salvageable fields (`observed_name`, `normalized_uri`) move to `CandidateEntity`/`location_description` as above; nothing is left to justify keeping `metadata` as a container. Also fixes a real bug: because `@vocab` applied recursively, `metadata.country`/`metadata.normalized_uri` were silently emitting *extra*, spurious `mo:country`/`geochem:normalized_uri` triples on the metadata blank node, alongside the real ones on `LocationInfo`. | — |

### Decision note: why `selector_reasoning`/`rejection_confidence` don't get the `evidence_excerpt` treatment

`evidence_excerpt` is a **verbatim quote from the paper** — that's precisely `:evidence_quote`'s contract ("verbatim or near-verbatim paper snippet"). `selector_reasoning` and `rejection_confidence` are the **LLM's own generated explanation** of its selection process — not paper text, and not really "evidence" in the ontology's sense. Stretching `:evidence_quote` to cover both would blur a distinction worth keeping. If you do want an audit trail for selection decisions, that's a separate, deliberate ontology decision (not something to back into by overloading `:evidence_quote`) — flag it if you want that discussed rather than silently included.

---

## Part 4 — What the two valid files were reworked into

`2020_Frenzel_etal.geolocated.jsonld` and `2024_Denisova_etal.geolocated.jsonld` have been rewritten in place following the mapping above: `location_info` collapsed to the selected candidate (or omitted for sites where the selection was a rejection), `country`/`state_or_province` reshaped into `mo:CandidateEntity` lists, `location` reshaped into WKT, and `evidence_excerpt` moved under `mo:reference`.
