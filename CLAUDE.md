# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This library (tum - TA2 Table Understanding) creates semantic descriptions of mineral-related tables for data extraction and integrates with SAND for interactive curation. Part of DARPA CRITICALMAAS program, it works with MinMod Knowledge Graph to model and publish mineral deposit data.

## Repository Structure

The codebase is organized into distinct processing layers:

- **tum/preprocessing/** - Table extraction and normalization from PDFs using Azure Document Intelligence
- **tum/sm/** - Semantic modeling algorithms
  - **gpp/** - Graph++ algorithm for semantic model generation (main algorithm)
  - **dsl/** - DSL-based semantic labeling approach
  - **llm/** - OpenAI-based semantic labeling
- **tum/lib/** - Core utilities (graph generation, Steiner tree, table registration)
- **tum/actors/** - Ray actors for distributed processing (data, db, drepr, MOS mapping)
- **tum/integrations/sand/** - SAND UI integration modules
- **tum/raw_transformations/** - Data type transformers (numbers, coordinates, decimals)
- **schema/** - RDF/TTL ontology definitions and validation
  - `mos.ttl` - simplified MinMod ontology
  - `geochem_v1.0.ttl` - GeoChem ontology (extends MinMod with Sample/Analysis/Element/Isotope classes)
  - `geochem_v1.0.shacl.ttl` - SHACL validation shapes for GeoChem
  - `geochem_vs_minmod.md` - comparison report detailing what GeoChem adds/omits relative to MinMod
- **data/** - Databases, examples, and table descriptions organized by project (minmod, geochem)

## Project Setup

### Recommended Folder Structure

```
<DARPA-CRITICALMAAS-DIR>
├── data                      # databases storage
├── ta2-minmod-data           # data repository
├── ta2-minmod-kg             # KG repository
└── ta2-table-understanding   # this repository
```

Set `MINMOD_DIR` environment variable to the parent directory:
```bash
export MINMOD_DIR=<DARPA-CRITICALMAAS-DIR>
```

### Installation

**Using uv (package manager):**
```bash
cd ta2-table-understanding
python -m venv .venv
uv sync
source .venv/bin/activate
```

**Build required databases:**
```bash
export CFG_FILE=$MINMOD_DIR/ta2-minmod-kg/config.yml.template
uv run python -m tum.make_db [--project <project=minmod>]
```

**Using Docker (recommended for deployment):**
```bash
bash scripts/build_docker.sh
```

### Environment Configuration

Copy `.env.template` to `.env` and configure:
- `AZURE_DOC_INTEL_ENDPOINT` - Azure Document Intelligence endpoint for PDF table extraction
- `AZURE_ACCESS_KEY` - Azure access key
- `OPENAI_API_KEY` - Required for GPT-based semantic labeling
- `CRITICAL_MAAS_DIR` - Override default working directory
- `ONTOLOGY_FILE` - Override default ontology file path

## Common Commands

### Database Management

Build entities, ontology classes, and properties databases:
```bash
uv run python -m tum.make_db --project minmod
uv run python -m tum.make_db --project geochem
```

### SAND UI (Interactive Table Modeling)

Initialize SAND database (run once):
```bash
uv run python -m sand init -d $MINMOD_DIR/data/minmod/sand.db
```

Start SAND UI for MinMod project:
```bash
uv run python -m sand start -d $MINMOD_DIR/data/minmod/sand.db -c $MINMOD_DIR/ta2-table-understanding/minmod.sand.yml
```

Start SAND UI for Geochemistry project:
```bash
uv run python -m sand start -d $MINMOD_DIR/data/geochem/sand.db -c $MINMOD_DIR/ta2-table-understanding/geochem.sand.yml
```

### Docker Deployment

Build Docker images:
```bash
bash scripts/build_docker.sh
```

Run services (SAND UI + nginx):
```bash
docker compose up
```

Services:
- SAND MinMod UI: port 5524
- SAND Geochem UI: port 5525
- nginx: ports 80 (HTTP) and 443 (HTTPS)

### Table Preprocessing

Extract tables from PDFs:
```bash
uv run python -m tum.preprocessing <command>
```

### MOS Mapping

Map Mineral Occurrence Schema (MOS) data:
```bash
uv run python -m tum.map_mos
```

## Architecture

### Semantic Modeling Pipeline

1. **Table Extraction** (tum/preprocessing/extract_table.py)
   - Extracts tables from PDFs using Azure Document Intelligence
   - Produces RawTable objects

2. **Table Normalization** (tum/preprocessing/norm_table.py, join_table.py)
   - Converts to column-based format
   - Handles multi-table joins

3. **Semantic Labeling** (tum/sm/)
   - **Graph++ (gpp)**: Main algorithm using graph-based approach with Steiner tree optimization
   - **DSL**: Domain-specific language approach
   - **LLM**: OpenAI GPT-based labeling
   - Predicts semantic types (class + property pairs) for each column

4. **Semantic Model Generation** (tum/sm/gpp/algo_v300.py)
   - Builds candidate graphs connecting semantic types
   - Uses Steiner tree algorithms to find optimal connections
   - Outputs SemanticModel objects

5. **DRepr Export** (tum/actors/drepr.py)
   - Converts semantic models to DRepr format for data transformation
   - Exports to TTL (Turtle RDF) or JSON

### Key Components

**MNDRDB (tum/db.py)**: Database wrapper for entities, ontology classes, and properties. Built from MinMod KG ontology.

**Namespace (tum/namespace.py)**: MNDRNamespace handles URI/ID conversions for MinMod resources.

**DAG (tum/dag.py)**: Defines directed acyclic graphs for processing workflows using libactor. Connects preprocessing, semantic modeling, and export steps.

**Graph Generation (tum/lib/graph_generation.py)**: Core logic for building candidate semantic graphs from column semantic types.

**Steiner Tree (tum/lib/steiner_tree.py)**: Finds minimal connecting subgraphs in ontology to link semantic types.

### SAND Integration

SAND UI configuration files (minmod.sand.yml, geochem.sand.yml) specify:
- Entity/class/property databases
- Available semantic model assistants (Grams++, GPT4.1, GPT5)
- Export formats (TTL, JSON)
- Search configuration

Integration modules in tum/integrations/sand/ provide:
- Database adapters (_db.py)
- Semantic labeling assistants (_grams.py, _openai.py)
- MinMod JSON export (_minmod_json_export.py)
- DSL integration (_dsl.py)

### Multiple Projects

The system supports multiple projects (minmod, geochem) with separate:
- Ontology files (schema/mos.ttl, schema/geochem_v1.0.ttl)
- Databases (data/minmod/databases/, data/geochem/databases/)
- SAND configurations (minmod.sand.yml, geochem.sand.yml)
- Docker services (sand:5524, geochem:5525)

## Dependencies

Uses uv for package management. Key dependencies:
- **sem-desc**: Semantic description framework
- **drepr-v2**: Data representation and transformation
- **kgdata**: Knowledge graph utilities
- **minmodkg/minmodapi**: MinMod KG models and API
- **ray/pyspark**: Distributed processing
- **openai**: LLM integration
- **azure-ai-formrecognizer**: PDF table extraction
- **sand-drepr/web-sand**: SAND UI (optional dependency group)

Install SAND dependencies:
```bash
uv sync --group sand
```

## Configuration Customization

SAND configuration files are highly customizable:
- **Entity databases**: Switch entity DB files or use in-memory dicts
- **Assistants**: Enable/disable different semantic labeling algorithms
- **Export formats**: Configure TTL vs JSON output
- **Model checkpoints**: Update Grams++ model paths

Edit minmod.sand.yml or geochem.sand.yml to customize.
