import os
from pathlib import Path

CRITICAL_MAAS_DIR = Path(
    os.environ.get(
        "CRITICAL_MAAS_DIR",
        str(Path(__file__).parent.parent.parent),
    )
)

REAM_DIR = Path(os.environ.get("REAM_DIR", CRITICAL_MAAS_DIR / "data/ream")).absolute()
