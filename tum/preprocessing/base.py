from __future__ import annotations

from functools import lru_cache
from pathlib import Path


class BasePipeOp:

    @lru_cache()
    def transformed_dir(self, infile: Path) -> Path:
        dir = infile.parent / "transformed"
        dir.mkdir(exist_ok=True, parents=True)
        return dir
        return dir
