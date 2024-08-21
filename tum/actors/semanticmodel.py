from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

from drepr.models.prelude import (
    Alignment,
    Attr,
    CSVProp,
    DRepr,
    RangeAlignment,
    Resource,
    ResourceType,
)
from drepr.models.prelude import SemanticModel as DReprSemanticModel
from dsl.dsl import DSL
from dsl.generate_train_data import DefaultSemanticTypeComparator
from dsl.input import DSLTable
from hugedict.chained_mapping import ChainedMapping
from kgdata.models.ont_class import OntologyClass
from kgdata.models.ont_property import OntologyProperty
from loguru import logger
from rdflib import RDFS
from ream.actor_version import ActorVersion
from ream.actors.base import BaseActor
from ream.cache_helper import Cache, MemBackend
from ream.params_helper import NoParams
from sand_drepr.dreprmodel import get_drepr_model
from sm.dataset import Example, FullTable
from sm.misc.funcs import assert_not_null, assert_one_item
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.outputs.semantic_model import (
    ClassNode,
    DataNode,
    Edge,
    SemanticModel,
    SemanticType,
)

import tum.sm.dsl.main as dsl_main
from tum.actors.data import DataActor
from tum.actors.db import KGDB
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
MinmodTableTransformationActorArgs = NoParams


class MinmodGraphGenerationActor(BaseActor[MinmodGraphGenerationActorArgs]):
    VERSION = ActorVersion.create(110, [DSL])

    def __init__(self, params: MinmodGraphGenerationActorArgs, data_actor: DataActor):
        super().__init__(params, dep_actors=[data_actor])
        self.data_actor = data_actor
        self.kgdb = assert_one_item(list(data_actor.db_actor.kgdbs.values()))

    def __call__(self, table: FullTable):
        kgns = self.kgdb.kgns
        dsl = self.get_dsl()
        ex_stypes = dsl_main.get_semantic_types(dsl, table.table, top_n=2)
        return dsl_main.gen_can_graph(ex_stypes, kgns)

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
                (
                    kgns.get_abs_uri("mndr:MineralInventory"),
                    kgns.get_abs_uri("mndr:Reference"),
                ): {kgns.get_abs_uri("mndr:reference"): 1.0},
                (
                    kgns.get_abs_uri("mndr:Reference"),
                    kgns.get_abs_uri("mndr:Document"),
                ): {kgns.get_abs_uri("mndr:document"): 1.0},
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
        kgdb = self.data_actor.get_kgdb(self.params.train_dsquery)

        examples = dsl_main.get_training_data(self.params.train_dsquery, kgdb.kgns)

        db = kgdb.pydb
        classes = {}
        classes.update(db.get_default_classes())
        classes = ChainedMapping(db.classes.cache(), classes)

        props = {}
        props.update(db.get_default_props())
        props = ChainedMapping(db.props.cache(), props)

        dsl = DSL(
            examples,
            self.get_working_fs().get("dsl").get_or_create(),
            classes,
            props,
        )
        dsl.get_model(
            train_if_not_exist=True,
            save_train_data=True,
        )
        return dsl


class MinmodGraphInferenceActor(BaseActor[MinmodGraphInferenceActorArgs]):
    VERSION = 101

    def __init__(
        self,
        params: MinmodGraphInferenceActorArgs,
        cangraph_actor: MinmodGraphGenerationActor,
    ):
        super().__init__(params, dep_actors=[cangraph_actor])
        self.cangraph_actor = cangraph_actor
        self.data_actor = cangraph_actor.data_actor
        self.kgdb = cangraph_actor.kgdb

    def __call__(self, table: FullTable):
        cg = self.cangraph_actor(table)
        return dsl_main.pred_sm(table.table, cg, self.kgdb.kgns)


class MinmodTableTransformationActor(BaseActor[MinmodTableTransformationActorArgs]):
    VERSION = 100

    def __init__(self, params: NoParams, graphinfer_actor: MinmodGraphInferenceActor):
        super().__init__(params, [graphinfer_actor])
        self.graphinfer_actor = graphinfer_actor
        self.data_actor = graphinfer_actor.data_actor

    # def __call__(self, dsquery: str):
    #     pass

    def gen_drepr_model(self, table: FullTable, sm: SemanticModel, kgdb: KGDB) -> DRepr:
        return get_drepr_model(
            table_columns=[c.clean_multiline_name for c in table.table.columns],
            table_size=table.table.shape()[0],
            sm=sm,
            kgns=kgdb.kgns,
            kgns_prefixes=kgdb.kgns.prefix2ns.copy(),
            ontprop_ar=self.graphinfer_actor.cangraph_actor.get_props(),
            ident_props=[str(RDFS.label)],
        )
