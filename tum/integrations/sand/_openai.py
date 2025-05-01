from __future__ import annotations

import copy
import random
from pathlib import Path

from dependency_injector.wiring import Provide
from libactor.cache import fmt_keys
from libactor.dag import Flow, PartialFn
from sand.container import AppContainer
from sand.extension_interface.assistant import IAssistant
from sand.helpers.dependency_injection import autoinject
from sand.models.entity import EntityAR
from sand.models.ontology import OntClassAR, OntPropertyAR
from sand.models.table import Table, TableRow
from sm.prelude import I

from tum.dag import (
    PROJECT_DIR,
    GppSemLabelActor,
    GppSemLabelArgs,
    IdentObj,
    get_context,
    get_dag,
)
from tum.integrations.sand._common import set_table


class OpenAIMinModAssistant(IAssistant):
    @autoinject
    def __init__(
        self,
        dbpath: Path,
        model: str,
        api_key: str,
        max_sampled_rows: int,
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
                        model="tum.sm.llm.openai_sem_label.OpenAISemLabel",
                        model_args={
                            "model": model,
                            "api_key": api_key,
                            "max_sampled_rows": max_sampled_rows,
                        },
                        data="tum.sm.llm.openai_sem_label.get_dataset",
                        data_args={},
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
