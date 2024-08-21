from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Mapping, TypeVar

import orjson
from kgdata.models.ont_class import OntologyClass
from kgdata.models.ont_property import OntologyProperty
from ream.helper import get_classpath
from sm.dataset import Example, FullTable
from sm.misc.funcs import import_func
from sm.misc.ray_helper import get_instance
from sm.outputs.semantic_model import SemanticModel
from tum.actors.db import KGDB, KGDBArgs
from tum.gpp.graph_space import GraphSpace
from tum.gpp.postprocessing.cgraph import CGraph


class ScoreSource(str, Enum):
    """Source of the estimated score"""

    # Estimated score from the semantic type prediction
    FROM_STYPE_MODEL = "from_stype_model"

    # Estimated score such as frequency from the KG mining
    FROM_KG_MINING = "from_kg_mining"


@dataclass(frozen=True)
class EstimatedScore:
    source: ScoreSource
    score: float

    @staticmethod
    def from_stype_model(score: float) -> EstimatedScore:
        return EstimatedScore(source=ScoreSource.FROM_STYPE_MODEL, score=score)

    @staticmethod
    def from_kg_mining(score: float) -> EstimatedScore:
        return EstimatedScore(source=ScoreSource.FROM_KG_MINING, score=score)


SemType = list[tuple[str, float]]
P = TypeVar("P")
ST = TypeVar(
    "ST",
    list[tuple[str, float]],
    tuple[SemType, SemType],
)


@dataclass
class CandidateGraph(Generic[P]):
    cg: CGraph
    # for tracking probabilities of nodes/edges in the graph
    cg_probs: P


@dataclass
class STypeAlgoInitArgs:
    clspath: str
    initargs: str

    def serialize(self):
        return orjson.dumps(
            {
                "clspath": self.clspath,
                "initargs": self.initargs,
            }
        ).decode("utf-8")


class STypeAlgorithm(Generic[ST, P], ABC):
    """Algorithm for generating candidate graphs and semantic models given predicted semantic types"""

    def get_init_args(self):
        return STypeAlgoInitArgs(
            get_classpath(self.__class__),
            orjson.dumps(self.__dict__).decode("utf-8"),
        )

    def serialize(self):
        return self.get_init_args().serialize()

    @staticmethod
    def get_instance(algo: STypeAlgorithm | STypeAlgoInitArgs):
        if isinstance(algo, STypeAlgorithm):
            return algo
        else:
            return get_instance(
                lambda: import_func(algo.clspath)(**orjson.loads(algo.initargs)),
                f"{algo.clspath}:{algo.initargs}",
            )

    @abstractmethod
    def get_candidate_graph(
        self,
        ex: Example[FullTable],
        ex_stypes: dict[int, ST],
        ent_cols: set[int],
        classes: Mapping[str, OntologyClass],
        props: Mapping[str, OntologyProperty],
        graphspace: GraphSpace,
    ) -> CandidateGraph[P]:
        """Get a candidate graph"""

    @abstractmethod
    def get_semantic_model(
        self,
        ex: Example[FullTable],
        cangraph: CandidateGraph[P],
        kgdb: KGDB | KGDBArgs,
    ) -> SemanticModel:
        """Get a semantic model out of the candidate graph"""
