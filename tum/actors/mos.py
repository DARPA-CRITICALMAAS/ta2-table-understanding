from __future__ import annotations

from pathlib import Path

import serde.json
from rdflib import Graph
from tum.map_mos import MosMapping


def mos_map(data: str | Path, outdir: Path) -> None:
    g = Graph()
    if isinstance(data, str):
        g.parse(data=data, format="turtle")
    else:
        assert isinstance(data, Path)
        g.parse(location=str(data), format="turtle")

    output = MosMapping(g, "https://minmod.isi.edu/users/s/usc")(dup_record_ids=True)
    serde.json.ser(output, outdir / "data.json", indent=2)
