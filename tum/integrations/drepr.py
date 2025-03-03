from collections import defaultdict
from io import BytesIO, StringIO

import sm.outputs.semantic_model as O
from kgdata.dbpedia.datasets.ontology_dump import aggregated_triples
from rdflib import BNode, Graph, URIRef
from sand_drepr.main import DreprExport

# from drepr.engine import MemoryOutput, OutputFormat, ResourceDataString, execute
from drepr.models.prelude import (
    AlignedStep,
    Attr,
    CSVProp,
    DRepr,
    IndexExpr,
    Path,
    PMap,
    Preprocessing,
    PreprocessingType,
    RangeAlignment,
    RangeExpr,
    Resource,
    ResourceType,
)
from sand.models.table import Table, TableRow

OutputFormat = str


class CustomizedDReprExport(DreprExport):
    pass
    # def post_processing(
    #     self, sm: O.SemanticModel, ttldata: str, output_format: OutputFormat
    # ) -> str:
    #     g = Graph()
    #     file = StringIO(ttldata)
    #     g.parse(file)

    #     counter = 15000
    #     remap = {}
    #     new_triples = []
    #     for s, p, o in g:
    #         if isinstance(s, BNode) and str(s) not in remap:
    #             remap[str(s)] = self.namespace.kgns.get_abs_uri(f"mndr:Q{counter}")
    #             counter += 1
    #         if isinstance(o, BNode) and str(o) not in remap:
    #             remap[str(o)] = self.namespace.kgns.get_abs_uri(f"mndr:Q{counter}")
    #             counter += 1

    #         if isinstance(s, BNode):
    #             s = URIRef(remap[str(s)])
    #         if isinstance(o, BNode):
    #             o = URIRef(remap[str(o)])

    #         new_triples.append((s, p, o))

    #     ng = Graph()
    #     for prefix, ns in self.namespace.kgns.prefix2ns.items():
    #         ng.bind(prefix, ns)
    #     for triple in new_triples:
    #         ng.add(triple)

    #     file = BytesIO()
    #     ng.serialize(file, format="turtle")
    #     ttldata = file.getvalue().decode()

    #     return super().post_processing(sm, ttldata, output_format)


#     def export_drepr_model(self, table: Table, sm: O.SemanticModel) -> DRepr:
#         drepr = super().export_drepr_model(table, sm)

#         # Add preprocessing to generate unique id for some given classes
#         target_classes = [
#             self.namespace.kgns.get_abs_uri(key)
#             for key in [
#                 "mndr:Ore",
#                 # "mndr:Grade",
#                 # "mndr:MineralInventory",
#             ]
#         ]

#         gen_unique_id = """
# return str(index)
# """.strip()

#         for u in sm.iter_nodes():
#             if isinstance(u, O.ClassNode):
#                 if u.abs_uri in target_classes:
#                     drepr.preprocessing.append(
#                         Preprocessing(
#                             type=PreprocessingType.pmap,
#                             value=PMap(
#                                 resource_id="table",
#                                 path=drepr.attrs[0].path,
#                                 code=gen_unique_id,
#                                 output="test-ore",
#                                 change_structure=False,
#                             ),
#                         )
#                     )

#         return drepr
