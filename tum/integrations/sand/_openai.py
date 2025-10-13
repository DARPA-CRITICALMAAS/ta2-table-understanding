from __future__ import annotations

import copy
import os
import random
from pathlib import Path

import serde.json
import strsim
from dependency_injector.wiring import Provide
from libactor.cache import fmt_keys
from libactor.dag import Flow, PartialFn
from sand.container import AppContainer
from sand.extension_interface.assistant import IAssistant
from sand.helpers.dependency_injection import autoinject
from sand.models.entity import EntityAR
from sand.models.ontology import OntClassAR, OntPropertyAR
from sand.models.table import Table, TableRow
from sm.dataset import FullTable
from sm.prelude import I, O
from tum.dag import (
    PROJECT_DIR,
    GppSemLabelActor,
    GppSemLabelArgs,
    IdentObj,
    get_context,
    get_dag,
)
from tum.integrations.sand._common import set_table
from tum.sm.llm.openai_sem_label import InputTable, OpenAILiteralPrediction


class OpenAIMinModAssistant(IAssistant):
    @autoinject
    def __init__(
        self,
        dbpath: Path,
        model: str,
        api_key: str,
        max_sampled_rows: int,
        example_dir: str,
        entities: EntityAR = Provide[AppContainer.entities],
        classes: OntClassAR = Provide[AppContainer.classes],
        props: OntPropertyAR = Provide[AppContainer.properties],
    ):
        self.entities = entities
        self.classes = classes
        self.props = props

        if len(api_key) < 24:
            api_key = os.environ[api_key]

        self.max_sampled_rows = max_sampled_rows
        cwd = PROJECT_DIR / "data/dag"
        self.dag = get_dag(
            cwd=cwd,
            table=set_table,
            # predict semantic types for each column
            sem_label=Flow(
                source="table",
                target=GppSemLabelActor(
                    GppSemLabelArgs(
                        model="tum.sm.llm.openai_sem_label.OpenAISemLabel",
                        model_args={
                            "model": model,
                            "api_key": api_key,
                            "max_sampled_rows": max_sampled_rows,
                        },
                        data="tum.sm.llm.openai_sem_label.get_dataset",
                        data_args={},
                    )
                ),
            ),
            without_sm_curation=True,
            without_json_export=True,
        )
        self.literal_prediction = OpenAILiteralPrediction(
            model=model,
            api_key=api_key,
            outdir=cwd / f"literal-prediction-{model}-{max_sampled_rows}",
            max_sampled_rows=max_sampled_rows,
        )
        self.context = get_context(cwd, dbpath)
        self.example_retriever = ExampleRetriever(Path(example_dir))

    def predict(self, table: Table, rows: list[TableRow]):
        norm_table = self.convert_table(table, rows)
        input_table = self.get_input_table(norm_table)
        sm = self.dag.process(
            input={"table": (norm_table,)},
            output={"sem_model"},
            context=self.get_mod_context(input_table),
        )["sem_model"][0].value
        post_process_sm(
            input_table,
            sm,
            self.literal_prediction,
        )
        rows = copy.deepcopy(rows)
        return sm, rows

    def convert_table(self, table: Table, rows: list[TableRow]) -> I.ColumnBasedTable:
        newtbl = I.ColumnBasedTable(
            f"p{table.project_id}---t:{table.id}---{table.name}",
            columns=[
                I.Column(index=ci, name=col, values=[row.row[ci] for row in rows])
                for ci, col in enumerate(table.columns)
            ],
        )
        return newtbl

    def get_input_table(self, table: I.ColumnBasedTable):
        return InputTable.from_full_table(
            FullTable.from_column_based_table(table),
            sample_size=self.max_sampled_rows,
            seed=42,
        )

    def get_mod_context(self, input_table: InputTable):
        indf = input_table.removed_irrelevant_table_df
        cells = list(set(indf.values.ravel().tolist()))

        prop2exs = self.example_retriever.get_topk_similar_examples(cells)

        schema = self.context["schema"].value
        schema = copy.deepcopy(schema)

        for i in range(len(schema.props)):
            propname = schema.prop_labels[i].replace(" ", "_")
            if propname not in prop2exs:
                continue
            exdata = prop2exs[propname]
            label = schema.prop_easy_labels[i] + ". "
            if len(exdata["aliases"]) > 0:
                label += "Property aliases: " + ", ".join(exdata["aliases"]) + ". "
            if len(exdata["values"]) > 0:
                label += (
                    "Examples: " + ", ".join((str(v) for v in exdata["values"])) + ". "
                )

            schema.prop_easy_labels[i] = label

        context = dict(**self.context)
        context["schema"] = IdentObj(
            key=self.context["schema"].key + "::" + input_table.id, value=schema
        )
        return context


class ExampleRetriever:
    def __init__(self, ex_dir: Path, top_k_examples: int = 10):
        self.ex_dir = ex_dir
        self.top_k_examples = top_k_examples
        self.tokenizer = strsim.CharacterTokenizer()

        self.name2exs = {}
        for ex_file in ex_dir.iterdir():
            if ex_file.suffix == ".json":
                self.name2exs[ex_file.stem] = serde.json.deser(ex_file)
                if (
                    "aliases" not in self.name2exs[ex_file.stem]
                    or "values" not in self.name2exs[ex_file.stem]
                ):
                    continue
                self.name2exs[ex_file.stem]["token_values"] = [
                    self.tokenizer.tokenize(v)
                    for v in self.name2exs[ex_file.stem]["values"]
                ]

    def get_topk_similar_examples(
        self, cells: list[str | int | float | bool]
    ) -> dict[str, dict]:
        token_cells = [self.tokenizer.tokenize(c) for c in cells if isinstance(c, str)]
        output = {}

        for name, exs in self.name2exs.items():
            values_score = []
            for i, token_val in enumerate(exs["token_values"]):
                score = max(
                    strsim.levenshtein_similarity(token_val, tkcel)
                    for tkcel in token_cells
                )
                values_score.append((i, score))
            topk = sorted(values_score, key=lambda x: x[1], reverse=True)[
                : self.top_k_examples
            ]
            output[name] = {
                "aliases": exs["aliases"],
                "values": [exs["values"][i] for i, score in topk],
            }

        return output


def post_process_sm(
    table: InputTable, sm: O.SemanticModel, literal_prediction: OpenAILiteralPrediction
):
    has_grade_unit = False
    has_commodity = False
    has_tonnage_unit = False

    for edge in sm.iter_edges():
        if edge.abs_uri == "https://minmod.isi.edu/ontology-simple/commodity_grade":
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

    if not has_grade_unit:
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

    if not has_commodity:
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

    if not has_tonnage_unit:
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
