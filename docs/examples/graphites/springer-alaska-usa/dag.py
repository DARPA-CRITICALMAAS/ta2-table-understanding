from __future__ import annotations

import os
from pathlib import Path

from gpp.actors.gpp_sem_label_actor import GppSemLabelActor, GppSemLabelArgs
from kgdata.models import Ontology
from libactor.dag import Flow
from timer import Timer
from tum.dag import (
    NormTableActor,
    NormTableArgs,
    PartialFn,
    get_context,
    get_dag,
    matrix_to_relational_table,
    read_table_from_file,
    select_table,
    table_range_select,
    to_column_based_table,
    write_table_to_file,
)

# os.environ["HF_REMOTE"] = "http://localhost:18861"

cwd = Path(__file__).parent
output_dir = cwd / "output"
infile = next(cwd.glob("*.csv"))
context = get_context(cwd)
ontology: Ontology = context["ontology"].value

dag = get_dag(
    cwd,
    table=[
        PartialFn(read_table_from_file),
        PartialFn(select_table, idx=0),
        NormTableActor(NormTableArgs()),
        to_column_based_table,
        PartialFn(
            write_table_to_file,
            outdir=output_dir,
            format="csv",
        ),
    ],
    sem_label=Flow(
        "table",
        GppSemLabelActor(
            GppSemLabelArgs(
                model="gpp.sem_label.model_usage.contrastive_v220.ISemLabelV220",
                model_args={
                    "ckpt_file": "/Volumes/research/resm-v2/data/lightning/csv/cta-dev/version_40/checkpoints/epoch=5-step=4728.ckpt",
                },
                data="gpp.sem_label.model_usage.contrastive_v220.get_dataset",
                data_args={
                    "example_dir": Path(
                        "/Volumes/research/resm-v2/data/datasets/ontology_examples"
                    ),
                    "model_params": Path(
                        "/Volumes/research/resm-v2/data/lightning/csv/cta-dev/version_40/params.json"
                    ),
                    "is_cta_only": False,
                    "ignore_no_type_column": False,
                    "target_label_ids": [
                        prop.id
                        for prop in ontology.props.values()
                        if prop.is_data_property()
                        and prop.id.split("/")[-1] not in ["record_id", "title", "url"]
                    ],
                },
            )
        ),
    ),
    without_json_export=True,
)

with Timer().watch_and_report("run dag"):
    output = dag.process(
        {"table": (infile,)},
        set(["sem_label"]),
        context,
    )
