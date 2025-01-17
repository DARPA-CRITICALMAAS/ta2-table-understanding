from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import orjson
import pandas as pd
import typer
from sm.prelude import I, M, O

from tum.preprocessing.extract_table import TableExtraction, TableExtractionArgs
from tum.preprocessing.join_table import TableJoin, TableJoinArgs
from tum.preprocessing.norm_table import TableNorm, TableNormArgs

app = typer.Typer(pretty_exceptions_short=True, pretty_exceptions_enable=False)


@app.command()
def main(infile: Path, pipe_ops: str):
    (infile.parent / "transformed").mkdir(exist_ok=True)

    for op_i, op in enumerate(pipe_ops.split("|")):
        m = re.match(r"([a-zA-Z-_0-9]+)(\{.+\})?", op.strip())
        assert m is not None

        func = m.group(1)
        args = m.group(2)
        if args is not None:
            args = orjson.loads(args)
        else:
            args = {}

        if op_i == 0:
            args["infile"] = infile

        if func == "extract_table":
            TableExtraction().invoke(TableExtractionArgs.from_dict(args))
        elif func == "join_table":
            TableJoin().invoke(TableJoinArgs.from_dict(args))
        elif func == "norm_table":
            TableNorm().invoke(TableNormArgs.from_dict(args))
        elif func == "matrix2relational":
            incols = args["cols"]
            cols: Optional[dict[str, list[int]]] = None
            if isinstance(incols, str):
                m2 = re.match(r"(\d+,)+\d+", incols)
                if m2 is not None:
                    cols = {"": [int(x) for x in incols.split(",")]}
                else:
                    m3 = re.match(r"(\d+:(?:\d+)?,)*(\d+:(?:\d+)?)", incols)
                    if m3 is not None:
                        cols = {}
                        if m3.group(0).find(",") == -1:
                            m3groups = {"": m3.group(0)}
                        else:
                            m3groups = {
                                f"g{i}": x for i, x in enumerate(m3.group(0).split(","))
                            }

                        for gname, m3g in m3groups.items():
                            m4 = re.match(r"(\d+):(\d+)?", m3g)
                            assert m4 is not None
                            if m4.group(2) is None:
                                rng = list(
                                    range(
                                        int(m4.group(1)),
                                        max(col.index for col in tbl.columns) + 1,
                                    )
                                )
                            else:
                                rng = list(range(int(m4.group(1)), int(m4.group(2))))
                            cols[gname] = [
                                ci for ci in rng if tbl.has_column_by_index(ci)
                            ]
            else:
                assert isinstance(incols, dict)
                cols = incols
            assert cols is not None
            tbl = TableExtraction().convert_matrix_to_relational(tbl, cols)
        elif func == "remove_cols":
            cols: Optional[list[int]] = None
            incols = args["cols"]
            m2 = re.match(r"(\d+,)+\d+", incols)
            if m2 is not None:
                cols = [int(x) for x in incols.split(",")]
            tbl = TableExtraction().remove_cols(tbl, cols)
        else:
            raise NotImplementedError(func)

    # tbl.as_dataframe().to_csv(infile.parent / "transformed" / infile.name, index=False)


if __name__ == "__main__":
    app()
