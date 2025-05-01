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
infile = next(cwd.glob("*.csv"))


dag = get_dag(
    cwd,
    table=[
        PartialFn(read_table_from_file),
        PartialFn(select_table, idx=0),
        NormTableActor(NormTableArgs()),
        PartialFn(to_column_based_table, num_header_rows=1),
    ],
)

with Timer().watch_and_report("run dag"):
    output = dag.process(
        {"table": (infile,)},
        set(["sem_label"]),
        get_context(),
    )
