from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from ream.actors.dsid import IDDSActor
from ream.dataset_helper import DatasetList, E
from sm.dataset import Example, FullTable
from sm.namespaces.utils import KGName

from tum.actors.db import KGDB, DBActor


@dataclass
class DataActorArgs:
    skip_unk_ont_ent: bool = field(
        default=False,
        metadata={
            "help": "Skip examples with unknown ontology entities (e.g., Q1234567)"
        },
    )
    skip_no_sm: bool = field(
        default=False,
        metadata={"help": "Skip examples without semantic models"},
    )


@dataclass
class PredictionTargets:
    cea: list[tuple[int, int]]
    cta: list[int]
    cpa: list[tuple[int, int]]


class DataActor(IDDSActor[Example[FullTable], DataActorArgs]):
    VERSION = 107

    def __init__(
        self,
        params: DataActorArgs,
        db_actor: DBActor,
    ):
        super().__init__(params, [db_actor])
        self.db_actor = db_actor

    @classmethod
    @lru_cache()
    def get_kgname(cls, dsquery: str) -> KGName:
        if dsquery.startswith("wt") or dsquery.startswith("semtab2022_r1"):
            return KGName.Wikidata
        return KGName.Generic

    def get_kgdb(self, dsquery: str) -> KGDB:
        kgname = self.get_kgname(dsquery)
        return self.db_actor.kgdbs[kgname]

    def load_dataset(self, dsquery: str) -> DatasetList[E]:
        raise NotImplementedError()
