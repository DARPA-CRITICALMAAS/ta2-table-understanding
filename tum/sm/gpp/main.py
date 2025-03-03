from __future__ import annotations

from typing import Any, Mapping

from kgdata.models import Ontology
from kgdata.models.ont_class import OntologyClass
from kgdata.models.ont_property import OntologyProperty
from libactor.typing import NoneType
from loguru import logger
from sm.dataset import Example, FullTable, SemanticModel
from sm.outputs.semantic_model import SemanticType
from tum.lib.graph_generation import GraphGeneration
from tum.misc import SemanticTypePrediction
from tum.sm.dsl.main import gen_can_graph, pred_sm

from gpp.actors.graph_space_actor import GraphSpace
from gpp.sem_model.from_sem_label import ISemModel
from gpp.sem_model.from_sem_label._algo_base import CandidateGraph, SemType
from gpp.sem_model.from_sem_label.algo_v300 import V200CGProbs


class TumGppSemModelAlgo(ISemModel[tuple[SemType, SemType], Any]):

    def get_candidate_graph(
        self,
        ex: Example[FullTable],
        ex_stypes: dict[int, tuple[SemType, SemType]],
        ent_cols: set[int],
        ontology: Ontology,
        graphspace: GraphSpace,
    ) -> CandidateGraph[Any]:
        """Get a candidate graph"""
        cangraph = gen_can_graph(
            [
                [
                    SemanticTypePrediction(
                        stype=SemanticType(
                            class_abs_uri=(
                                curi := ontology.kgns.id_to_uri(
                                    ontology.props[propid].domains[0]
                                )
                            ),
                            class_rel_uri=ontology.kgns.get_rel_uri(curi),
                            predicate_abs_uri=(
                                puri := ontology.kgns.id_to_uri(
                                    ontology.props[propid].id
                                )
                            ),
                            predicate_rel_uri=ontology.kgns.get_rel_uri(puri),
                        ),
                        score=score,
                        col_index=ci,
                        col_name=ex.table.table.get_column_by_index(ci).clean_name
                        or "",
                    )
                    for propid, score in ptypes
                ]
                for ci, (_, ptypes) in ex_stypes.items()
            ],
            ontology.kgns,
        )
        return CandidateGraph(cangraph, None)  # type: ignore

    def get_semantic_model(
        self,
        ex: Example[FullTable],
        cangraph: CandidateGraph[Any],
        ontology: Ontology,
    ) -> SemanticModel:
        """Get a semantic model out of the candidate graph"""
        sm = pred_sm(ex.table.table, cangraph.cg, ontology.kgns)  # type: ignore
        return sm
