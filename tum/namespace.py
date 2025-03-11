from __future__ import annotations

from rdflib import OWL, RDF, RDFS, SKOS, XSD

from sm.namespaces.namespace import DefaultKnowledgeGraphNamespace
from sm.namespaces.utils import register_kgns

MNR = "mnr"
MNR_NS = "https://minmod.isi.edu/resource/"
MNO = "mno"
MNO_NS = "https://minmod.isi.edu/ontology/"
MOS = "mos"
MOS_NS = "https://minmod.isi.edu/ontology-simple/"

GEMR = "gemr"
GEMR_NS = "https://geochemistry.isi.edu/resource/"
GEMO = "gemo"
GEMO_NS = "https://geochemistry.isi.edu/ontology/"

GEOKB = "geokb"
GEOKB_NS = "https://geokb.wikibase.cloud/entity/"
DREPR_NS = "http://purl.org/drepr/1.0/"


class MNDRNamespace(DefaultKnowledgeGraphNamespace):
    entity_id: str = str(RDFS.Resource)
    entity_uri: str = str(RDFS.Resource)
    entity_label: str = "rdfs:Resource"
    statement_uri: str = MNR_NS + "Statement"
    main_namespaces: list[str] = [
        MNO_NS,
        MOS_NS,
        MNR_NS,
        GEMR_NS,
        GEMO_NS,
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
                MNR: MNR_NS,
                MNO: MNO_NS,
                MOS: MOS_NS,
                GEOKB: GEOKB_NS,
                GEMR: GEMR_NS,
                GEMO: GEMO_NS,
                "rdf": str(RDF),
                "rdfs": str(RDFS),
                "xsd": str(XSD),
                "owl": str(OWL),
                "skos": str(SKOS),
                "geo": "http://www.opengis.net/ont/geosparql#",
                "drepr": DREPR_NS,
            }
        )

    def id_to_uri(self, id: str) -> str:
        return self.get_abs_uri(id)

    def uri_to_id(self, uri: str) -> str:
        return self.get_rel_uri(uri)


register_kgns(MNR, MNDRNamespace.create())
