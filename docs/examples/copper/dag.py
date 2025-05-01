from __future__ import annotations

import os
from pathlib import Path

from libactor.misc import T
from timer import Timer

from tum.dag import (
    NormTableActor,
    NormTableArgs,
    PartialFn,
    always_fail,
    get_context,
    get_dag,
    matrix_to_relational_table,
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
        PartialFn(table_range_select, start_row=3, end_row=2306, end_col="BO"),
        NormTableActor(NormTableArgs()),
        PartialFn(
            matrix_to_relational_table,
            drop_cols=list(range(27, 33)) + list(range(55, 60)),
            horizontal_props=[
                {"row": 0, "col": (6, 27)},
                {"row": 1, "col": (6, 27)},
                {"row": 0, "col": (34, 55)},
                {"row": 1, "col": (34, 55)},
            ],
        ),
        PartialFn(to_column_based_table, num_header_rows=2),
        PartialFn(write_table_to_file, outdir=output_dir, format="csv"),
    ],
)

with Timer().watch_and_report("run dag"):
    output = dag.process(
        {"table": (infile,)},
        set(["table"]),
        get_context(cwd),
    )
