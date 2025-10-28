from __future__ import annotations

from typing import Optional

from sm.prelude import I, O
from tum.dag import IdentObj, hash_dict
from tum.sm.llm.openai_sem_label import InputTable, OpenAILiteralPrediction


def set_table(table: I.ColumnBasedTable) -> IdentObj[I.ColumnBasedTable]:
    return IdentObj(key=hash_dict(table.to_dict()), value=table)


def post_process_sm(
    table: InputTable,
    sm: O.SemanticModel,
    literal_prediction: Optional[OpenAILiteralPrediction] = None,
):
    has_grade_unit = False
    has_commodity = False
    has_tonnage_unit = False

    for edge in sm.iter_edges():
        if (
            edge.abs_uri
            == "https://minmod.isi.edu/ontology-simple/commodity_and_grade_unit"
        ):
            edge.abs_uri = "https://minmod.isi.edu/ontology-simple/commodity"
            edge.rel_uri = "mos:commodity"
            edge.readable_label = "commodity"
            sm.add_edge(
                O.Edge(
                    source=edge.source,
                    target=edge.target,
                    abs_uri="https://minmod.isi.edu/ontology-simple/grade_unit",
                    rel_uri="mos:grade_unit",
                    readable_label="grade unit",
                )
            )

            has_grade_unit = True
            has_commodity = True

        if edge.abs_uri == "https://minmod.isi.edu/ontology-simple/grade_unit":
            has_grade_unit = True
        if edge.abs_uri == "https://minmod.isi.edu/ontology-simple/commodity":
            has_commodity = True
        if edge.abs_uri == "https://minmod.isi.edu/ontology-simple/tonnage_unit":
            has_tonnage_unit = True

    if not has_grade_unit and literal_prediction is not None:
        grade_unit = literal_prediction.extract_grade_unit(table)
        if grade_unit is not None:
            uid = sm.add_node(O.LiteralNode(grade_unit, is_in_context=True))
            for node in sm.iter_nodes():
                if (
                    isinstance(node, O.ClassNode)
                    and node.abs_uri
                    == "https://minmod.isi.edu/ontology-simple/MineralInventory"
                ):
                    sm.add_edge(
                        O.Edge(
                            source=node.id,
                            target=uid,
                            abs_uri="https://minmod.isi.edu/ontology-simple/grade_unit",
                            rel_uri="mos:grade_unit",
                        )
                    )

    if not has_commodity and literal_prediction is not None:
        commodity = literal_prediction.extract_commodity(table)
        if commodity is not None:
            uid = sm.add_node(O.LiteralNode(commodity, is_in_context=True))
            for node in sm.iter_nodes():
                if (
                    isinstance(node, O.ClassNode)
                    and node.abs_uri
                    == "https://minmod.isi.edu/ontology-simple/MineralInventory"
                ):
                    sm.add_edge(
                        O.Edge(
                            source=node.id,
                            target=uid,
                            abs_uri="https://minmod.isi.edu/ontology-simple/commodity",
                            rel_uri="mos:commodity",
                        )
                    )

    if not has_tonnage_unit and literal_prediction is not None:
        tonnage_unit = literal_prediction.extract_tonnage_unit(table)
        if tonnage_unit is not None:
            uid = sm.add_node(O.LiteralNode(tonnage_unit, is_in_context=True))
            for node in sm.iter_nodes():
                if (
                    isinstance(node, O.ClassNode)
                    and node.abs_uri
                    == "https://minmod.isi.edu/ontology-simple/MineralInventory"
                ):
                    sm.add_edge(
                        O.Edge(
                            source=node.id,
                            target=uid,
                            abs_uri="https://minmod.isi.edu/ontology-simple/tonnage_unit",
                            rel_uri="mos:tonnage_unit",
                        )
                    )
