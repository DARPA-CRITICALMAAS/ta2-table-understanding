from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dsl.dsl import DSL
from dsl.input import DSLTable
from hugedict.chained_mapping import ChainedMapping
from kgdata.models.multilingual import MultiLingualString, MultiLingualStringList
from kgdata.models.ont_property import OntologyProperty
from ream.actors.base import BaseActor
from ream.cache_helper import Cache, MemBackend
from ream.params_helper import NoParams
from sm.dataset import Example, FullTable
from sm.misc.funcs import group_by
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.outputs.semantic_model import (
    ClassNode,
    DataNode,
    Edge,
    SemanticModel,
    SemanticType,
)

from tum.actors.data import DataActor
from tum.lib.cgraph import BaseEdge, CGNode, CGraph
from tum.lib.steiner_tree import SteinerTree


@dataclass
class MinmodGraphGenerationActorArgs:
    train_dsquery: str
    meta_prop_file: Path
    top_n_stypes: int = 4


MinmodGraphInferenceActorArgs = NoParams


@dataclass
class MinmodCanGraphExtractedResult:
    nodes: dict[str, dict]
    edges: list[dict]


@dataclass
class SemanticTypePrediction:
    stype: SemanticType
    score: float
    column: int


class MinmodGraphGenerationActor(BaseActor[MinmodGraphGenerationActorArgs]):
    VERSION = 103

    def __init__(self, params: MinmodGraphGenerationActorArgs, data_actor: DataActor):
        super().__init__(params, dep_actors=[data_actor])
        self.data_actor = data_actor

    def __call__(self, dsquery: str):
        kgns = self.data_actor.get_kgdb(dsquery).kgns

        examples = self.data_actor(dsquery)

        example_stypes = self.get_dsl()(
            [ex.replace_table(DSLTable.from_full_table(ex.table)) for ex in examples],
            top_n=self.params.top_n_stypes,
        )

        output: list[MinmodCanGraphExtractedResult] = []
        for ei, ex in enumerate(examples):
            output.append(
                self.gen_graph(
                    ex,
                    [
                        SemanticTypePrediction(
                            (s := example_stypes[ei][ci][0]).semantic_type,
                            s.score,
                            col.index,
                        )
                        for ci, col in enumerate(ex.table.table.columns)
                    ],
                    kgns,
                )
            )

        return output

    def gen_graph(
        self,
        ex: Example[FullTable],
        ex_stypes: list[SemanticTypePrediction],
        kgns: KnowledgeGraphNamespace,
    ):
        cls2types = group_by(ex_stypes, lambda stype: stype.stype.class_abs_uri)

        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        mineral_site = kgns.get_abs_uri("mndr:MineralSite")

        if mineral_site in cls2types:
            source_id = mineral_site + ":0"
            nodes[source_id] = {
                "id": source_id,
                "uri": mineral_site,
                "score": max(stype.score for stype in cls2types[mineral_site]),
            }
            for stype in cls2types.pop(mineral_site):
                target_id = f"col:{stype.column}"
                nodes[target_id] = {
                    "id": target_id,
                    "col_index": stype.column,
                    "label": ex.table.table.columns[stype.column].clean_multiline_name,
                    "score": 1.0,
                }
                edges.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "predicate": stype.stype.predicate_abs_uri,
                        "score": stype.score,
                    }
                )

        mineral_inventory = kgns.get_abs_uri("mndr:MineralInventory")
        if mineral_inventory in cls2types:
            # TODO: fix me -- infer this list
            key_props = {
                kgns.get_abs_uri(reluri)
                for reluri in [
                    "mndr:grade",
                    "mndr:p_grade_zn",
                    "mndr:p_grade_pb",
                    "mndr:p_grade_ag",
                ]
            }
            inventory_props = cls2types.pop(mineral_inventory)
            node_inventories = {}
            for i, stype in enumerate(inventory_props):
                if stype.stype.predicate_abs_uri not in key_props:
                    continue
                source_id = mineral_inventory + f":{i}"
                target_id = f"col:{stype.column}"
                node_inventories[source_id] = {
                    "id": source_id,
                    "uri": mineral_inventory,
                    "score": stype.score,
                }
                nodes[target_id] = {
                    "id": target_id,
                    "col_index": stype.column,
                    "label": ex.table.table.columns[stype.column].clean_multiline_name,
                    "score": 1.0,
                }
                edges.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "predicate": stype.stype.predicate_abs_uri,
                        "score": stype.score,
                    }
                )
            nodes.update(node_inventories)

            for i, stype in enumerate(inventory_props):
                if stype.stype.predicate_abs_uri in key_props:
                    continue

                target_id = f"col:{stype.column}"
                if target_id not in nodes:
                    nodes[target_id] = {
                        "id": target_id,
                        "col_index": stype.column,
                        "label": ex.table.table.columns[
                            stype.column
                        ].clean_multiline_name,
                        "score": 1.0,
                    }

                for source_id in node_inventories:
                    edges.append(
                        {
                            "source": source_id,
                            "target": target_id,
                            "predicate": stype.stype.predicate_abs_uri,
                            "score": stype.score,
                        }
                    )

        sources = [
            node for node in nodes.values() if node.get("uri", None) == mineral_site
        ]
        targets = [
            node
            for node in nodes.values()
            if node.get("uri", None) == mineral_inventory
        ]
        for source in sources:
            for target in targets:
                edges.append(
                    {
                        "source": source["id"],
                        "target": target["id"],
                        "predicate": kgns.get_abs_uri("mndr:mineral_inventory"),
                        "score": 1.0,
                    }
                )

        return MinmodCanGraphExtractedResult(nodes, edges)

    @Cache.cache(backend=MemBackend())
    def get_dsl(self):
        """Get a trained DSL model for the given dataset query."""
        examples = self.data_actor(self.params.train_dsquery)
        examples = [
            Example(id=ex.id, sms=ex.sms, table=DSLTable.from_full_table(ex.table))
            for ex in examples
        ]

        kgdb = self.data_actor.get_kgdb(self.params.train_dsquery)
        db = kgdb.pydb

        # TODO: fix me.
        df = pd.read_csv(str(self.params.meta_prop_file))
        props = {}
        props.update(db.default_props)

        for _, row in df.iterrows():
            mndr = kgdb.kgns.prefix2ns["mndr"]
            props[mndr + row["id"]] = OntologyProperty(
                id=mndr + row["id"],
                label=MultiLingualString.en(row["label"]),
                description=MultiLingualString.en(row["description"]),
                aliases=MultiLingualStringList.en(
                    [str(x).strip() for x in row["aliases"].split("|")]
                ),
                datatype="",
                parents=[],
                related_properties=[],
                equivalent_properties=[],
                subjects=[],
                inverse_properties=[],
                instanceof=[],
                ancestors={},
            )

        dsl = DSL(
            examples,
            self.get_working_fs().get("dsl").get_or_create(),
            db.classes,
            ChainedMapping(db.props.cache(), props),
        )
        dsl.get_model(train_if_not_exist=True)
        return dsl


class MinmodGraphInferenceActor(BaseActor[MinmodGraphInferenceActorArgs]):
    def __init__(
        self,
        params: MinmodGraphInferenceActorArgs,
        cangraph_actor: MinmodGraphGenerationActor,
    ):
        super().__init__(params, dep_actors=[cangraph_actor])
        self.cangraph_actor = cangraph_actor
        self.data_actor = cangraph_actor.data_actor

    def __call__(self, dsquery: str):
        examples = self.data_actor(dsquery)
        cangraphs = self.cangraph_actor(dsquery)
        kgns = self.data_actor.get_kgdb(dsquery).kgns

        return [
            self.predict_sm(ex, cangraphs[ei], kgns) for ei, ex in enumerate(examples)
        ]

    def predict_sm(
        self,
        ex: Example[FullTable],
        cangraph: MinmodCanGraphExtractedResult,
        kgns: KnowledgeGraphNamespace,
    ):
        cgraph = CGraph()
        for node in cangraph.nodes.values():
            cgraph.add_node(
                CGNode(
                    id=node["id"],
                    is_statement_node=False,
                    is_column_node="col_index" in node,
                    is_entity_node=False,
                    is_literal_node=False,
                    is_in_context=False,
                    column_index=node.get("col_index", None),
                )
            )

        edge_probs = {}
        for edge in cangraph.edges:
            cgraph.add_edge(
                BaseEdge(
                    id=-1,
                    source=edge["source"],
                    target=edge["target"],
                    key=edge["predicate"],
                )
            )
            edge_probs[(edge["source"], edge["target"], edge["predicate"])] = (
                edge["score"]
                * cangraph.nodes[edge["source"]]["score"]
                * cangraph.nodes[edge["target"]]["score"]
            )

        st = SteinerTree(
            ex.table,
            cgraph,
            edge_probs=edge_probs,
            threshold=0.0,
            additional_terminal_nodes=None,
        )
        pred_cg = st.get_result()

        sm = SemanticModel()
        idmap = {}
        for e in pred_cg.iter_edges():
            source = cangraph.nodes[e.source]
            target = cangraph.nodes[e.target]

            for node in [source, target]:
                if node["id"] not in idmap:
                    if "col_index" in node:
                        idmap[node["id"]] = sm.add_node(
                            DataNode(
                                col_index=node["col_index"],
                                label=node["label"],
                            )
                        )
                    else:
                        assert "uri" in node
                        idmap[node["id"]] = sm.add_node(
                            ClassNode(
                                abs_uri=node["uri"],
                                rel_uri=kgns.get_rel_uri(node["uri"]),
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
