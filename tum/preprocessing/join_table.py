from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import serde.csv
from sm.inputs.prelude import ColumnBasedTable

from tum.preprocessing.base import BasePipeOp


@dataclass
class TableJoinArgs:
    source: Path
    target: Path
    output: Path
    join_cols: Optional[tuple[int, int]]

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            source=Path(d["source"]),
            target=Path(d["target"]),
            output=Path(d["output"]),
            join_cols=d.get("join_cols"),
        )


class TableJoin(BasePipeOp):

    def invoke(self, args: TableJoinArgs):
        source_table = self.read_table(args.source)
        target_table = self.read_table(args.target)

        if args.join_cols is None:
            # join based on the first same name column
            source_cols = {
                col.name: col.index for col in reversed(source_table.columns)
            }
            target_cols = {
                col.name: col.index for col in reversed(target_table.columns)
            }

            same_names = set(source_cols.keys()).intersection(target_cols.keys())
            if len(same_names) == 0:
                raise ValueError(
                    "No same name columns found. Please specify the columns to join"
                )
            join_col = min(same_names, key=lambda name: source_cols[name])
            join_cols = (source_cols[join_col], target_cols[join_col])
        else:
            join_cols = args.join_cols

        print(f"Joining on column {join_cols[0]} and {join_cols[1]}")

        # now we join the two tables
        source_names = {col.name for col in source_table.columns}

        target_index = defaultdict(list)
        for ri, cval in enumerate(
            target_table.get_column_by_index(join_cols[1]).values
        ):
            target_index[cval].append(ri)

        joined_rows = []
        header = [col.name for col in source_table.columns]
        for col in target_table.columns:
            if col.index == join_cols[1]:
                continue
            if col.name in source_names:
                new_name = f"{col.name} ({col.index})"
                assert new_name not in source_names
                header.append(new_name)
            else:
                header.append(col.name)
        joined_rows.append(header)

        for ri in range(source_table.nrows()):
            key = source_table.columns[join_cols[0]].values[ri]
            baserow = [col.values[ri] for col in source_table.columns]
            for target_ri in target_index[key]:
                joined_rows.append(
                    baserow
                    + [
                        col.values[target_ri]
                        for col in target_table.columns
                        if col.index != join_cols[1]
                    ]
                )

        serde.csv.ser(joined_rows, args.output)

    def read_table(self, infile: Path):
        rows = serde.csv.deser(infile)
        return ColumnBasedTable.from_rows(
            rows[1:], table_id=infile.stem, headers=rows[0]
        )
