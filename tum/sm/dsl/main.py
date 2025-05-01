from __future__ import annotations

import random
import shutil
from copy import deepcopy
from pathlib import Path

import requests
from dsl.dsl import DSL, DSLTable
from gpp.sem_label.isem_label import TableSemLabelAnnotation
from loguru import logger
from sm.dataset import Dataset, Example, FullTable
from sm.inputs.column import Column
from sm.inputs.table import ColumnBasedTable
from sm.misc.funcs import assert_not_null, assert_one_item
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.outputs.semantic_model import (
    ClassNode,
    DataNode,
    Edge,
    SemanticModel,
    SemanticType,
)
from sm.typing import ColumnIndex, ExampleId, InternalID
from smml.dataset import ColumnarDataset

from tum.config import PROJECT_DIR
from tum.lib.cgraph import CGraph
from tum.lib.graph_generation import GraphGeneration
from tum.lib.steiner_tree import SteinerTree
from tum.misc import SemanticTypePrediction
from tum.namespace import MNDRNamespace

DREPR_UNK = "http://purl.org/drepr/1.0/Unknown"


def get_training_data(ds: str, kgns: KnowledgeGraphNamespace):
    examples: list[Example[DSLTable]] = []
    for file in (PROJECT_DIR / f"data/training_set/{ds}").iterdir():
        if file.name.endswith(".txt"):
            file.read_text()
            chunks = [x.strip() for x in file.read_text().split("--------------------")]
            chunks = [x for x in chunks if len(x) > 0]
            c, p = chunks[0].split("---")
            stype = SemanticType(
                class_abs_uri=kgns.get_abs_uri(c),
                class_rel_uri=c,
                predicate_abs_uri=kgns.get_abs_uri(p),
                predicate_rel_uri=p,
            )

            for i in range(1, len(chunks)):
                chunk = chunks[i].splitlines()
                assert chunk[0].startswith("::") and chunk[0].endswith("::")
                assert chunk[2] == ""
                tbl = DSLTable.from_column_based_table(
                    ColumnBasedTable(
                        table_id=f"{chunk[0]}--{i}",
                        columns=[Column(index=0, name=chunk[1], values=chunk[3:])],
                    )
                )
                sm = SemanticModel()
                sm.add_edge(
                    Edge(
                        source=sm.add_node(
                            ClassNode(
                                abs_uri=stype.class_abs_uri, rel_uri=stype.class_rel_uri
                            )
                        ),
                        target=sm.add_node(DataNode(col_index=0, label=chunk[0])),
                        abs_uri=stype.predicate_abs_uri,
                        rel_uri=stype.predicate_rel_uri,
                    )
                )
                examples.append(Example(id=tbl.table.table_id, sms=[sm], table=tbl))
    return examples


def get_semantic_types(
    dsl: DSL, table: ColumnBasedTable, top_n: int, ignore_empty_val: bool = True
):
    if ignore_empty_val:
        table = deepcopy(table)
        for col in table.columns:
            col.values = [
                v for v in col.values if v is not None and str(v).strip() != ""
            ]

    dsl_tbl = DSLTable.from_column_based_table(table)

    exs = []
    for col in dsl_tbl.columns:
        tblid = f"{table.table_id}---{col.col_index}"
        exs.append(
            Example(
                id=tblid,
                table=DSLTable(
                    table=table.keep_columns([col.col_index]), columns=[col]
                ),
                sms=[],
            )
        )

    stypes = [assert_one_item(ex_stypes) for ex_stypes in dsl(exs, top_n=top_n)]
    return [
        [
            SemanticTypePrediction(
                stype.semantic_type,
                stype.score,
                col.index,
                col.clean_multiline_name or "",
            )
            for stype in stypes[ci]
        ]
        for ci, col in enumerate(table.columns)
        # if top 1 semantic type is unknown, then we remove them
        if stypes[ci][0].semantic_type.class_abs_uri != DREPR_UNK
    ]


def gen_can_graph(
    ex_stypes: list[list[SemanticTypePrediction]],
    kgns: KnowledgeGraphNamespace,
):
    gen = GraphGeneration(
        {
            kgns.get_abs_uri("mos:MineralSite"): 1,
            kgns.get_abs_uri("mos:MineralInventory"): 1,
        },
        {
            (
                kgns.get_abs_uri("mos:MineralSite"),
                kgns.get_abs_uri("mos:MineralInventory"),
            ): {kgns.get_abs_uri("mos:mineral_inventory"): 1.0},
        },
    )

    cg = gen(ex_stypes)
    logger.info(
        "Candidate Graph with: {} nodes and {} edges",
        cg.num_nodes(),
        cg.num_edges(),
    )
    return cg


def pred_sm(tbl: ColumnBasedTable, cgraph: CGraph, kgns: KnowledgeGraphNamespace):
    edge_probs = {}
    for edge in cgraph.iter_edges():
        edge_probs[(edge.source, edge.target, edge.key)] = (
            edge.score
            # * cangraph.nodes[edge["source"]]["score"]
            # * cangraph.nodes[edge["target"]]["score"]
        )

    st = SteinerTree(
        tbl,
        cgraph,
        edge_probs=edge_probs,
        threshold=1e-7,
        additional_terminal_nodes=None,
    )
    pred_cg = st.get_result()

    sm = SemanticModel()
    idmap = {}
    for e in pred_cg.iter_edges():
        source = cgraph.get_node(e.source)
        target = cgraph.get_node(e.target)

        for node in [source, target]:
            if node.id not in idmap:
                if node.is_column_node:
                    assert node.column_index is not None
                    idmap[node.id] = sm.add_node(
                        DataNode(
                            col_index=node.column_index,
                            label=assert_not_null(
                                tbl.get_column_by_index(
                                    node.column_index
                                ).clean_multiline_name
                            ),
                        )
                    )
                else:
                    assert node.value is not None and node.is_class_node
                    idmap[node.id] = sm.add_node(
                        ClassNode(
                            abs_uri=node.value,
                            rel_uri=kgns.get_rel_uri(node.value),
                        )
                    )

        sm.add_edge(
            Edge(
                source=idmap[e.source],
                target=idmap[e.target],
                abs_uri=e.key,
                rel_uri=kgns.get_rel_uri(e.key),
            )
        )
    return sm


def save_training_data(
    ds: str, exs: list[Example[FullTable]], kgns: KnowledgeGraphNamespace
):
    outdir = PROJECT_DIR / f"data/training_set/{ds}"
    shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(parents=True)

    file_check = {}
    random.seed(54)

    for ex in exs:
        for col in ex.table.table.columns:
            stypes = {
                stype
                for sm in ex.sms
                for stype in sm.get_semantic_types_of_column(col.index)
            }
            colvalues = [
                v for v in col.values if v is not None and str(v).strip() != ""
            ]
            if len(colvalues) > 100:
                colvalues = random.sample(colvalues, 100)
            colvalues = "\n".join(str(x).replace("\n", "\\n") for x in colvalues)

            for stype in stypes:
                filepath = outdir / (
                    stype.class_rel_uri.split(":")[1]
                    + "__"
                    + stype.predicate_rel_uri.split(":")[1]
                    + ".txt"
                )

                semtype = f"{stype.class_rel_uri}---{stype.predicate_rel_uri}"

                if not filepath.exists():
                    with open(filepath, "w") as f:
                        f.write(semtype)
                        f.write("\n\n")
                    file_check[filepath] = semtype

                if filepath.exists() and filepath not in file_check:
                    with open(filepath, "r") as f:
                        line = f.readline().strip()
                        assert line == semtype
                    file_check[filepath] = semtype

                with open(filepath, "a") as f:
                    f.write("\n\n")
                    f.write("--------------------\n")
                    f.write(f"::{ex.id}::\n")
                    f.write(col.clean_name or "")
                    f.write("\n\n")
                    f.write(colvalues)


def make_training_data(
    project: str,
    kgns: KnowledgeGraphNamespace,
    sand_endpoint: str = "http://localhost:5524",
):
    # download project data
    resp = requests.get(sand_endpoint + "/api/project").json()
    project_id = None
    for record in resp["items"]:
        if record["name"] == project:
            project_id = record["id"]
            break
    assert project_id is not None

    resp = requests.get(sand_endpoint + f"/api/project/{project_id}/export")
    (PROJECT_DIR / f"data/training_set/{project}.zip").write_bytes(resp.content)

    # make dsl-like dataset
    examples = Dataset(PROJECT_DIR / f"data/training_set/{project}.zip").load()

    save_training_data(f"dsl-{project}", examples, kgns)


if __name__ == "__main__":
    make_training_data("minmod", MNDRNamespace.create())
