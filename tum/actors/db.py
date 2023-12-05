from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Optional, Sequence, TypeAlias, Union

from kgdata.db import GenericDB
from kgdata.wikidata.db import WikidataDB
from ream.actors.base import BaseActor
from sm.misc.ray_helper import get_instance
from sm.namespaces.utils import KGName, get_kgns, register_kgns

from tum.namespace import MNDRNamespace


@dataclass
class KGDBArgs:
    name: KGName
    version: str
    datadir: Path
    entity_url: Optional[str] = None
    entity_metadata_url: Optional[str] = None
    entity_batch_size: int = 64
    entity_metadata_batch_size: int = 128

    def to_dict(self):
        return {"name": self.name, "version": self.version}

    def get_entity_urls(self) -> list[str]:
        return self.get_urls(self.entity_url)

    def get_entity_metadata_urls(self) -> list[str]:
        return self.get_urls(self.entity_metadata_url)

    def get_urls(self, pattern: Optional[str]) -> list[str]:
        if pattern is None:
            return []
        ((begin, end),) = re.findall(r"(\d+)-(\d+)", pattern)
        template = pattern.replace(f"{begin}-{end}", "{}")
        return [template.format(i) for i in range(int(begin), int(end))]


@dataclass
class DBActorArgs:
    kgdbs: Sequence[KGDBArgs]

    def __post_init__(self):
        self.kgdbs = sorted(self.kgdbs, key=lambda db: db.name)
        assert len(set(db.name for db in self.kgdbs)) == len(
            self.kgdbs
        ), "Should not have duplicated KGs"

    def to_dict(self):
        return [{"name": kgdb.name, "version": kgdb.version} for kgdb in self.kgdbs]


class DBActor(BaseActor[DBActorArgs]):
    VERSION = 100

    def __init__(self, params: DBActorArgs):
        super().__init__(params, [])
        self.kgdbs: Mapping[KGName, KGDB] = {
            kgdb.name: KGDB.get_instance(kgdb) for kgdb in params.kgdbs
        }


PyKGDB: TypeAlias = Union[GenericDB, WikidataDB]


@dataclass
class KGDB:
    args: KGDBArgs

    @cached_property
    def kgns(self):
        return get_kgns(self.args.name)

    @cached_property
    def pydb(self) -> PyKGDB:
        if self.args.name == KGName.Wikidata:
            return WikidataDB(self.args.datadir)
        elif self.args.name == KGName.Generic:
            return GenericDB(self.args.datadir)
        else:
            raise NotImplementedError()

    @staticmethod
    def get_instance(db: KGDB | KGDBArgs) -> KGDB:
        if isinstance(db, KGDB):
            return db
        return get_instance(lambda: KGDB(db), f"{db.name}:{db.version}:{db.datadir}")


register_kgns(KGName.Generic, MNDRNamespace.create())
