from __future__ import annotations

import os
from mimetypes import suffix_map
from pathlib import Path

from timer import Timer
from tum.dag import (
    NormTableActor,
    NormTableArgs,
    PartialFn,
    always_fail,
    get_context,
    get_dag,
    matrix_to_relational_table,
    matrix_to_relational_table_v2,
    read_table_from_file,
    select_table,
    table_range_select,
    to_column_based_table,
    write_table_to_file,
)

os.environ["HF_REMOTE"] = "http://localhost:18861"

cwd = Path(__file__).parent
output_dir = cwd / "output"
infile = next(cwd.glob("*.xlsx"))

dag = get_dag(
    cwd,
    table=[
        PartialFn(read_table_from_file),
        PartialFn(select_table, idx=0),
        PartialFn(table_range_select, start_row=1, start_col=1, end_col="DL"),
        NormTableActor(NormTableArgs()),
        PartialFn(
            write_table_to_file,
            outdir=output_dir,
            format="csv",
            suffix="_00_matrix.temp",
        ),
        PartialFn(
            matrix_to_relational_table_v2,
            matrix_prop={
                "row": 2,
                "vertical_col": (9, 10),
                "horizontal_col": (10, 30),
                "repeat": 5,
            },
            start_data_row=3,
            horizontal_props=[
                {"row": 1, "col": (9, 114)},
            ],
        ),
        PartialFn(
            write_table_to_file, outdir=output_dir, format="csv", suffix="_01__rel.temp"
        ),
        PartialFn(to_column_based_table, num_header_rows=3),
        PartialFn(write_table_to_file, outdir=output_dir, format="csv"),
    ],
)

with Timer().watch_and_report("run dag"):
    output = dag.process(
        {"table": (infile,)},
        set(["sem_label"]),
        get_context(),
    )
