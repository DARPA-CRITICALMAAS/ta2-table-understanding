# Per-Field Extraction Provenance in GeoChem

**Files changed:**
- `geochem_v1.1.ttl` — new properties (renamed from `geochem_v1.0.ttl`, `owl:versionInfo` bumped to `1.1.0`)
- `geochem_v1.1.shacl.ttl` — new validation shapes (renamed from `geochem_v1.0.shacl.ttl`)

**Goal:** record, per extracted field on a `:Sample` / `:Analysis` / `:Element`, where the value came from — supporting quote, page/cell location, which extraction pipeline produced it, and how confident the extraction is.

---

## Design decision: reuse `mo:Reference`, don't invent a parallel model

MinMod already has a provenance pattern used for `mo:MineralSite`/`mo:MineralInventory`:

```
<subject> mo:reference [
    a mo:Reference ;
    mo:document <paper> ;
    mo:property "<uri of the field this reference is for>"^^xsd:anyURI ;
    mo:page_info [ a mo:PageInfo ; mo:page 12 ; mo:bounding_box [...] ]
] .
```

An earlier draft (`schema/ontology extra.txt`) proposed a second, parallel "flat" model (`:field_evidence`, `:evidence`, `:evidence_field`, `:bbox`) that duplicated this instead of reusing it. We rejected that in favor of extending `mo:Reference` directly, so that geochem provenance stays queryable the same way as MinMod site-level provenance, and so a single `mo:Reference` SPARQL pattern works across both datasets.

**What that means concretely:**
- `mo:property` already scopes one `Reference` to a single field on the subject — so the draft's `:evidence_field` was dropped as redundant.
- For **PDF sources**, `mo:page_info → mo:PageInfo → mo:bounding_box → mo:BoundingBox` already gives page number + pixel rectangle — so the draft's `:bbox` was dropped as redundant.
- `mo:reference`'s domain is locked to `mo:MineralSite`/`mo:MineralInventory`. Reusing it directly on `:Sample`/`:Analysis`/`:Element` would RDFS-mistype those nodes as `mo:MineralSite`. A new sub-property, `:reference`, was added with the same range (`mo:Reference`) but domain widened to `:Sample`/`:Analysis`/`:Element`.
- `mo:PageInfo` requires exactly one `mo:page` (`owl:cardinality 1`) — it assumes a paginated PDF and has no slot for "which Excel sheet" or "which table cell". Rather than relaxing that constraint (which would mean editing a class from the *imported* `mo:` ontology), non-PDF sources simply **skip `mo:page_info` entirely** and attach a typed `:ArtifactInfo` node via `:artifact_info` instead. `mo:Reference` doesn't require `mo:page_info` to be present, so both styles are valid on the same class (and shouldn't be combined — see SHACL warning below).

---

## New properties

### `:reference` (object property)

| | |
|---|---|
| Domain | `:Sample` ∪ `:Analysis` ∪ `:Element` |
| Range | `mo:Reference` |
| Sub-property of | `mo:reference` |

The edge from an extracted value's subject to its provenance record.

### Datatype properties directly on `mo:Reference`

Fields describing *extraction quality/identity*, independent of what kind of artifact the value came from:

| Property | Range | Notes |
|---|---|---|
| `:evidence_quote` | `xsd:string` | Verbatim/near-verbatim source snippet |
| `:evidence_confidence` | `xsd:decimal` `[0,1]` | Confidence from *source anchoring* (quote+bbox=0.95, quote+page=0.80, quote only=0.55, asserted only=0.30). Distinct from `mo:confidence`, which scores model/candidate agreement |
| `:extraction_backend` | `xsd:string` | Table-extraction backend, e.g. `docling`, `pdfplumber`, `camelot` |
| `:extraction_confidence` | `xsd:decimal` `[0,1]` | Cross-backend agreement (`n_backends_agreeing / n_backends_active`). Distinct from `:evidence_confidence` and `mo:confidence` |
| `:paper_id` | `xsd:string` | Corpus-local paper id, e.g. `2018_Yuan_etal` |

### `:artifact_info` (object property) and the `:ArtifactInfo` class hierarchy

Fields describing *where inside the source artifact* the value came from live on a separate node, `:ArtifactInfo`, reached via `:artifact_info` on `mo:Reference`. Different artifact types need different fields, so `:ArtifactInfo` is a base class with type-specific subclasses (mirroring the `XCandidate` subclassing pattern already used throughout `mo:`), rather than one flat class with every field optional and a string type tag:

```
:ArtifactInfo (abstract)
├── :artifact_path : xsd:string   — shared by all subtypes, path/id of the source file
├── :TableArtifactInfo (abstract) — row/column-organized artifacts
│   ├── :table_id  : xsd:string   — stable id of the table, e.g. "T1"
│   ├── :table_row : xsd:integer  — must appear with :table_col
│   ├── :table_col : xsd:integer  — must appear with :table_row
│   ├── :ExcelArtifactInfo
│   │   └── :sheet_name : xsd:string   — required
│   └── :CsvArtifactInfo   — no extra fields beyond TableArtifactInfo
└── :JsonArtifactInfo
    └── :json_path : xsd:string   — required, e.g. "$.samples[3].analyses[1].grade"
```

`:artifact_info` itself:

| | |
|---|---|
| Domain | `mo:Reference` |
| Range | `:ArtifactInfo` |

An `:ArtifactInfo` node is always instantiated as one of the leaf subclasses (`:ExcelArtifactInfo`, `:CsvArtifactInfo`, `:JsonArtifactInfo`), never as the bare base class — the `rdf:type` *is* the type discriminator, so no separate `artifact_type` string field is needed. Adding a new artifact type later (HTML table, XML, ...) means adding a new subclass, not widening an existing flat property list.

### `:source_analysis_uri` on `:Analysis` (not provenance — a structural join key)

| | |
|---|---|
| Domain | `:Analysis` |
| Range | `xsd:anyURI` |

Not extraction provenance — it's a cross-reference back to the un-split spot-level `:Analysis` a per-element `:Analysis` was derived from (the draft's `:source_analysis_uri` was moved here instead of onto `mo:Reference`, since `mo:uri` is a node's own identifier, not a pointer to another node).

---

## What was dropped or renamed from the original draft, and why

| Draft property | Outcome | Why |
|---|---|---|
| `:field_evidence`, `:evidence` | dropped | Superseded by `:reference` (points straight at `mo:Reference`) |
| `:evidence_field` | dropped | Superseded by existing `mo:property` |
| `:bbox` | dropped | Superseded by existing `mo:page_info → mo:PageInfo → mo:BoundingBox` for PDF sources |
| `:source` | renamed → `:artifact_path`, moved to `:ArtifactInfo` | An unrelated `mo:source` already exists (domain `mo:MatchInfo`) — same label, different meaning. Also not a `Reference`-level field once `:ArtifactInfo` was introduced (see below) |
| `:source_analysis_uri` | kept, moved to `:Analysis` | It's a join key between two `:Analysis` nodes, not provenance metadata about a `mo:Reference` |

**Revision (2026-07-29):** `:table_id`/`:table_row`/`:table_col`/`:sheet_name` were first added directly on `mo:Reference` (flat), then moved onto the new `:ArtifactInfo` node (see above) once it was decided that artifact-location fields should live in their own type-scoped structure rather than accumulate as optional fields on `Reference` itself. `:json_path` and the `:ArtifactInfo` class hierarchy are new in this revision.

---

## Examples

### 1. PDF source (page + bounding box)

An `:Analysis` node's `:grade` value, extracted from page 12 of a PDF:

```turtle
@prefix :   <https://geochemistry.isi.edu/ontology/> .
@prefix mo: <https://minmod.isi.edu/ontology/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:analysis_042
    a :Analysis ;
    :element :element_Au ;
    :grade "2.3"^^xsd:decimal ;
    :grade_unit :unit_gpt ;
    :reference :ref_042_grade .

:ref_042_grade
    a mo:Reference ;
    mo:document :doc_2018_Yuan_etal ;
    mo:property "https://geochemistry.isi.edu/ontology/grade"^^xsd:anyURI ;
    mo:page_info [
        a mo:PageInfo ;
        mo:page 12 ;
        mo:bounding_box [
            a mo:BoundingBox ;
            mo:x_min "120.5"^^xsd:decimal ;
            mo:x_max "210.0"^^xsd:decimal ;
            mo:y_min "430.2"^^xsd:decimal ;
            mo:y_max "448.7"^^xsd:decimal ;
        ]
    ] ;
    :evidence_quote "Au grade reported as 2.3 g/t across the main zone" ;
    :evidence_confidence "0.95"^^xsd:decimal ;
    :extraction_backend "docling" ;
    :extraction_confidence "1.0"^^xsd:decimal ;
    :paper_id "2018_Yuan_etal" .
```

### 2. Excel source (sheet + cell, no PDF page)

The same kind of field, but extracted from an Excel supplementary table instead — note `:artifact_info` points at a typed `:ExcelArtifactInfo` node instead of `mo:page_info`:

```turtle
:analysis_043
    a :Analysis ;
    :element :element_Ag ;
    :grade "15.1"^^xsd:decimal ;
    :reference :ref_043_grade .

:ref_043_grade
    a mo:Reference ;
    mo:document :doc_2018_Yuan_etal ;
    mo:property "https://geochemistry.isi.edu/ontology/grade"^^xsd:anyURI ;
    :extraction_backend "openpyxl" ;
    :extraction_confidence "1.0"^^xsd:decimal ;
    :paper_id "2018_Yuan_etal" ;
    :artifact_info :ai_043 .
    # no mo:page_info here — SHACL warns if it's combined with :artifact_info

:ai_043
    a :ExcelArtifactInfo ;
    :artifact_path "supp:2018_Yuan_etal.xlsx" ;
    :sheet_name "Sheet2" ;
    :table_id "T2" ;
    :table_row 14 ;
    :table_col 5 .
```

### 3. JSON source (path into the document)

Same idea again, but the value was extracted from a JSON artifact — `:artifact_info` points at a `:JsonArtifactInfo` node with a `:json_path` instead of a table cell:

```turtle
:analysis_044
    a :Analysis ;
    :element :element_Au ;
    :grade "0.8"^^xsd:decimal ;
    :reference :ref_044_grade .

:ref_044_grade
    a mo:Reference ;
    mo:document :doc_2018_Yuan_etal ;
    mo:property "https://geochemistry.isi.edu/ontology/grade"^^xsd:anyURI ;
    :extraction_backend "custom_json_parser" ;
    :extraction_confidence "1.0"^^xsd:decimal ;
    :paper_id "2018_Yuan_etal" ;
    :artifact_info :ai_044 .

:ai_044
    a :JsonArtifactInfo ;
    :artifact_path "extract:2018_Yuan_etal.json" ;
    :json_path "$.samples[3].analyses[1].grade" .
```

### 4. Per-element split join key

If a single spot-level analysis (`:analysis_100`, covering multiple elements) is split into one `:Analysis` node per element downstream, each split node points back to the original via `:source_analysis_uri`:

```turtle
:analysis_100
    a :Analysis ;
    :element :element_Au ;
    :element :element_Ag ;
    :grade "..."^^xsd:decimal .
    # (spot-level, multiple elements on one Analysis)

:analysis_100_Au
    a :Analysis ;
    :element :element_Au ;
    :grade "2.3"^^xsd:decimal ;
    :source_analysis_uri "https://geochemistry.isi.edu/data/analysis_100"^^xsd:anyURI .
```

---

## SHACL validation (`geochem_v1.1.shacl.ttl`)

New shapes added:

- `:reference` (→ `mo:Reference`) added to `SampleShape`, `AnalysisShape`, `ElementShape`.
- `:source_analysis_uri` added to `AnalysisShape` (`xsd:anyURI`, max 1).
- `:ReferenceGeochemShape` (target `mo:Reference`):
  - `:evidence_quote`, `:evidence_confidence`, `:extraction_backend`, `:extraction_confidence`, `:paper_id`, all `sh:maxCount 1`
  - `:evidence_confidence` and `:extraction_confidence` bounded to `[0, 1]`
  - `:artifact_info` bounded to `sh:class :ArtifactInfo`, `sh:maxCount 1`
  - **Warning**: `mo:page_info` (PDF locator) and `:artifact_info` (non-PDF locator) should not both be present on the same `mo:Reference`
- `:ArtifactInfoShape` (target `:ArtifactInfo`): `:artifact_path`, max 1
- `:TableArtifactInfoShape` (target `:TableArtifactInfo`, inherited by `:ExcelArtifactInfo`/`:CsvArtifactInfo` instances via `rdfs:subClassOf` + `rdfs` inference): `:table_id`/`:table_row`/`:table_col`, indices bounded `≥ 0`; **Warning**: `:table_row` and `:table_col` must appear together
- `:ExcelArtifactInfoShape` (target `:ExcelArtifactInfo`): `:sheet_name` required (`sh:minCount 1`)
- `:JsonArtifactInfoShape` (target `:JsonArtifactInfo`): `:json_path` required (`sh:minCount 1`)

All new checks are `sh:Warning` severity, consistent with the rest of the file's recommendation-style shapes (they don't block loading, they flag likely mistakes).

Verified with `pyshacl` (`inference='rdfs'`, needed so `:ExcelArtifactInfo`/`:CsvArtifactInfo` instances pick up the inherited `:TableArtifactInfoShape` via subclass entailment): valid Excel- and JSON-style `mo:Reference` instances conform; a `:TableArtifactInfo` with only `:table_row` (no `:table_col`) and a `mo:Reference` combining `mo:page_info` with `:artifact_info` both correctly produce warnings.
