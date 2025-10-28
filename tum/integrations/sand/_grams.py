from __future__ import annotations

import copy
import os
from functools import partial
from pathlib import Path
from typing import Optional, Sequence
from uuid import uuid4

import pandas as pd
import serde.json
from dependency_injector.wiring import Provide
from gp.actors.data import KGDB
from gp.misc.itemdistance import KGItemDistance
from gpp.sem_label.data_modules.v210 import SLabelV210DataModule
from gpp.sem_label.feats import (
    GetExamplesArgs,
    get_class_distance,
    get_examples,
    get_property_distance,
    get_sample_label,
    get_target_label,
    get_target_label_examples,
    get_text_embedding,
    get_text_sample_v1,
)
from gpp.sem_label.feats._sample import GetSampleLabelOutput
from gpp.sem_label.feats._target_label import GetTargetLabelOutput, get_similar_labels
from gpp.sem_label.model_usage.contrastive_v220 import RedirectMapping
from kgdata.models import Ontology, OntologyClass, OntologyProperty
from libactor.cache import IdentObj
from libactor.dag import Flow
from sand.container import AppContainer
from sand.extension_interface.assistant import IAssistant
from sand.helpers.dependency_injection import autoinject
from sand.models.entity import EntityAR
from sand.models.ontology import OntClassAR, OntPropertyAR
from sand.models.table import Table, TableRow
from sm.dataset import Example, FullTable
from sm.misc.funcs import filter_duplication
from sm.prelude import I
from smml.dataset import ColumnarDataset
from tum.dag import PROJECT_DIR, GppSemLabelActor, GppSemLabelArgs, get_context, get_dag
from tum.integrations.sand._common import InputTable, post_process_sm, set_table
from tum.sm.llm.openai_sem_label import InputTable, OpenAILiteralPrediction


class GppMinModAssistant(IAssistant):
    @autoinject
    def __init__(
        self,
        dbpath: Path,
        model_ckpt_file: Path,
        model_params_file: Path,
        example_dir: str | Path,
        entities: EntityAR = Provide[AppContainer.entities],
        classes: OntClassAR = Provide[AppContainer.classes],
        props: OntPropertyAR = Provide[AppContainer.properties],
    ):
        self.entities = entities
        self.classes = classes
        self.props = props

        example_dir = Path(example_dir)

        cwd = PROJECT_DIR / "data/dag"
        has_example_ids = {file.stem for file in example_dir.iterdir()}

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
                            "ckpt_file": model_ckpt_file,
                        },
                        data="tum.integrations.sand._grams.get_dataset",
                        data_args={
                            "example_dir": example_dir,
                            "model_params": model_params_file,
                            "ignore_no_type_column": False,
                            "target_label_ids": [
                                prop.uri
                                for prop in self.props.values()
                                if prop.uri.rsplit("/", 1)[1].lower() in has_example_ids
                            ],
                        },
                    )
                ),
            ),
            without_sm_curation=True,
            without_json_export=True,
        )
        self.context = get_context(cwd, dbpath)

        if "OPENAI_API_KEY" in os.environ:
            self.literal_prediction = OpenAILiteralPrediction(
                model="gpt-4.1",
                api_key=os.environ["OPENAI_API_KEY"],
                outdir=cwd / f"literal-prediction-gpt-4.1-20",
                max_sampled_rows=20,
            )
        else:
            self.literal_prediction = None

    def predict(self, table: Table, rows: list[TableRow]):
        norm_table = self.convert_table(table, rows)
        out = self.dag.process(
            input={"table": (norm_table,)},
            output={"sem_label", "sem_model"},
            context=self.context,
        )

        sm = out["sem_model"][0].value
        post_process_sm(
            InputTable.from_full_table(
                FullTable.from_column_based_table(norm_table),
                sample_size=20,
                seed=42,
            ),
            sm,
            self.literal_prediction,
        )
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


def make_raw_dataset(
    example_dir: Path,
    exs: Sequence[Example[FullTable]],
    kgdb: IdentObj[KGDB],
    ignore_no_type_column: bool = True,
    target_label_ids: Optional[Sequence[str]] = None,
    n_examples_per_label: int = 100,
):
    cls_distance = get_class_distance(kgdb.value.ontology).value
    prop_distance = get_property_distance(kgdb.value.ontology).value

    ontology = kgdb.value.ontology.value

    id2ex = {}
    for infile in example_dir.glob("*.json"):
        obj = serde.json.deser(infile)
        id2ex[obj["id"]] = obj

    samples = get_sample_label(exs, ontology.kgns, ignore_no_type_column)
    text_samples = get_text_sample_v1(exs, samples)
    target_labels = get_target_label(
        samples, ontology, cls_distance, prop_distance, target_label_ids
    )

    for l in target_labels:
        ex = id2ex[l["id"]]
        for alias in ex.get("aliases", []):
            if alias not in l["aliases"]:
                l["aliases"].append(alias)

    target_label_examples = [
        {
            "id": l["id"],
            "example": id2ex[l["id"]]["values"],
        }
        for l in target_labels
    ]

    return {
        "samples": text_samples,
        "target_labels": pd.DataFrame(data=target_labels).set_index("id"),
        "target_label_examples": {x["id"]: x["example"] for x in target_label_examples},
    }


def get_dataset(
    example_dir: Path,
    model_params: Path,
    n_examples_per_column: int = 100,
    n_examples_per_label: int = 100,
    ignore_no_type_column: bool = True,
    target_label_ids: Optional[Sequence[str]] = None,
):
    params = serde.json.deser(model_params)
    datamodule = SLabelV210DataModule(
        f"/tmp/{uuid4()}",  # we do not need data_dir in this case.
        params["embedding_model"],
        get_text_embedding(params["embedding_model"]),
        train_batch_size=32,
        eval_batch_size=32,
        n_examples_per_column=n_examples_per_column,
        n_examples_per_label=n_examples_per_label,
    )

    def func(
        examples: IdentObj[Sequence[Example[FullTable]]],
        kgdb: IdentObj[KGDB],
    ) -> ColumnarDataset:
        name = str(uuid4())
        is_train = False
        dataset = make_raw_dataset(
            example_dir,
            examples.value,
            kgdb,
            ignore_no_type_column,
            target_label_ids,
            n_examples_per_label,
        )
        dataset = datamodule.transformation(name, dataset)
        dataset = datamodule.make_columnar_dataset(
            name, dataset, embedding_readonly=False
        )
        datamodule.embedding_manager.flush(soft=False)
        return dataset

    return func
    return func
    return func
