import orjson
import serde.json
import sm.outputs.semantic_model as O
from rdflib import RDF, RDFS, XSD, Graph, Namespace, URIRef
from sand.config import AppConfig
from sand.models.table import Table, TableRow
from sand_drepr.main import DreprExport, OutputFormat
from tum.map_mos import MosMapping


class MinModJSONExport(DreprExport):
    """Export data to JSON format."""

    def export_data(
        self,
        table: Table,
        rows: list[TableRow],
        sm: O.SemanticModel,
    ) -> str:
        ttl = super().export_data(table, rows, sm, OutputFormat.TTL)

        created_by = "https://minmod.isi.edu/users/u/unknown"
        g = Graph()
        g.parse(data=ttl, format="turtle")

        return orjson.dumps(
            MosMapping(g, created_by)(dup_record_ids=True),
            option=orjson.OPT_INDENT_2,
        ).decode()
