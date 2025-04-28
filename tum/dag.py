from __future__ import annotations

import os
import shutil
from functools import partial
from pathlib import Path
from typing import Optional, Sequence

from drepr.main import OutputFormat
from duneflow.ops.curation import SemanticModelCuratorActor, SemanticModelCuratorArgs
from duneflow.ops.formatter import to_column_based_table
from duneflow.ops.matrix_to_relational import matrix_to_relational_table
from duneflow.ops.matrix_to_relational_v2 import matrix_to_relational_table_v2
from duneflow.ops.norm import NormTableActor, NormTableArgs
from duneflow.ops.reader import read_table_from_file
from duneflow.ops.reader._table_file_reader import RawTable
from duneflow.ops.select import table_range_select
from duneflow.ops.writer import write_table_to_file
from gp.actors.data import KGDB, GPExample, KGDBArgs
from gpp.actors.gpp_sem_label_actor import GppSemLabelActor, GppSemLabelArgs
from gpp.actors.gpp_sem_model_actor import GppSemModelActor, GppSemModelArgs
from gpp.actors.graph_space_actor import (
    GraphSpaceV1Actor,
    GraphSpaceV1Args,
    PConnection,
)
from gpp.llm.qa_llm import Schema
from kgdata.models import Ontology
from libactor.cache import IdentObj
from libactor.dag import DAG, Flow, PartialFn
from libactor.dag._dag import ComputeFn
from libactor.storage import GlobalStorage
from libactor.typing import T
from sm.dataset import ColumnBasedTable, Context, Example, FullTable, Matrix
from sm.misc.prelude import get_classpath
from sm.namespaces.prelude import KGName, register_kgns
from timer import Timer
from tum.actors.drepr import DReprActor, DReprArgs
from tum.actors.mos import mos_map
from tum.config import CRITICAL_MAAS_DIR, PROJECT_DIR
from tum.db import MNDRDB
from tum.namespace import MNDRNamespace


class FixMNDRNamespace(MNDRNamespace):
    def id_to_uri(self, id: str) -> str:
        return str(id)

    def uri_to_id(self, uri: str) -> str:
        return str(uri)


kgns = FixMNDRNamespace.create()
register_kgns(KGName.Generic, kgns)


def select_table(tables: Sequence[T], idx: int) -> T:
    return tables[idx]


def write_ttl(text: str, outdir: Path) -> str:
    """Write a string to a file"""
    filename = os.path.join(outdir, "data.ttl")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def always_fail(input: T) -> T:
    raise Exception("Stopping here")


def get_context(
    cwd: Path,
):
    GlobalStorage.init(cwd / "storage")

    """Return context for the DAG"""
    with Timer().watch_and_report("get context"):
        ontology, entities = Ontology.from_ttl(
            KGName.Generic,
            kgns,
            Path(__file__).parent.parent / "schema/mos.ttl",
        )
        ontkey = "mos-v3"
        schema = Schema.from_ontology(ontology)
        context = {
            "ontology": IdentObj(ontkey, ontology),
            "schema": IdentObj(ontkey, schema),
            "kgns": ontology.kgns,
            "entity_columns": None,
        }

        pconns: list[PConnection] = []
        for pid in schema.props:
            prop = ontology.props[pid]
            assert len(prop.domains) == 1, prop.id
            pconns.append(
                PConnection(
                    prop=prop.id,
                    qual=None,
                    source_type=prop.domains[0],
                    target_type=prop.ranges[0] if len(prop.ranges) > 0 else None,
                    freq=1,
                )
            )

        context["graph_space"] = GraphSpaceV1Actor(
            GraphSpaceV1Args(
                top_k_data_props=5,
                top_k_object_props=5,
            )
        ).forward(
            None,
            context["schema"],
            context["ontology"],
            IdentObj(ontkey, pconns),
        )

        kgdb = KGDB(
            KGDBArgs(
                name=KGName.Generic,
                version="20250311",
                datadir=CRITICAL_MAAS_DIR / "data/minmod/databases",
                clspath=get_classpath(MNDRDB),
            )
        )
        kgdb.ontology = context["ontology"]
        context["kgdb"] = IdentObj(kgdb.args.get_key(), kgdb)
    return context


def get_type_conversions():
    def convert_table(table: ColumnBasedTable) -> FullTable:
        return FullTable(
            table=table,
            context=Context(),
            links=Matrix.default(table.shape(), list),
        )

    def table_to_example(table: ColumnBasedTable) -> Example[FullTable]:
        return Example(
            table.table_id,
            sms=[],
            table=convert_table(table),
        )

    def table_to_ident_example(table: ColumnBasedTable) -> IdentObj[Example[FullTable]]:
        return IdentObj(table.table_id, table_to_example(table))

    def table_to_ident(table: ColumnBasedTable) -> IdentObj[ColumnBasedTable]:
        return IdentObj(table.table_id, table)

    def table_to_ident_2(table: RawTable) -> IdentObj[RawTable]:
        return IdentObj(table.id, table)

    def extract_example(example: Example[FullTable]) -> FullTable:
        return example.table

    def example_to_ident_example(example: GPExample) -> IdentObj[GPExample]:
        return IdentObj(example.id, example)

    def example_to_ident_example_2(example: GPExample) -> IdentObj[Example[FullTable]]:
        return IdentObj(example.id, example)

    def example_to_ident_table(example: GPExample) -> IdentObj[FullTable]:
        return IdentObj(example.id, example.table)

    return [
        convert_table,
        table_to_example,
        table_to_ident_example,
        table_to_ident,
        table_to_ident_2,
        extract_example,
        example_to_ident_example,
        example_to_ident_example_2,
        example_to_ident_table,
    ]


def get_dag(
    cwd: Path,
    table: list[Flow | ComputeFn],
    sem_label: Optional[Flow | ComputeFn] = None,
    sem_model: Optional[Flow | ComputeFn] = None,
    without_json_export: bool = False,
):
    GlobalStorage.init(cwd / "storage")
    output_dir = cwd / "output"

    if sem_label is None:
        sem_label = Flow(
            source="table",
            target=GppSemLabelActor(
                GppSemLabelArgs(
                    model="gpp.sem_label.models.llm.SimpleSemLabelQAModel",
                    model_args={"model": "meta-llama/Llama-2-70b-chat-hf"},
                    data="gpp.sem_label.models.llm.get_dataset",
                    data_args={"sample_size": 20, "seed": 42},
                )
            ),
        )
    if sem_model is None:
        sem_model = Flow(
            source=["table", "sem_label"],
            target=GppSemModelActor(
                GppSemModelArgs(
                    algo="tum.sm.gpp.main.TumGppSemModelAlgo",
                    algo_args={},
                )
            ),
        )

    with Timer().watch_and_report("create dag"):
        dag = DAG.from_dictmap(
            {
                "table": table,
                "sem_label": sem_label,
                "sem_model": [
                    sem_model,
                    Flow(
                        source=["table", ""],
                        target=SemanticModelCuratorActor(
                            SemanticModelCuratorArgs(output_dir, "yml")
                        ),
                    ),
                ],
                "export": (
                    [
                        Flow(
                            source=["table", "sem_model"],
                            target=DReprActor(DReprArgs(output_dir, OutputFormat.TTL)),
                        ),
                        PartialFn(write_ttl, outdir=output_dir),
                    ]
                    + (
                        []
                        if without_json_export
                        else [PartialFn(mos_map, outdir=output_dir)]
                    )
                ),
            },
            type_conversions=get_type_conversions(),
        )
    return dag
