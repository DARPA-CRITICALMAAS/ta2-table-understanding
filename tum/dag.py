from __future__ import annotations

import base64
import hashlib
import os
import shutil
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Optional, Sequence

import httpx
import orjson
import sm.outputs as O
from drepr.main import OutputFormat
from duneflow.ops.curation import SemanticModelCuratorActor, SemanticModelCuratorArgs
from duneflow.ops.formatter import to_column_based_table
from duneflow.ops.matrix_to_relational import matrix_to_relational_table
from duneflow.ops.matrix_to_relational_v2 import matrix_to_relational_table_v2
from duneflow.ops.norm import NormTableActor, NormTableArgs, norm_column_based_table
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
from slugify import slugify
from sm.dataset import ColumnBasedTable, Context, Example, FullTable, Matrix
from sm.misc.prelude import get_classpath
from sm.namespaces.prelude import KGName, register_kgns
from sm.outputs.semantic_model import SemanticModel
from timer import Timer
from tum.actors.drepr import DReprActor, DReprArgs
from tum.actors.mos import mos_map
from tum.config import CRITICAL_MAAS_DIR, PROJECT_DIR
from tum.db import MNDRDB
from tum.namespace import MNDRNamespace
from tum.preprocessing.extract_table import extract_table_from_pdf


class FixMNDRNamespace(MNDRNamespace):
    def id_to_uri(self, id: str) -> str:
        return str(id)

    def uri_to_id(self, uri: str) -> str:
        return str(uri)


kgns = FixMNDRNamespace.create()
register_kgns(KGName.Generic, kgns)


def get_ontology():
    return Ontology.from_ttl(
        KGName.Generic,
        kgns,
        Path(__file__).parent.parent / "schema/mos.ttl",
    )[0]


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
    dbpath: Path = CRITICAL_MAAS_DIR / "data/minmod/databases",
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
                datadir=dbpath,
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
    table: Sequence[Flow | ComputeFn] | Flow | ComputeFn,
    sem_label: Optional[Flow | ComputeFn] = None,
    sem_model: Optional[Flow | ComputeFn] = None,
    without_sm_curation: bool = False,
    without_json_export: bool = False,
    sand_endpoint: Optional[str] = None,
):
    GlobalStorage.init(cwd / "storage")
    output_dir = cwd / "output"

    if sem_label is None:
        sem_label = Flow(
            source="table",
            target=GppSemLabelActor(
                GppSemLabelArgs(
                    model="tum.sm.dsl.dsl_sem_label.DSLSemLabelModel",
                    model_args={
                        "model": "logistic-regression",
                        "ontology_factory": "tum.dag.get_ontology",
                        "data_dir": PROJECT_DIR / "data/minmod/mos-v3",
                    },
                    data="tum.sm.dsl.dsl_sem_label.get_dataset",
                    data_args={},
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

    sem_model_pipeline = [sem_model]
    # add sand curator to the pipeline
    if sand_endpoint is not None:
        sem_model_pipeline.append(
            Flow(
                source=["table", ""],
                target=PartialFn(
                    sand_curator,
                    sand_endpoint=sand_endpoint,
                    output_dir=output_dir,
                ),
            )
        )
    if not without_sm_curation:
        sem_model_pipeline.append(
            Flow(
                source=["table", ""],
                target=SemanticModelCuratorActor(
                    SemanticModelCuratorArgs(output_dir, "yml")
                ),
            ),
        )

    with Timer().watch_and_report("create dag"):
        dag = DAG.from_dictmap(
            {
                "table": table,
                "sem_label": sem_label,
                "sem_model": sem_model_pipeline,
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


def sand_curator(
    table: IdentObj[ColumnBasedTable],
    sm: IdentObj[SemanticModel],
    sand_endpoint: str,
    output_dir: Path,
) -> IdentObj[SemanticModel]:
    from sand.client import Client

    client = Client(sand_endpoint)

    project_name = "Default"
    project_id = client.get_project_id(project_name)

    # TODO: we can warn about the conflict if we store the table key in the description
    # retrieve or create table if it doesn't exist
    table_name = slugify(table.value.table_id) + "__" + shorten_key(table.key)
    if not client.tables.has({"project": project_id, "name": table_name}):
        # create table if it does not exist
        resp = httpx.post(
            client.projects.endpoint + f"/{project_id}/upload",
            files={
                table_name: (
                    table_name + ".csv",
                    table.value.df.to_csv(index=False, sep=","),
                )
            },
            data={"selected_tables": "[0]"},
        )
        if resp.status_code != 200:
            raise Exception(f"Failed to upload table: {resp.text}")

    table_id = client.get_table_id(project_name, table_name)

    # we create the semantic models if they do not exist in SAND
    if not client.semantic_models.has({"table": table_id, "name": "sm-auto-0"}):
        client.semantic_models.create(
            {
                "table": table_id,
                "name": "sm-auto-0",
                "description": "",
                "version": 0,
                "data": to_sand_sm(sm.value),
            }
        )

    print(
        "Edit the semantic model in SAND at this URL:",
        f"{sand_endpoint}/tables/{table_id}",
    )

    # we download the semantic model
    resp = client.semantic_models.get_one({"table": table_id, "name": "sm-auto-0"})
    curated_sm = from_sand_sm(resp["data"])

    if resp["version"] > 0:
        # this means that the semantic model has been updated
        O.ser_simple_tree_yaml(
            table.value,
            curated_sm,
            kgns,
            output_dir / f"description.yml",
        )
    return IdentObj(key=hash_dict(resp["data"]), value=curated_sm)


def to_sand_sm(sm: SemanticModel) -> dict:
    """Convert a SemanticModel to a dictionary suitable for SAND."""

    def serialize_classnode(node: O.ClassNode) -> dict:
        return {
            "id": node.id,
            "type": "class_node",
            "uri": node.abs_uri,
            "label": node.label,
            "approximation": node.approximation,
        }

    def serialize_datanode(node: O.DataNode) -> dict:
        return {
            "id": node.id,
            "type": "data_node",
            "column_index": node.col_index,
            "label": node.label,
        }

    def serialize_literalnode(node: O.LiteralNode) -> dict:
        return {
            "id": node.id,
            "type": "literal_node",
            "value": {"value": node.value, "type": node.datatype.value},
            "is_in_context": node.is_in_context,
            "label": node.label,
        }

    return {
        "nodes": [
            (
                serialize_classnode(node)
                if isinstance(node, O.ClassNode)
                else (
                    serialize_datanode(node)
                    if isinstance(node, O.DataNode)
                    else serialize_literalnode(node)
                )
            )
            for node in sm.iter_nodes()
        ],
        "edges": [
            {
                "label": edge.label,
                "uri": edge.abs_uri,
                "source": edge.source,
                "target": edge.target,
                "approximation": edge.approximation,
            }
            for edge in sm.iter_edges()
        ],
    }


def from_sand_sm(obj: dict) -> SemanticModel:
    """Convert a dictionary from SAND to a SemanticModel."""
    nodes = []
    for node in obj["nodes"]:
        if node["type"] == "class_node":
            nodes.append(
                asdict(
                    O.ClassNode(
                        id=node["id"],
                        abs_uri=node["uri"],
                        rel_uri=node["uri"],
                        approximation=node["approximation"],
                        readable_label=node["label"],
                    )
                )
            )
        elif node["type"] == "data_node":
            nodes.append(
                asdict(
                    O.DataNode(
                        id=node["id"],
                        col_index=node["column_index"],
                        label=node["label"],
                    )
                )
            )
        elif node["type"] == "literal_node":
            nodes.append(
                asdict(
                    O.LiteralNode(
                        id=node["id"],
                        value=node["value"]["value"],
                        datatype=O.LiteralNodeDataType(node["value"]["type"]),
                        is_in_context=node["is_in_context"],
                        readable_label=node["label"],
                    )
                )
            )

    edges = [
        asdict(
            O.Edge(
                source=edge["source"],
                target=edge["target"],
                abs_uri=edge["uri"],
                rel_uri=edge["uri"],
                readable_label=edge["label"],
                approximation=edge.get("approximation", False),
            )
        )
        for edge in obj["edges"]
    ]

    return SemanticModel.from_dict({"nodes": nodes, "edges": edges})


def shorten_key(key: str) -> str:
    """Shorten a key using SHA-256 and return base64 digest."""
    return base64.b64encode(hashlib.sha256(key.encode()).digest()).decode("utf-8")[:8]


def hash_dict(d: dict) -> str:
    """Hash a dictionary using SHA-256 and return base64 digest."""
    return base64.b64encode(hashlib.sha256(orjson.dumps(d)).digest()).decode("utf-8")[
        :8
    ]
