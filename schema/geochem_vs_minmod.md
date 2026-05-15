# Ontology Comparison Report: MinMod vs GeoChem

**Files compared:**
- MinMod: `../ta2-minmod-kg/schema/ontology.ttl` (v2.1.1)
- GeoChem: `schema/geochem_v1.0.ttl` (v1.0.0)

---

## Key Finding: GeoChem is a Selective Superset of MinMod

`geochem_v1.0.ttl` declares `owl:imports <https://minmod.isi.edu/ontology/>` and explicitly re-declares the MinMod classes and properties relevant to geochemistry. Concepts specific to mineral systems modelling (`mo:MineralSystem`, `mo:EvidenceLayer`, `mo:MappableCriteria` and their associated properties) are intentionally omitted from the explicit declarations — they remain accessible via the import but play no role in geochem data. Semantically, GeoChem is a superset of the relevant MinMod vocabulary.

---

## Complete MinMod Inventory (all present in GeoChem)

### Classes (29 re-declared in GeoChem)

| Class | Description |
|---|---|
| `mo:BoundingBox` | Bounding box coordinates in a document |
| `mo:Commodity` | A mineral commodity |
| `mo:CommodityCandidate` | Candidate commodity match (subclass of MatchInfo) |
| `mo:CoordinateReferenceSystem` | CRS definition |
| `mo:CoordinateReferenceSystemCandidate` | CRS match candidate |
| `mo:Country` | Country entity |
| `mo:CountryCandidate` | Country match candidate |
| `mo:DepositType` | Deposit type with environment and group |
| `mo:DepositTypeCandidate` | Deposit type match candidate |
| `mo:Document` | Source document (doi, journal, title, year, etc.) |
| `mo:GeologyInfo` | Geological information (age, lithology, etc.) |
| `mo:LocationInfo` | Location information (WKT, CRS, country, etc.) |
| `mo:MatchInfo` | Candidate match with confidence score |
| `mo:MaterialForm` | Material form with commodity and conversion factor |
| `mo:MaterialFormCandidate` | Material form match candidate |
| `mo:Measure` | A quantity with value and unit |
| `mo:MineralInventory` | Mineral inventory entry (grade, ore, commodity) |
| `mo:MineralSite` | A mineral deposit site |
| `mo:PageInfo` | Page reference with bounding box |
| `mo:Reference` | Document reference for provenance |
| `mo:ResourceReserveCategory` | JORC/NI 43-101 resource/reserve category |
| `mo:ResourceReserveCategoryCandidate` | Category match candidate |
| `mo:StateOrProvince` | State or province entity |
| `mo:StateOrProvinceCandidate` | State/province match candidate |
| `mo:ThingHasLabel` | Mixin: requires `rdfs:label` |
| `mo:ThingMayHaveAltLabel` | Mixin: may have `skos:altLabel` |
| `mo:ThingMayHaveComment` | Mixin: may have `rdfs:comment` |
| `mo:Unit` | Measurement unit |
| `mo:UnitCandidate` | Unit match candidate |

**Not re-declared** (available via `owl:imports` but not relevant to geochem): `mo:EvidenceLayer`, `mo:MappableCriteria`, `mo:MineralSystem`

### Object Properties (29 re-declared in GeoChem)

`bounding_box`, `category`, `commodity`, `country`, `crs`, `cutoff_grade`, `deposit_type_candidate`, `document`, `geology_info`, `grade`, `location_info`, `location_info_objectproperty`, `match_info_objectproperty`, `material_form`, `material_form_objectproperty`, `measure_objectproperty`, `mineral_inventory`, `mineral_inventory_objectproperty`, `mineral_site_objectproperty`, `normalized_uri`, `ore`, `page_info`, `page_info_objectproperty`, `property`, `reference`, `reference_objectproperty`, `source`, `state_or_province`, `unit`

**Not re-declared**: `deposit_type`, `energy`, `mappable_criteria_objectproperty`, `mineral_system_objectproperty`, `outflow`, `pathway`, `potential_dataset`, `preservation`, `supporting_references`, `trap`

### Data Properties (51 re-declared in GeoChem)

`age`, `bounding_box_dataproperty`, `comments`, `confidence`, `contained_metal`, `conversion`, `date`, `deposit_type_dataproperty`, `description`, `document_dataproperty`, `doi`, `environment`, `geology_info_dataproperty`, `group`, `issue`, `journal`, `lithology`, `location`, `location_accuracy`, `location_description`, `location_source`, `location_info_dataproperty`, `match_info_dataproperty`, `material_form_dataproperty`, `measure_dataproperty`, `mineral_inventory_dataproperty`, `mineral_site_dataproperty`, `modified_at`, `month`, `name`, `observed_name`, `page`, `page_info_dataproperty`, `primary_commodities`, `process`, `record_id`, `secondary_commodities`, `site_rank`, `site_type`, `source_id`, `title`, `unit_name`, `uri`, `value`, `volume`, `x_max`, `x_min`, `y_max`, `y_min`, `year`, `zone`

**Not re-declared**: `criteria`, `evidence_layer_dataproperty`, `mappable_criteria_dataproperty`, `relevance_score`, `theoretical`

---

## What GeoChem Adds Beyond MinMod

### GeoChem-Only Classes (`:` namespace = `https://geochemistry.isi.edu/ontology/`)

| Class | Description |
|---|---|
| `:MineralResourcePaper` | Scientific paper containing geochemical data |
| `:Sample` | Geochemical sample collected from a mineral site |
| `:Analysis` | Geochemical analysis performed on a sample |
| `:Element` | Chemical element being analysed |
| `:Isotope` | Isotope associated with an analysis |

### GeoChem-Only Object Properties

| Property | Domain → Range | Description |
|---|---|---|
| `:has_sample` | `MineralResourcePaper` → `Sample` | Links paper to its samples |
| `:has_analysis` | `Sample` → `Analysis` | Links sample to analyses |
| `:from_deposit` | `Sample` → `mo:MineralSite` | Links sample to its deposit |
| `:element` | `Analysis` → `Element` | Element analysed |
| `:isotope` | `Analysis` → `Isotope` | Isotope measured |
| `:grade_unit` | `Analysis` → `mo:UnitCandidate` | Unit for grade measurement |
| `:detection_limit_unit` | `Element` → `mo:UnitCandidate` | Unit for detection limit |

### GeoChem-Only Data Properties

**On `Sample`:** `sample_id`, `sample_name`, `sample_local_id`, `sample_type`, `collection_date`, `description`, `mineral`, `sampling_method`, `sample_preparation`, `material_class`, `material_class_comment`, `analysed_material`, `sample_deposit_relation`, `geological_province`, `strat_unit_uid`, `strat_grouping`, `earth_material_group`, `earth_material_qualifier`, `mode_occurrence`, `metamorphic_grade`, `alteration`, `paragenetic_stage`, `texture`, `color`, `associated_minerals`, `feature_type`, `feature_name`, `feature_local_uid`, `top_depth_m`, `bottom_depth_m`, `comments`

**On `Analysis`:** `grade`, `aggregation_method`, `analytical_method`, `analysis_id`, `instrument_type`, `laboratory_location`, `operating_conditions`, `standards_used`, `data_quality`, `analysis_date`

**On `MineralResourcePaper`:** `paper_title`, `paper_authors`, `paper_doi`, `paper_year`, `paper_journal`, `paper_url`

**On `Element`:** `detection_limit`

### Geochem-Namespace Convenience Properties Extending MinMod Classes

These properties have domains on MinMod classes but are declared in the geochem namespace (`:`) to avoid polluting `mo:`. They remain sub-properties of MinMod's abstract property hierarchy so OWL reasoners classify them correctly:

| Property | Domain | Sub-property of | Notes |
|---|---|---|---|
| `:row_index` | `mo:MineralSite` | `mo:mineral_site_dataproperty` | Row index in source spreadsheet — no MinMod equivalent |

---

## Summary

| | MinMod | GeoChem |
|---|---|---|
| Classes | 32 | 29 (mo:) + 5 (:) = **34** |
| Object Properties | 39 | 29 (mo:) + 7 (:) = **36** |
| Data Properties | 56 | 51 (mo:) + 49 (:) = **100** |

---

## Adding GeoChem Data to a MinMod Triplestore

GeoChem instance data can be loaded directly into an existing MinMod triplestore without conflict. RDF graphs are additive and the open-world assumption means unknown terms are simply ignored by MinMod applications rather than causing errors.

### What Works

- **Shared `mo:` vocabulary**: Any `mo:MineralSite`, `mo:MineralInventory`, etc. instances created via GeoChem use the same URIs as MinMod and are immediately compatible.
- **The bridge property**: `:from_deposit` links a `:Sample` to an existing `mo:MineralSite` URI in the triplestore, enabling cross-dataset SPARQL queries without any special joins.
- **GeoChem-specific classes are isolated by design**: `:Sample`, `:Analysis`, `:Element`, `:Isotope`, `:MineralResourcePaper` live in the geochem namespace. MinMod applications will ignore them, which is the correct behaviour — they are not MinMod concepts.

### Key Requirement

The `mo:MineralSite` URI used in `:from_deposit` must match the URI already in the MinMod triplestore. The geochem data is only as connected as the site identifiers it references.

### Property Name Notes

GeoChem defines `:grade`, `:collection_date`, `:description`, and `:comments` with similar local names to some MinMod properties. These will never appear on the same subject node, so there is no RDF-level risk. The only one worth noting for future data mapping:

- **`:grade` vs `mo:grade`**: GeoChem `:grade` is a raw literal on `:Analysis`; MinMod `mo:grade` is an object property on `mo:MineralInventory` pointing to a `mo:Measure` node. If geochem grade data ever needs to be promoted into a MinMod mineral inventory, it requires wrapping in a `mo:Measure` instance — not a simple rename.

### Recommendation

- Use `mo:` properties for anything that maps to an existing MinMod class (site, inventory, location, document, etc.)
- Keep all geochem-specific data in the `:` namespace — never declare properties under `mo:` that MinMod's ontology does not define
- `:row_index` is the only geochem convenience property extending a MinMod class — it has no MinMod equivalent and is used to track the source row in a table or spreadsheet
