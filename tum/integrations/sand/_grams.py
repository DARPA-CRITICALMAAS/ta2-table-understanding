from __future__ import annotations

import copy
from pathlib import Path

from dependency_injector.wiring import Provide
from libactor.dag import Flow
from sand.container import AppContainer
from sand.extension_interface.assistant import IAssistant
from sand.helpers.dependency_injection import autoinject
from sand.models.entity import EntityAR
from sand.models.ontology import OntClassAR, OntPropertyAR
from sand.models.table import Table, TableRow
from sm.prelude import I
from tum.dag import PROJECT_DIR, GppSemLabelActor, GppSemLabelArgs, get_context, get_dag
from tum.integrations.sand._common import set_table


class GppMinModAssistant(IAssistant):
    @autoinject
    def __init__(
        self,
        dbpath: Path,
        entities: EntityAR = Provide[AppContainer.entities],
        classes: OntClassAR = Provide[AppContainer.classes],
        props: OntPropertyAR = Provide[AppContainer.properties],
    ):
        self.entities = entities
        self.classes = classes
        self.props = props

        cwd = PROJECT_DIR / "data/dag"
        self.dag = get_dag(
            cwd=cwd,
            table=set_table,
            # predict semantic types for each column
            sem_label=Flow(
                source="table",
                target=GppSemLabelActor(
                    GppSemLabelArgs(
                        model="gpp.sem_label.model_usage.contrastive_v220.SemLabelV220",
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
                            "ignore_no_type_column": False,
                            "target_label_ids": [
                                prop.id
                                for prop in self.props.values()
                                if prop.id not in {"drepr:unknown", "mos:category"}
                            ],
                        },
                    )
                ),
            ),
            without_sm_curation=True,
            without_json_export=True,
        )
        self.context = get_context(cwd, dbpath)

    def predict(self, table: Table, rows: list[TableRow]):
        norm_table = self.convert_table(table, rows)
        sm = self.dag.process(
            input={"table": (norm_table,)},
            output={"sem_model"},
            context=self.context,
        )["sem_model"][0].value
        rows = copy.deepcopy(rows)
        return sm, rows

    def convert_table(self, table: Table, rows: list[TableRow]) -> I.ColumnBasedTable:
        newtbl = I.ColumnBasedTable(
            f"p{table.project_id}---t:{table.id}---{table.name}",
            columns=[
                I.Column(index=ci, name=col, values=[row.row[ci] for row in rows])
                for ci, col in enumerate(table.columns)
            ],
        )
        return newtbl
