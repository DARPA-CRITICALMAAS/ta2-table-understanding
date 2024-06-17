from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property, lru_cache, partial
from pathlib import Path
from typing import cast

import pandas as pd
from kgdata.db import (
    GenericDB,
    deser_from_dict,
    make_get_rocksdb,
    ser_to_dict,
    small_dbopts,
)
from kgdata.dbpedia.datasets.entities import to_entity
from kgdata.dbpedia.datasets.ontology_dump import aggregated_triples
from kgdata.models.entity import Entity
from kgdata.models.multilingual import MultiLingualString, MultiLingualStringList
from kgdata.models.ont_class import OntologyClass
from kgdata.models.ont_property import OntologyProperty
from rdflib import OWL, RDF, RDFS, XSD, Graph, URIRef
from sm.namespaces.namespace import KnowledgeGraphNamespace
from sm.outputs.semantic_model import SemanticType

get_entity_db = make_get_rocksdb(
    ser_value=ser_to_dict,
    deser_value=partial(deser_from_dict, Entity),
    version=1,
    dbopts=small_dbopts,
)
get_class_db = make_get_rocksdb(
    ser_value=ser_to_dict,
    deser_value=partial(deser_from_dict, OntologyClass),
    version=1,
    dbopts=small_dbopts,
)
get_prop_db = make_get_rocksdb(
    ser_value=ser_to_dict,
    deser_value=partial(deser_from_dict, OntologyProperty),
    version=1,
    dbopts=small_dbopts,
)


@dataclass
class MetaProperty(OntologyProperty):
    expand_graph: list[tuple[str, str, str]]

    def get_equivalent_property(self) -> str:
        for edge in self.expand_graph:
            if edge[2] == "[target]":
                return edge[1]
        raise ValueError("Meta property must have one [target] marker")

    def get_target_semantic_type(self) -> tuple[str, str]:
        for edge in self.expand_graph:
            if edge[2] == "[target]":
                return edge[0], edge[1]
        raise ValueError("Meta property must have one [target] marker")


class MNDRDB(GenericDB):
    instance = None

    def __init__(self, database_dir: Path | str, read_only: bool = True):
        self.database_dir = Path(database_dir)
        self.read_only = read_only

    @staticmethod
    def init(database_dir: str | Path) -> MNDRDB:
        if MNDRDB.instance is not None:
            assert MNDRDB.instance.database_dir == Path(database_dir)
        else:
            MNDRDB.instance = MNDRDB(database_dir)
        return MNDRDB.instance

    @staticmethod
    def get_instance() -> MNDRDB:
        assert MNDRDB.instance is not None
        return MNDRDB.instance

    @cached_property
    def entities(self):
        return get_entity_db(
            self.database_dir / "entities.db", read_only=self.read_only
        )

    @cached_property
    def classes(self):
        return get_class_db(self.database_dir / "classes.db", read_only=self.read_only)

    @cached_property
    def props(self):
        return get_prop_db(self.database_dir / "props.db", read_only=self.read_only)

    def get_default_props(self):
        props = super().get_default_props()
        props.update(
            {
                "http://purl.org/drepr/1.0/unknown": OntologyProperty(
                    id="http://purl.org/drepr/1.0/unknown",
                    label=MultiLingualString.en("unknown"),
                    description=MultiLingualString.en("type of an column is unknown"),
                    aliases=MultiLingualStringList({"en": ["unknown"]}, "en"),
                    datatype=str(XSD.string),
                    parents=[],
                    related_properties=[],
                    equivalent_properties=[],
                    inverse_properties=[],
                    instanceof=[str(RDF.Property)],
                    ancestors={},
                    domains=[],
                    ranges=[],
                )
            }
        )
        return props

    def get_default_classes(self):
        return {
            "http://purl.org/drepr/1.0/Unknown": OntologyClass(
                id="http://purl.org/drepr/1.0/Unknown",
                label=MultiLingualString.en("Unknown"),
                description=MultiLingualString.en("type of an column is unknown"),
                aliases=MultiLingualStringList({"en": ["unknown"]}, "en"),
                parents=[],
                properties=[],
                different_froms=[],
                equivalent_classes=[],
                ancestors={},
            ),
            str(RDFS.Resource): OntologyClass(
                id=str(RDFS.Resource),
                label=MultiLingualString.en("Resource"),
                description=MultiLingualString.en("Resource"),
                aliases=MultiLingualStringList.en(["Resource", "Entity"]),
                parents=[],
                properties=[],
                different_froms=[],
                equivalent_classes=[],
                ancestors={},
            ),
        }

    def get_meta_properties(
        self, kgns: KnowledgeGraphNamespace, meta_prop_file: Path
    ) -> dict[str, OntologyProperty]:
        props = {}
        df = pd.read_csv(str(meta_prop_file))

        for _, row in df.iterrows():
            mndr = kgns.prefix2ns["mndr"]
            prop = MetaProperty(
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
                inverse_properties=[],
                instanceof=[],
                ancestors={},
                expand_graph=[
                    cast(
                        tuple[str, str, str],
                        (
                            [
                                (
                                    resource
                                    if resource in ["[source]", "[target]"]
                                    else kgns.get_abs_uri(resource)
                                )
                                for resource in edge.split("--")
                            ]
                        ),
                    )
                    for edge in row["graph"].split(",")
                ],
                domains=[],
                ranges=[],
            )
            prop.equivalent_properties.append(prop.get_equivalent_property())
            props[prop.id] = prop
        return props

    @classmethod
    @lru_cache()
    def parse_ontology(
        cls, ontology_file: Path
    ) -> tuple[
        dict[str, OntologyClass], dict[str, OntologyProperty], dict[str, Entity]
    ]:
        g = Graph()
        g.parse(ontology_file)

        classes = {}
        props = {}
        ents = {}

        # parse classes
        source2triples = defaultdict(list)
        for s, p, o in g:
            source2triples[s].append((s, p, o))

        resources = [
            aggregated_triples(x)
            for x in source2triples.items()
            if isinstance(x[0], URIRef)
        ]

        rdf_type = str(RDF.type)

        for resource in resources:
            ent = to_entity(resource, "en")

            (stmt,) = ent.props[rdf_type]
            if stmt.value in {RDF.Property, OWL.DatatypeProperty, OWL.ObjectProperty}:
                ranges = ent.props.get(str(RDFS.range), [])
                if len(ranges) == 0:
                    datatype = ""
                else:
                    if any(str(r.value).startswith(str(XSD)) for r in ranges):
                        assert len(ranges) == 1
                        datatype = str(ranges[0].value)
                    else:
                        # this is likely to be an object property
                        datatype = str(XSD.anyURI)
                props[ent.id] = OntologyProperty(
                    id=ent.id,
                    label=ent.label,
                    description=ent.description,
                    aliases=ent.aliases,
                    datatype=datatype,
                    parents=[],
                    related_properties=[],
                    equivalent_properties=[],
                    inverse_properties=[],
                    instanceof=[str(RDF.Property)],
                    ancestors={},
                    domains=[],
                    ranges=[],
                )
            elif stmt.value == RDFS.Class:
                classes[ent.id] = OntologyClass(
                    id=ent.id,
                    label=ent.label,
                    description=ent.description,
                    aliases=ent.aliases,
                    parents=[],
                    properties=[],
                    different_froms=[],
                    equivalent_classes=[],
                    ancestors={},
                )
            else:
                ents[ent.id] = ent

        return classes, props, ents
