from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dsl.dsl import DSL
from dsl.generate_train_data import DefaultSemanticTypeComparator
from dsl.input import DSLTable
from hugedict.chained_mapping import ChainedMapping
from kgdata.models.ont_class import OntologyClass
from kgdata.models.ont_property import OntologyProperty
from loguru import logger
from ream.actor_version import ActorVersion
from ream.actors.base import BaseActor
from ream.cache_helper import Cache, MemBackend
from ream.params_helper import NoParams
from sm.dataset import Example, FullTable
from sm.misc.funcs import assert_not_null
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.outputs.semantic_model import (
    ClassNode,
    DataNode,
    Edge,
    SemanticModel,
    SemanticType,
)

from tum.actors.data import DataActor
from tum.db import MetaProperty
from tum.lib.cgraph import CGraph
from tum.lib.graph_generation import GraphGeneration
from tum.lib.steiner_tree import SteinerTree
from tum.misc import SemanticTypePrediction


@dataclass
class MinmodGraphGenerationActorArgs:
    train_dsquery: str
    meta_prop_file: Path
    top_n_stypes: int = 4


MinmodGraphInferenceActorArgs = NoParams
MinmodCanGraphExtractedResult = CGraph


class MinmodGraphGenerationActor(BaseActor[MinmodGraphGenerationActorArgs]):
    VERSION = ActorVersion.create(108, [DSL])

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
                        [
                            SemanticTypePrediction(
                                stype.semantic_type,
                                stype.score,
                                col.index,
                            )
                            for stype in example_stypes[ei][ci]
                        ]
                        for ci, col in enumerate(ex.table.table.columns)
                    ],
                    kgns,
                )
            )

        return output

    def gen_graph(
        self,
        ex: Example[FullTable],
        ex_stypes: list[list[SemanticTypePrediction]],
        kgns: KnowledgeGraphNamespace,
    ) -> MinmodCanGraphExtractedResult:
        gen = GraphGeneration(
            {
                kgns.get_abs_uri("mndr:MineralSite"): 1,
                kgns.get_abs_uri("mndr:LocationInfo"): 1,
                kgns.get_abs_uri("mndr:MineralInventory"): 1,
                kgns.get_abs_uri("mndr:Grade"): None,
                kgns.get_abs_uri("mndr:Ore"): 1,
            },
            {
                (
                    kgns.get_abs_uri("mndr:MineralSite"),
                    kgns.get_abs_uri("mndr:MineralInventory"),
                ): {kgns.get_abs_uri("mndr:mineral_inventory"): 1.0},
                (
                    kgns.get_abs_uri("mndr:MineralSite"),
                    kgns.get_abs_uri("mndr:LocationInfo"),
                ): {kgns.get_abs_uri("mndr:location_info"): 1.0},
                (
                    kgns.get_abs_uri("mndr:MineralInventory"),
                    kgns.get_abs_uri("mndr:Grade"),
                ): {kgns.get_abs_uri("mndr:grade"): 1.0},
                (
                    kgns.get_abs_uri("mndr:MineralInventory"),
                    kgns.get_abs_uri("mndr:Ore"),
                ): {kgns.get_abs_uri("mndr:ore"): 1.0},
            },
        )
        cg = gen(ex_stypes)
        logger.info(
            "Candidate Graph with: {} nodes and {} edges",
            cg.num_nodes(),
            cg.num_edges(),
        )
        return cg

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

        props = {}
        props.update(db.default_props)
        props.update(db.get_meta_properties(kgdb.kgns, self.params.meta_prop_file))
        props = ChainedMapping(db.props.cache(), props)

        dsl = DSL(
            examples,
            self.get_working_fs().get("dsl").get_or_create(),
            db.classes,
            props,
        )
        dsl.get_model(
            train_if_not_exist=True,
            stype_cmp=SemanticTypeMetaComparator(db.classes, props, kgdb.kgns),
            save_train_data=True,
        )
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
        cgraph: MinmodCanGraphExtractedResult,
        kgns: KnowledgeGraphNamespace,
    ):
        edge_probs = {}
        for edge in cgraph.iter_edges():
            edge_probs[(edge.source, edge.target, edge.key)] = (
                edge.score
                # * cangraph.nodes[edge["source"]]["score"]
                # * cangraph.nodes[edge["target"]]["score"]
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
                                    ex.table.table.get_column_by_index(
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


class SemanticTypeMetaComparator(DefaultSemanticTypeComparator):
    def __init__(
        self,
        classes: Mapping[str, OntologyClass],
        props: Mapping[str, OntologyProperty],
        kgns: KnowledgeGraphNamespace,
    ):
        super().__init__(classes, props)
        self.kgns = kgns

    def __call__(self, stype1: SemanticType, stype2: SemanticType):
        score = super().__call__(stype1, stype2)
        if score == 1.0:
            return score

        stype1_prop = self.props[stype1.predicate_abs_uri]
        stype2_prop = self.props[stype2.predicate_abs_uri]

        need_recal = False

        if isinstance(stype1_prop, MetaProperty):
            newstype = stype1_prop.get_target_semantic_type()
            stype1 = SemanticType(
                class_abs_uri=newstype[0],
                class_rel_uri=self.kgns.get_rel_uri(newstype[0]),
                predicate_abs_uri=newstype[1],
                predicate_rel_uri=self.kgns.get_rel_uri(newstype[1]),
            )
            need_recal = True

        if isinstance(stype2_prop, MetaProperty):
            newstype = stype2_prop.get_target_semantic_type()
            stype2 = SemanticType(
                class_abs_uri=newstype[0],
                class_rel_uri=self.kgns.get_rel_uri(newstype[0]),
                predicate_abs_uri=newstype[1],
                predicate_rel_uri=self.kgns.get_rel_uri(newstype[1]),
            )
            need_recal = True

        if need_recal:
            score = max(score, self.__call__(stype1, stype2))
        return score
