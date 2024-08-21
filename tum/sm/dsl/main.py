from __future__ import annotations

from dsl.dsl import DSL, DSLTable
from loguru import logger
from sm.dataset import Example
from sm.inputs.table import Column, ColumnBasedTable
from sm.misc.funcs import assert_not_null
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.outputs.semantic_model import (
    ClassNode,
    DataNode,
    Edge,
    SemanticModel,
    SemanticType,
)

from tum.config import PROJECT_DIR
from tum.lib.cgraph import CGraph
from tum.lib.graph_generation import GraphGeneration
from tum.lib.steiner_tree import SteinerTree
from tum.misc import SemanticTypePrediction

DREPR_UNK = "http://purl.org/drepr/1.0/Unknown"


def get_training_data(ds: str, kgns: KnowledgeGraphNamespace):
    examples = []
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
                assert chunk[1] == ""
                tbl = DSLTable.from_column_based_table(
                    ColumnBasedTable(
                        table_id=f"{file.stem}--{i}",
                        columns=[Column(index=0, name=chunk[0], values=chunks[2:])],
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


def get_semantic_types(dsl: DSL, table: ColumnBasedTable, top_n: int):
    ex = Example(
        id=table.table_id, table=DSLTable.from_column_based_table(table), sms=[]
    )

    stypes = dsl([ex], top_n=top_n)[0]
    return [
        [
            SemanticTypePrediction(
                stype.semantic_type,
                stype.score,
                col.index,
            )
            for stype in stypes[ci]
        ]
        for ci, col in enumerate(ex.table.table.columns)
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
