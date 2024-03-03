from __future__ import annotations

from rdflib import OWL, RDF, RDFS, XSD
from sm.namespaces.namespace import DefaultKnowledgeGraphNamespace
from sm.namespaces.utils import register_kgns

MNDR = "mndr"
MNDR_NS = "https://minmod.isi.edu/resource/"
GEOKB = "geokb"
GEOKB_NS = "https://geokb.wikibase.cloud/entity/"
DREPR_NS = "http://purl.org/drepr/1.0/"


class MNDRNamespace(DefaultKnowledgeGraphNamespace):
    entity_id: str = str(RDFS.Resource)
    entity_uri: str = str(RDFS.Resource)
    entity_label: str = "rdfs:Resource"
    statement_uri: str = MNDR_NS + "Statement"
    main_namespaces: list[str] = [
        MNDR_NS,
        GEOKB_NS,
        str(RDF),
        str(RDFS),
        str(XSD),
        str(OWL),
        DREPR_NS,
    ]

    @classmethod
    def create(cls):
        return cls.from_prefix2ns(
            {
                MNDR: MNDR_NS,
                GEOKB: GEOKB_NS,
                "rdf": str(RDF),
                "rdfs": str(RDFS),
                "xsd": str(XSD),
                "owl": str(OWL),
                "drepr": DREPR_NS,
            }
        )

    def id_to_uri(self, id: str) -> str:
        if id.startswith("Q") or id.startswith("P"):
            return MNDR_NS + id
        return id


register_kgns(MNDR, MNDRNamespace.create())
