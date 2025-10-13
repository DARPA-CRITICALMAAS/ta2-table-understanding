from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from gpp.actors.qa_llm_actor import InputTable
from gpp.llm.qa_llm import ExplicitV100, Message, Schema, Thread
from gpp.llm.qa_llm._hugging_face_agent import BaseInference
from gpp.sem_label.isem_label import TableSemLabelAnnotation
from gpp.sem_label.models.llm import (
    HuggingFaceBasedAgent,
    MaxTokensExceededError,
    QueryResult,
    disk_slugify,
)
from libactor.cache import IdentObj
from openai import OpenAI
from sm.dataset import Example, FullTable
from sm.inputs.table import ColumnBasedTable
from sm.typing import ExampleId, InternalID
from smml.dataset import ColumnarDataset


class OpenAIAgent(BaseInference):
    def __init__(self, model: str, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _infer(self, conversation: list[Message], max_new_tokens: int) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": {
                        "user": "user",
                        "system": "developer",
                        "assistant": "assistant",
                    }[msg.role],
                    "content": msg.content,
                }
                for msg in conversation
            ],  # type: ignore
            max_output_tokens=max_new_tokens,
        )
        return response.output_text.strip()


class OpenAISemLabel(ExplicitV100):
    prompt_prop = """Use the below csv table and properties to answer the question.
**Table:**\n{CSV_TABLE}\n\n**Properties:**\n{PROPERTIES}\n
Question: What is the best property in the list above to describe the column "{COLUMN}"?
Please keep your answer short with only the property or N/A if there is no suitable property. Also, please wrap your answer with backticks. For example, {EXAMPLE}.
    """.strip()

    def __init__(
        self,
        model: str,
        api_key: str,
        outdir: Path,
        max_sampled_rows: int,
        max_new_tokens: int = 100,
    ):
        self.model = model
        self.api_key = api_key
        self.outdir = outdir
        self.max_new_tokens = max_new_tokens
        self.max_sampled_rows = max_sampled_rows
        self.client = OpenAIAgent(model, api_key)

    @classmethod
    def load(
        cls,
        workdir: Path,
        model: str,
        api_key: str,
        max_sampled_rows: int,
        max_new_tokens: int = 100,
    ):
        return cls(model, api_key, workdir / "openai", max_sampled_rows, max_new_tokens)

    def predict_dataset(
        self, dataset: ColumnarDataset, batch_size: int = 8, verbose: bool = False
    ) -> dict[ExampleId, TableSemLabelAnnotation]:
        output = {}
        tables: list[ColumnBasedTable] = dataset.columns["table"]  # type: ignore
        schema: Schema = dataset.references["schema"]  # type: ignore

        for table in tables:
            input_table = InputTable.from_full_table(
                FullTable.from_column_based_table(table),
                sample_size=self.max_sampled_rows,
                seed=42,
            )
            res = self.query(
                input_table,
                schema,
                [],
            )
            cta, _ = self.extract(
                input_table,
                [],
                schema,
                res,
                can_ask_for_correction=False,
            )

            norm_stypes = {}
            for i, col in enumerate(table.columns):
                norm_stypes[col.index] = []
                if i in cta:
                    norm_stypes[col.index].append((cta[i], 0.9))

            output[table.table_id] = norm_stypes

        return output

    def query(
        self,
        table: InputTable,
        schema: Schema,
        entity_columns: list[int],
    ) -> QueryResult:
        prop_content = "\n".join(
            [f"{i+1}. {s}" for i, s in enumerate(schema.prop_easy_labels)]
        )

        name = table.id.replace("/", "_")

        csv_table = table.removed_irrelevant_table
        n_retry = 1

        cta_output = []
        for ci in table.column_indexes:
            for _ in range(1, 10):
                msgs = []
                if len(self.system) > 0:
                    msgs.append(Message("system", self.system))
                msgs.append(
                    Message(
                        "user",
                        self.prompt_prop.format(
                            CSV_TABLE=csv_table,
                            PROPERTIES=prop_content,
                            COLUMN=table.index2name[ci],
                            EXAMPLE=f"`{schema.prop_easy_labels[-1]}`",
                        ),
                    )
                )
                try:
                    thread = Thread(
                        f"{name}/cta_{ci}_{disk_slugify(table.index2name[ci])}",
                        msgs,
                    )
                    thread = self.chat(thread)
                    cta_output.append((ci, thread))
                    break
                except MaxTokensExceededError as e:
                    n_rows = len(table.removed_irrelevant_table_df)
                    n_rows = n_rows - 10 * n_retry
                    n_retry += 1
                    assert n_rows >= 5, "We don't want our table to be too short"
                    print(
                        f"[{table.id}] Property prompt for column {ci} is too long. Try shorten the table to {n_rows} rows: {str(e)}"
                    )

                    csv_table = (
                        table.removed_irrelevant_table_df.head(n_rows)
                        .to_csv(index=False)
                        .strip()
                    )

        return (cta_output, [])

    def extract(
        self,
        table: InputTable,
        entity_columns: list[int],
        schema: Schema,
        output: QueryResult,
        can_ask_for_correction: bool = False,
    ):
        cta: dict[int, InternalID] = {}

        for ci, thread in output[0]:
            classid = self.parse_cpa_answer(thread.messages[-1].content, schema)
            if classid is None or classid not in schema.prop_label_keys:
                continue
            cta[ci] = schema.prop_label_keys[classid]

        return cta, []


class OpenAILiteralPrediction(HuggingFaceBasedAgent[Thread]):
    name = "openai-literal-prediction"
    system = "You are a skilled data scientist and you are asked to interpret a schema of the given table."
    prompt_tonnage_unit = """Use the below csv table to answer the question.
**Table:**\n{CSV_TABLE}\n\n
**Question**: What is the unit of tonnage values of mineral inventories of the mineral sites/deposits in the table?
Please keep your answer short with only the unit or N/A if there is no appropriate unit to all tonnage values. Also, please wrap your answer with backticks. For example, `Mt`.
"""
    prompt_grade_unit = """Use the below csv table to answer the question.
**Table:**\n{CSV_TABLE}\n\n
**Question**: What is the unit of grade values of mineral inventories of the mineral sites/deposits in the table?
Please keep your answer short with only the unit or N/A if there is no appropriate unit to all grade values. Also, please wrap your answer with backticks. For example, `%`.
"""
    prompt_commodity = """Use the below csv table to answer the question.
**Table:**\n{CSV_TABLE}\n\n
**Question**: What is the commodity of all the mineral sites/deposits reported in the table?
Please keep your answer short with only the unit or N/A if there is no reported commodity. Also, please wrap your answer with backticks. For example, `Copper`.
"""

    def __init__(
        self,
        model: str,
        api_key: str,
        outdir: Path,
        max_sampled_rows: int,
        max_new_tokens: int = 100,
    ):
        self.model = model
        self.api_key = api_key
        self.outdir = outdir
        self.max_new_tokens = max_new_tokens
        self.max_sampled_rows = max_sampled_rows
        self.client = OpenAIAgent(model, api_key)

    def query(
        self,
        table: InputTable,
        schema: Schema,
        entity_columns: list[int],
    ) -> Thread:
        raise NotImplementedError()

    def extract(
        self,
        table: InputTable,
        entity_columns: list[int],
        schema: Schema,
        output: Thread,
        can_ask_for_correction: bool = False,
    ):
        raise NotImplementedError()

    def extract_tonnage_unit(
        self,
        table: InputTable,
    ):
        name = table.id.replace("/", "_")
        csv_table = table.removed_irrelevant_table
        msgs = [
            Message("system", self.system),
            Message("user", self.prompt_tonnage_unit.format(CSV_TABLE=csv_table)),
        ]
        thread = Thread(
            f"{name}/literal_tonnage_unit",
            msgs,
        )
        thread = self.chat(thread)
        return self.extract_answer(thread.messages[-1].content)

    def extract_grade_unit(
        self,
        table: InputTable,
    ):
        name = table.id.replace("/", "_")
        csv_table = table.removed_irrelevant_table
        msgs = [
            Message("system", self.system),
            Message("user", self.prompt_grade_unit.format(CSV_TABLE=csv_table)),
        ]
        thread = Thread(
            f"{name}/literal_grade_unit",
            msgs,
        )
        thread = self.chat(thread)
        return self.extract_answer(thread.messages[-1].content)

    def extract_commodity(
        self,
        table: InputTable,
    ):
        name = table.id.replace("/", "_")
        csv_table = table.removed_irrelevant_table
        msgs = [
            Message("system", self.system),
            Message("user", self.prompt_commodity.format(CSV_TABLE=csv_table)),
        ]
        thread = Thread(
            f"{name}/literal_commodity",
            msgs,
        )
        thread = self.chat(thread)
        return self.extract_answer(thread.messages[-1].content)

    @classmethod
    def extract_answer(cls, ans: str):
        out = []
        for colpattern in [r'"([^"]*)"', r"`([^`]*)`"]:
            out.extend(list(re.finditer(colpattern, ans)))

        # sort by the order found in the answer
        out.sort(key=lambda x: x.span()[0])

        no_answer_keywords = ["N/A", "n/a", "N/a"]

        if any(item.group(1) in no_answer_keywords for item in out):
            return None

        if len(out) == 0:
            return None

        return out[0].group(1)


def get_dataset():
    def func(
        examples: IdentObj[Sequence[Example[FullTable]]], schema: IdentObj[Schema]
    ) -> ColumnarDataset:
        columns = {"table": []}
        for ex in examples.value:
            table = ex.table.table
            columns["table"].append(table)
        return ColumnarDataset(columns, references={"schema": schema.value})

    return func
