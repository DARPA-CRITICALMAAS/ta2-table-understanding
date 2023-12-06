"""Sand Integration"""
import copy
from dataclasses import dataclass
from pathlib import Path

import rltk.similarity as sim
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
from sm.misc.funcs import identity_func
from sm.prelude import O

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
            id=ent.id,
            uri=ent.id,
            label=ent.label,
            aliases=ent.aliases,
            description=ent.description,
            properties={
                pid: [
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
    str(XSD.float): "number",
}


@dataclass
class WrappedOntProp(OntProperty):
    @staticmethod
    def from_kg_prop(obj: KGOntologyProperty):
        return WrappedOntProp(
            id=kgns.get_rel_uri(obj.id),
            uri=obj.id,
            label=obj.label,
            description=obj.description,
            aliases=obj.aliases,
            datatype=PropDataTypeMapping.get(obj.datatype, "unknown"),
            parents=[kgns.get_rel_uri(p) for p in obj.parents],
            ancestors={kgns.get_rel_uri(k): v for k, v in obj.ancestors.items()},
        )


def get_entity_db(dbfile: str):
    store = MNDRDB(Path(dbfile).parent).entities
    return StoreWrapper(
        store,
        key_deser=identity_func,
        val_deser=WrappedEntity.from_kg_entity,
    )


def get_ontclass_db(dbfile: str):
    store = MNDRDB(Path(dbfile).parent).classes
    return StoreWrapper(
        store,
        key_deser=identity_func,
        val_deser=WrappedOntClass.from_kg_class,
    )


def get_ontprop_db(dbfile: str):
    store = MNDRDB(Path(dbfile).parent).props
    return StoreWrapper(
        store,
        key_deser=identity_func,
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

    def predict(self, table: Table, rows: list[TableRow]):
        sm = O.SemanticModel()
        rows = copy.deepcopy(rows)
        return sm, rows

    def levenshtein(self, entity_mention: str, entity_label: str):
        return sim.levenshtein_similarity(entity_mention, entity_label)
