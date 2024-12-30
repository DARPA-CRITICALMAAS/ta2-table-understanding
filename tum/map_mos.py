from __future__ import annotations

import glob
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional

import rdflib.term
import serde.json
import typer
from minmodkg.entity_linking import EntityLinking, IEntityLinking
from rdflib import RDF, RDFS, XSD, Graph, Namespace, URIRef
from slugify import slugify
from sm.misc.funcs import assert_isinstance
from tqdm.auto import tqdm
from tum.config import CRITICAL_MAAS_DIR
from tum.lib.unit_and_commodity import (
    CommodityCompatibleLinker,
    UnitAndCommodityTrustedLinker,
    UnitCompatibleLinker,
)

mos = Namespace("https://minmod.isi.edu/ontology-simple/")
mnr = Namespace("https://minmod.isi.edu/resource/")
app = typer.Typer(pretty_exceptions_short=True, pretty_exceptions_enable=False)
JsonValue = str | int | float | bool


class MosMapping:
    """Mapping from the simple ontology to the full ontology"""

    def __init__(self, g: Graph):
        self.g = g

        predefined_ent_dir = CRITICAL_MAAS_DIR / "kgdata/data/predefined-entities"

        self.country_linker = EntityLinking.get_instance(predefined_ent_dir, "country")
        self.state_or_province_linker = EntityLinking.get_instance(
            predefined_ent_dir, "state_or_province"
        )
        self.crs_linker = EntityLinking.get_instance(predefined_ent_dir, "crs")
        self.category_linker = EntityLinking.get_instance(
            predefined_ent_dir, "category"
        )
        self.unit_commodity_linker = UnitAndCommodityTrustedLinker.get_instance(
            CRITICAL_MAAS_DIR / "kgdata/data/predefined-entities",
            CRITICAL_MAAS_DIR
            / "ta2-table-understanding/data/units_and_commodities.json",
        )

        self.unit_linker = UnitCompatibleLinker(self.unit_commodity_linker)
        self.commodity_linker = CommodityCompatibleLinker(self.unit_commodity_linker)

    @staticmethod
    def map(infile: Path, dup_record_ids: bool) -> list:
        g = Graph()
        g.parse(str(infile), format="turtle")
        return MosMapping(g)(dup_record_ids)

    def __call__(self, dup_record_ids: bool) -> list:
        doc_nodes = list(self.g.subjects(RDF.type, mos.Document))
        if len(doc_nodes) == 0:
            # no document, they use `source_id`
            doc_node = None
            source_id = next(self.g.subject_objects(mos.source_id))[1]
            doc = {"uri": source_id}
        else:
            doc_node = doc_nodes[0]
            doc = self.map_doc(doc_node)

        sites = {}
        site_names = [
            (
                site,
                assert_isinstance(self.map_literal(self.object(site, RDFS.label)), str),
            )
            for site in self.g.subjects(RDF.type, mos.MineralSite)
        ]

        record_type = None
        if doc_node is not None and self.has(doc_node, mos.record_type):
            record_type = self.map_literal(self.object(doc_node, mos.record_type))

        for ri, (site_node, site_name) in tqdm(
            enumerate(sorted(site_names, key=lambda x: x[1])), total=len(site_names)
        ):
            invs = []
            for inv in self.g.objects(site_node, mos.mineral_inventory):
                invs.extend(self.map_mineral_inventory(inv, doc))

            if self.has(site_node, mos.row_index):
                ri = self.map_literal(self.object(site_node, mos.row_index))
                record_id = f"{slugify(site_name)}__{ri}"
            elif self.has(site_node, mos.record_id):
                record_id = self.map_literal(self.object(site_node, mos.record_id))
            elif record_type == "multirow":
                record_id = slugify(site_name)
            elif record_type == "row":
                if self.has(site_node, mos.country):
                    country = self.map_literal(self.object(site_node, mos.country))
                    assert isinstance(country, str)
                    record_id = f"{slugify(site_name)}__{slugify(country)}"
                else:
                    record_id = slugify(site_name)
                record_id += "__" + str(ri)
            else:
                raise Exception("No record id")

            if record_id in sites:
                if not dup_record_ids:
                    raise Exception("Duplicate record id: {}".format(record_id))
                else:
                    # we have duplicated record ids when inventories are splitted into multiple rows
                    assert sites[record_id]["location_info"] == self.map_location_info(
                        site_node
                    )
                    assert sites[record_id]["name"] == site_name
                    assert sites[record_id]["deposit_type_candidate"] == [
                        self.map_deposit_type(deptyp)
                        for deptyp in self.g.objects(site_node, mos.deposit_type)
                    ]
                    sites[record_id]["mineral_inventory"].extend(invs)
            else:
                sites[record_id] = {
                    "source_id": doc["uri"],
                    "record_id": record_id,
                    "name": site_name,
                    "location_info": self.map_location_info(site_node),
                    "deposit_type_candidate": [
                        self.map_deposit_type(deptyp)
                        for deptyp in self.g.objects(site_node, mos.deposit_type)
                    ],
                    "mineral_inventory": invs,
                }

        return list(sites.values())

    def map_doc(self, doc: rdflib.term.Node) -> dict:
        output = {}

        if self.has(doc, mos.title):
            output["title"] = assert_isinstance(
                self.map_literal(self.object(doc, mos.title)), str
            )

        if self.has(doc, mos.doi):
            output["doi"] = assert_isinstance(
                self.map_literal(self.object(doc, mos.doi)), str
            )
            output["uri"] = "https://doi.org/" + output["doi"]
        else:
            assert self.has(doc, mos.title)
            output["uri"] = "http://minmod.isi.edu/papers/" + slugify(output["title"])

        if self.has(doc, mos.author):
            output["authors"] = [
                self.map_literal(author) for author in self.g.objects(doc, mos.author)
            ]
        return output

    def map_location_info(self, site: rdflib.term.Node) -> Optional[dict]:
        output = {}
        if self.has(site, mos.country):
            output["country"] = [
                self.get_candidate(obj, self.country_linker)
                for obj in self.g.objects(site, mos.country)
            ]
        if self.has(site, mos.state_or_province):
            output["state_or_province"] = [
                self.get_candidate(
                    obj,
                    self.state_or_province_linker,
                )
                for obj in self.g.objects(site, mos.state_or_province)
            ]
        if self.has(site, mos.location):
            output["location"] = assert_isinstance(
                self.map_literal(self.object(site, mos.location)), str
            )
        elif self.has(site, mos.latitude):
            assert self.has(site, mos.longitude)
            long = assert_isinstance(
                self.map_literal(self.object(site, mos.longitude)), float
            )
            lat = assert_isinstance(
                self.map_literal(self.object(site, mos.latitude)), float
            )
            output["location"] = f"POINT({long:.5f} {lat:.5f})"

        if self.has(site, mos.crs):
            output["crs"] = self.get_candidate(
                self.object(site, mos.crs), self.crs_linker
            )
        else:
            output["crs"] = {
                "normalized_uri": "https://minmod.isi.edu/resource/Q701",
                "confidence": 0.8,  # my guess for the prior probability
                "source": "SAND",
            }

        if len(output) == 0:
            return None
        return output

    def map_deposit_type(self, dep_type: rdflib.term.Node) -> dict:
        if isinstance(dep_type, rdflib.term.Literal):
            return self.get_candidate(
                dep_type,
                None,
            )

        return self.get_candidate(
            self.object(dep_type, RDFS.label),
            (dep_type, "prelinked"),
        )

    def map_mineral_inventory(self, inv: rdflib.term.Node, doc: dict) -> list[dict]:
        base: dict = {
            "commodity": self.get_candidate(
                self.object(inv, mos.commodity), self.commodity_linker
            ),
            "reference": {"document": doc, "page_info": []},
        }

        if self.has(inv, mos.date):
            base["date"] = self.map_literal(self.object(inv, mos.date))

        # if they spell out grade/tonnage for different categories
        if self.has(inv, mos.tonnage):
            base["ore"] = {
                "value": self.map_literal(self.object(inv, mos.tonnage)),
                "unit": self.get_candidate(
                    self.object(inv, mos.tonnage_unit), self.unit_linker
                ),
            }
            if self.has(inv, mos.category):
                # handle Measure+Indicated
                inv_cat_lst = []
                for cat in self.g.objects(inv, mos.category):
                    if isinstance(cat, rdflib.term.Literal) and "+" in str(cat):
                        inv_cat_lst.extend(
                            (rdflib.term.Literal(x) for x in str(cat).split("+"))
                        )
                    else:
                        inv_cat_lst.append(cat)
                base["category"] = [
                    self.get_candidate(cat, self.category_linker) for cat in inv_cat_lst
                ]
            if self.has(inv, mos.grade):
                base["grade"] = {
                    "value": self.map_literal(self.object(inv, mos.grade)),
                    "unit": self.get_candidate(
                        self.object(inv, mos.grade_unit), self.unit_linker
                    ),
                }

            return [base]

        output = []
        # if they only report the aggregated grade/tonnage
        if self.has(inv, mos.resource_tonnage):
            resource = base.copy()
            resource["ore"] = {
                "value": self.map_literal(self.object(inv, mos.resource_tonnage)),
                "unit": self.get_candidate(
                    self.object(inv, mos.resource_tonnage_unit), self.unit_linker
                ),
            }
            if self.has(inv, mos.resource_grade):
                resource["grade"] = {
                    "value": self.map_literal(self.object(inv, mos.resource_grade)),
                    "unit": self.get_candidate(
                        self.object(inv, mos.resource_grade_unit), self.unit_linker
                    ),
                }
            resource["category"] = [
                self.get_candidate(mnr[cat], None)
                for cat in ["Inferred", "Indicated", "Measured"]
            ]
            output.append(resource)

        if self.has(inv, mos.reserve_tonnage):
            reserve = base.copy()
            reserve["ore"] = {
                "value": self.map_literal(self.object(inv, mos.reserve_tonnage)),
                "unit": self.get_candidate(
                    self.object(inv, mos.reserve_tonnage_unit), self.unit_linker
                ),
            }
            if self.has(inv, mos.reserve_grade):
                reserve["grade"] = {
                    "value": self.map_literal(self.object(inv, mos.reserve_grade)),
                    "unit": self.get_candidate(
                        self.object(inv, mos.reserve_grade_unit), self.unit_linker
                    ),
                }
            reserve["category"] = [
                self.get_candidate(mnr[cat], None) for cat in ["Proven", "Probable"]
            ]
            output.append(reserve)

        return output

    def get_candidate(
        self,
        value: rdflib.term.Node,
        linker: Optional[
            IEntityLinking | tuple[rdflib.term.Node, Literal["prelinked"]]
        ],
    ) -> dict:
        if isinstance(value, rdflib.term.URIRef):
            return {
                "normalized_uri": value,
                "confidence": 0.99,
                "source": "SAND",
            }

        if isinstance(value, rdflib.term.Literal):
            observed_name = assert_isinstance(self.map_literal(value), str)
            output = {
                "observed_name": observed_name,
                "confidence": 0.0,
                "source": "SAND",
            }

            if linker is not None:
                if isinstance(linker, tuple):
                    subj = linker[0]
                    assert linker[1] == "prelinked"
                    if self.has(subj, mos.normalized_uri):
                        output["normalized_uri"] = self.map_uri(
                            self.object(subj, mos.normalized_uri)
                        )
                        if self.has(subj, mos.confidence):
                            output["confidence"] = self.map_literal(
                                self.object(subj, mos.confidence)
                            )
                        else:
                            output["confidence"] = 0.99
                else:
                    ent_score = linker.link(observed_name)
                    if ent_score is not None:
                        output["normalized_uri"] = ent_score[0].id
                        output["confidence"] = ent_score[1]

            return output

        raise Exception("Unreachable")

    def has(self, subj: rdflib.term.Node, prop: rdflib.term.Node) -> bool:
        return (subj, prop, None) in self.g

    def object(self, subj: rdflib.term.Node, prop: URIRef) -> rdflib.term.Node:
        try:
            (obj,) = list(self.g.objects(subj, prop))
        except:
            print(subj, list(self.g.objects(subj, prop)))
            raise
        return obj

    def map_uri(self, val: rdflib.term.Node) -> str:
        assert isinstance(val, rdflib.term.URIRef), val
        return str(val)

    def map_literal(self, val: rdflib.term.Node) -> JsonValue:
        if not isinstance(val, rdflib.term.Literal):
            raise TypeError("argument of type %s is not a literal" % type(val))

        if val.datatype is None:
            assert isinstance(val.value, str)
            return val.value

        if val.datatype == XSD.double:
            assert isinstance(val.value, float), (val.value, type(val.value))
            return val.value

        if val.datatype == XSD.decimal:
            assert isinstance(val.value, Decimal), (val.value, type(val.value))
            return float(val.value)

        if val.datatype == XSD.int or val.datatype == XSD.integer:
            assert isinstance(val.value, int)
            return val.value

        if val.datatype == XSD.string:
            assert isinstance(val.value, str)
            return val.value

        raise NotImplementedError(val.datatype)


@app.command()
def main(
    file: str,
    outdir: str,
    dup_record_id: bool = typer.Option(
        False, help="Whether to allow duplicate record ids"
    ),
):
    print("Mapping file", file)
    print("Expect duplicate record ids:", dup_record_id)
    for infile in glob.glob(file):
        infile = Path(infile)
        serde.json.ser(
            MosMapping.map(infile, dup_record_id),
            Path(outdir) / (infile.stem + ".json"),
            indent=2,
        )


if __name__ == "__main__":
    app()
