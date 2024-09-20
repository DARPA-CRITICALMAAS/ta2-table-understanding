from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import orjson
import pandas as pd
import typer
from sm.prelude import I, M, O


class TableRecognition:

    def __init__(self):
        pass

    def remove_cols(self, tbl: I.ColumnBasedTable, cols: list[int]):
        remove_cols = set(cols)
        # print("\n".join(f"{col.index}: {col.clean_name}" for col in tbl.columns))
        keep_cols = [col.index for col in tbl.columns if col.index not in remove_cols]
        return tbl.keep_columns(keep_cols)

    def convert_matrix_to_relational(
        self,
        tbl: I.ColumnBasedTable,
        trans_columns_index: dict[str, list[int]],
        missing_values: Optional[set[str]] = None,
    ):
        missing_values = missing_values or {"", "NA", "N/A", "NULL", "None"}

        trans_columns_index_set = {ci for v in trans_columns_index.values() for ci in v}
        trancols = {
            k: [tbl.get_column_by_index(ci) for ci in v]
            for k, v in trans_columns_index.items()
        }
        keepcols = [
            col for col in tbl.columns if col.index not in trans_columns_index_set
        ]

        rows = []
        nrows, ncols = tbl.shape()
        for ri in range(nrows):
            base_record: dict = {
                "row_index": ri,
            }
            for col in keepcols:
                base_record[col.clean_multiline_name] = col.values[ri]

            for group, groupcols in trancols.items():
                for col in groupcols:
                    if col.values[ri] in missing_values:
                        continue
                    record = base_record.copy()
                    record[f"{group}_attrs"] = col.clean_multiline_name
                    record[f"{group}_attr_values"] = col.values[ri]
                    rows.append(record)

        return I.ColumnBasedTable.from_dataframe(pd.DataFrame(rows), tbl.table_id)


app = typer.Typer()


@app.command()
def main(infile: Path, pipe_ops: str):
    if infile.suffix == ".csv":
        tbl = I.ColumnBasedTable.from_dataframe(
            pd.read_csv(infile, na_filter=False), infile.stem
        )
    else:
        raise NotImplementedError()

    for op in pipe_ops.split("|"):
        m = re.match(r"([a-zA-Z-_0-9]+)(\{.+\})?", op.strip())
        assert m is not None

        func = m.group(1)
        args = m.group(2)
        if args is not None:
            args = orjson.loads(args)
        else:
            args = {}

        if func == "matrix2relational":
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
            tbl = TableRecognition().convert_matrix_to_relational(tbl, cols)
        elif func == "remove_cols":
            cols: Optional[list[int]] = None
            incols = args["cols"]
            m2 = re.match(r"(\d+,)+\d+", incols)
            if m2 is not None:
                cols = [int(x) for x in incols.split(",")]
            tbl = TableRecognition().remove_cols(tbl, cols)
        else:
            raise NotImplementedError(func)

    (infile.parent / "transformed").mkdir(exist_ok=True)
    tbl.as_dataframe().to_csv(infile.parent / "transformed" / infile.name, index=False)
    return tbl


if __name__ == "__main__":
    app()
