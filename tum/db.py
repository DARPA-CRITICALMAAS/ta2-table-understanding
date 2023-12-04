from __future__ import annotations

from collections import defaultdict
from functools import cached_property, lru_cache, partial
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph

from kgdata.db import deser_from_dict, make_get_rocksdb, ser_to_dict, small_dbopts
from kgdata.dbpedia.datasets.entities import to_entity
from kgdata.dbpedia.datasets.ontology_dump import aggregated_triples
from kgdata.models.entity import Entity
from kgdata.models.ont_class import OntologyClass
from kgdata.models.ont_property import OntologyProperty

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


class MNDRDB:
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

    @classmethod
    @lru_cache()
    def parse_ontology(
        cls, ontology_file: Path
    ) -> tuple[
        dict[str, OntologyClass], dict[str, OntologyProperty], dict[str, Entity]
    ]:
        g = Graph()
        g.parse(ontology_file)

        source2triples = defaultdict(list)
        for s, p, o in g:
            source2triples[s].append((s, p, o))

        resources = [aggregated_triples(x) for x in source2triples.items()]
        classes = {}
        props = {}
        ents = {}

        rdf_type = str(RDF.type)

        for resource in resources:
            ent = to_entity(resource, "en")

            (stmt,) = ent.props[rdf_type]
            if stmt.value == RDF.Property:
                # TODO: improve me -- fix me!!!
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
                    subjects=[],
                    inverse_properties=[],
                    instanceof=[str(RDF.Property)],
                    ancestors={},
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
