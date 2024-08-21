"""Sand Integration"""

import copy
from collections import ChainMap, defaultdict
from dataclasses import dataclass
from pathlib import Path

import rltk.similarity as sim
import serde.csv
from dependency_injector.wiring import Provide
from kgdata.models.entity import Entity as KGEntity
from kgdata.models.ont_class import OntologyClass as KGOntologyClass
from kgdata.models.ont_property import OntologyProperty as KGOntologyProperty
from rdflib import RDF, RDFS, XSD, Literal, URIRef
from sand.container import AppContainer
from sand.extension_interface.assistant import IAssistant
from sand.extensions.search.default_search import DefaultSearch
from sand.extensions.wikidata import WD_DATATYPE_MAPPING
from sand.helpers.dependency_injection import autoinject
from sand.models.base import StoreWrapper
from sand.models.entity import Entity, EntityAR, Statement, Value
from sand.models.ontology import (
    OntClass,
    OntClassAR,
    OntProperty,
    OntPropertyAR,
    OntPropertyDataType,
)
from sand.models.table import CandidateEntity, Link, Table, TableRow
from sm.dataset import Dataset, Example, FullTable
from sm.misc.funcs import identity_func
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.prelude import I, M, O

from tum.db import MNDRDB
from tum.namespace import MNDRNamespace

kgns = MNDRNamespace.create()


@dataclass
class WrappedEntity(Entity):
    @property
    def instanceof(self):
        return str(RDF.type)

    @staticmethod
    def from_kg_entity(ent: KGEntity):
        return WrappedEntity(
            id=kgns.get_rel_uri(ent.id),
            uri=ent.id,
            label=ent.label,
            aliases=ent.aliases,
            description=ent.description,
            properties={
                kgns.get_rel_uri(pid): [
                    Statement(
                        value=value_deser(stmt.value),
                        qualifiers={
                            qid: [value_deser(x) for x in lst]
                            for qid, lst in stmt.qualifiers.items()
                        },
                        qualifiers_order=stmt.qualifiers_order,
                    )
                    for stmt in stmts
                ]
                for pid, stmts in ent.props.items()
            },
        )


@dataclass
class WrappedOntClass(OntClass):
    @staticmethod
    def from_kg_class(obj: KGOntologyClass):
        return WrappedOntClass(
            id=kgns.get_rel_uri(obj.id),
            uri=obj.id,
            label=obj.label,
            description=obj.description,
            aliases=obj.aliases,
            parents=[kgns.get_rel_uri(p) for p in obj.parents],
            ancestors={kgns.get_rel_uri(k): v for k, v in obj.ancestors.items()},
        )


PropDataTypeMapping: dict[str, OntPropertyDataType] = {
    str(XSD.anyURI): "entity",
    str(XSD.string): "string",
    str(XSD.float): "decimal-number",
    str(XSD.integer): "integer-number",
}


@dataclass
class WrappedOntProp(OntProperty):
    @staticmethod
    def from_kg_prop(obj: KGOntologyProperty):
        return WrappedOntProp(
            id=kgns.uri_to_id(obj.id),
            uri=obj.id,
            label=obj.label,
            description=obj.description,
            aliases=obj.aliases,
            datatype=PropDataTypeMapping.get(obj.datatype, "unknown"),
            parents=[kgns.uri_to_id(p) for p in obj.parents],
            ancestors={kgns.uri_to_id(k): v for k, v in obj.ancestors.items()},
        )


def get_entity_db(dbfile: str):
    db = MNDRDB(Path(dbfile).parent)
    store = db.entities
    return StoreWrapper(
        store,
        key_deser=kgns.get_abs_uri,
        val_deser=WrappedEntity.from_kg_entity,
    )


def get_ontclass_db(dbfile: str):
    db = MNDRDB(Path(dbfile).parent)
    store = ChainMap(db.get_default_classes(), db.classes)
    return StoreWrapper(
        store,
        key_deser=kgns.get_abs_uri,
        val_deser=WrappedOntClass.from_kg_class,
    )


def get_ontprop_db(dbfile: str):
    db = MNDRDB(Path(dbfile).parent)
    store = ChainMap(db.get_default_props(), db.props)
    return StoreWrapper(
        store,
        key_deser=kgns.get_abs_uri,
        val_deser=WrappedOntProp.from_kg_prop,
    )


@autoinject
def dummy_search(
    entities: EntityAR = Provide[AppContainer.entities],
    classes: OntClassAR = Provide[AppContainer.classes],
    props: OntPropertyAR = Provide[AppContainer.properties],
):
    return DefaultSearch(entities, classes, props)


def value_deser(val: URIRef | Literal):
    if isinstance(val, URIRef):
        if kgns.is_uri_in_main_ns(val):
            return Value(type="entityid", value=kgns.uri_to_id(val))
        return Value(type="entityid", value=val)
    else:
        # TODO: fix me, treat everything as string...
        return Value(type="string", value=str(val))


class GramsMinModAssistant(IAssistant):
    @autoinject
    def __init__(
        self,
        entities: EntityAR = Provide[AppContainer.entities],
        classes: OntClassAR = Provide[AppContainer.classes],
        props: OntPropertyAR = Provide[AppContainer.properties],
    ):
        self.entities = entities
        self.classes = classes
        self.props = props

        from sm.namespaces.utils import KGName

        from tum.actors.entry import (
            DataActorArgs,
            DBActorArgs,
            G,
            KGDBArgs,
            MinmodGraphGenerationActorArgs,
            MinmodGraphInferenceActorArgs,
            MinmodTableTransformationActor,
        )
        from tum.config import CRITICAL_MAAS_DIR

        self.meta_prop_file = (
            CRITICAL_MAAS_DIR / "ta2-table-understanding/data/meta_property/data.csv"
        )

        self.actor = G.create_actor(
            MinmodTableTransformationActor,
            [
                DBActorArgs(
                    kgdbs=[
                        KGDBArgs(
                            name=KGName.Generic,
                            version="20231130",
                            datadir=CRITICAL_MAAS_DIR / "data/databases",
                        )
                    ]
                ),
                DataActorArgs(skip_unk_ont_ent=True, skip_no_sm=True),
                MinmodGraphGenerationActorArgs(
                    train_dsquery="dsl-semtype",
                    meta_prop_file=self.meta_prop_file,
                    top_n_stypes=2,
                ),
                MinmodGraphInferenceActorArgs(),
            ],
        )

    def predict(self, table: Table, rows: list[TableRow]):
        full_table = self.convert_table(table, rows)
        sm = self.actor.graphinfer_actor(full_table)
        rows = copy.deepcopy(rows)
        return sm, rows

    def levenshtein(self, entity_mention: str, entity_label: str):
        return sim.levenshtein_similarity(entity_mention, entity_label)

    def convert_table(self, table: Table, rows: list[TableRow]) -> FullTable:
        newtbl = I.ColumnBasedTable(
            f"p{table.project_id}-t:{table.id}-{table.name}",
            columns=[
                I.Column(index=ci, name=col, values=[row.row[ci] for row in rows])
                for ci, col in enumerate(table.columns)
            ],
        )
        links = M.Matrix.default(newtbl.shape(), list)
        return FullTable(
            table=newtbl,
            context=I.Context(),
            links=links,
        )
