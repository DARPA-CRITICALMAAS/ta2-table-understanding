import os
from pathlib import Path

CRITICAL_MAAS_DIR = Path(
    os.environ.get(
        "CRITICAL_MAAS_DIR",
        str(Path(__file__).parent.parent.parent),
    )
)

DATA_DIR = Path(os.environ.get("DATA_DIR", CRITICAL_MAAS_DIR / "data"))

PROJECT_DIR = Path(
    os.environ.get("PROJECT_DIR", str(Path(__file__).parent.parent))
).absolute()

REAM_DIR = Path(os.environ.get("REAM_DIR", CRITICAL_MAAS_DIR / "data/ream")).absolute()

ONTOLOGY_FILE = Path(
    os.environ.get("ONTOLOGY_FILE", str(PROJECT_DIR / "schema/mos.ttl"))
)

DATA_REPO = Path(
    os.environ.get("DATA_REPO", str(CRITICAL_MAAS_DIR / "ta2-minmod-data"))
)

KG_ETL_FILE = Path(
    os.environ.get("KG_ETL_FILE", str(CRITICAL_MAAS_DIR / "ta2-minmod-kg" / "etl.yml"))
)

KG_OUTDIR = Path(os.environ.get("KG_OUTDIR", str(CRITICAL_MAAS_DIR / "kgdata")))
