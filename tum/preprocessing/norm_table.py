from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import serde.csv
from sm.misc.prelude import Matrix

from tum.preprocessing.base import BasePipeOp


@dataclass
class TableNormArgs:
    infile: Path

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            infile=Path(d["infile"]),
        )


class TableNorm(BasePipeOp):
    def invoke(self, args: TableNormArgs):
        if args.infile.suffix != ".csv":
            return

        cells = Matrix(serde.csv.deser(args.infile))
        update = False

        # norm numbers
        for ri, ci, cell in cells.enumerate_flat_iter():
            if re.match("^[0-9,]+$", cell) is not None:
                cells[ri, ci] = cell.replace(",", "")
                update = True

        if update:
            print(f"Update {args.infile}")
            serde.csv.ser(cells.data, args.infile)
