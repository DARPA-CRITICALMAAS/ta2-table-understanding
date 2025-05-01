"""Sand Integration"""

from collections import ChainMap
from dataclasses import dataclass
from pathlib import Path

from dependency_injector.wiring import Provide
from kgdata.models.entity import Entity as KGEntity
from kgdata.models.ont_class import OntologyClass as KGOntologyClass
from kgdata.models.ont_property import OntologyProperty as KGOntologyProperty
from rdflib import RDF, XSD, Literal, URIRef
from sand.container import AppContainer
from sand.extensions.search.default_search import DefaultSearch
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
    str(XSD.int): "integer-number",
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
