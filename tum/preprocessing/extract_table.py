from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import serde.json
from azure.ai.formrecognizer import AnalyzeResult, DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from libactor.cache import cache
from sm.inputs.prelude import Column, ColumnBasedTable
from sm.misc.prelude import Matrix, assert_not_null, filter_duplication
from timer import Timer
from tqdm import tqdm

from tum.config import AZURE_ACCESS_KEY, AZURE_DOC_INTEL_ENDPOINT
from tum.preprocessing.base import BasePipeOp


@dataclass
class TableExtractionArgs:
    infile: Path
    # page range
    page: Optional[tuple[int, int]] = None

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            infile=Path(d["infile"]),
            page=(
                (int(d["page"][0]), int(d["page"][1]))
                if d.get("page") is not None
                else None
            ),
        )


class TableExtraction(BasePipeOp):

    def __init__(self):
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=assert_not_null(AZURE_DOC_INTEL_ENDPOINT),
            credential=AzureKeyCredential(assert_not_null(AZURE_ACCESS_KEY)),
        )

    def invoke(self, args: TableExtractionArgs):
        assert args.infile.suffix == ".pdf"

        with Timer().watch_and_report("Analyze document"):
            result = self.analyze(args.infile)

        for ti, table in tqdm(enumerate(result.tables or []), desc="Extract tables"):
            # extract table cells -- spanning cells are copied
            cells = Matrix.default((table.row_count, table.column_count), dict)
            nrows, ncols = cells.shape()
            for cell in table.cells:
                for i in range(cell.row_span or 1):
                    for j in range(cell.column_span or 1):
                        cells[cell.row_index + i, cell.column_index + j] = {
                            "kind": cell.kind,
                            "content": cell.content.replace("\n", " ")
                            .replace(":unselected:", "")
                            .strip(),
                        }

            # if this is a relational table with column headers spanning multiple rows, we can merge the headers
            is_relational_table = False
            row_types = []
            for i in range(0, nrows):
                if all(cells[i, j]["kind"] == "columnHeader" for j in range(ncols)):
                    row_types.append("header")
                elif all(cells[i, j]["kind"] == "content" for j in range(ncols)):
                    row_types.append("content")
                else:
                    row_types.append("mixed")
            n_headers = 0
            for i, type in enumerate(row_types):
                if type == "header":
                    n_headers += 1
                else:
                    break
            if n_headers > 1 and row_types[n_headers] == "content":
                is_relational_table = True

            # now it's a relational table with column headers spanning multiple rows
            if is_relational_table and n_headers > 1:
                new_cells = Matrix(cells[n_headers - 1 :, :])
                # we only merge multi-row headers, what about multi-column headers?
                for cj in range(ncols):
                    values = " ".join(
                        filter_duplication(
                            (
                                cells[ri, cj]["content"].strip()
                                for ri in range(n_headers)
                            )
                        )
                    )
                    new_cells[0, cj] = {"kind": "columnHeader", "content": values}
                cells = new_cells
                nrows, ncols = cells.shape()

            (
                ColumnBasedTable(
                    args.infile.stem + f"_table_{ti}",
                    [
                        Column(
                            index=ci,
                            name=cells[0, ci]["content"],
                            values=[cells[ri, ci]["content"] for ri in range(1, nrows)],
                        )
                        for ci in range(ncols)
                    ],
                )
                .as_dataframe()
                .to_csv(
                    self.transformed_dir(args.infile) / f"extract_table_{ti}.csv",
                    index=False,
                )
            )

    def analyze(self, infile: Path) -> AnalyzeResult:
        cache_file = self.transformed_dir(infile) / "doc_analyze_result.json"
        if not cache_file.exists():
            poller = self.document_analysis_client.begin_analyze_document(
                "prebuilt-document", infile.read_bytes()
            )
            result = poller.result()
            serde.json.ser(result.to_dict(), cache_file, indent=2)

        return AnalyzeResult.from_dict(serde.json.deser(cache_file))


# # sample document
# formUrl = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"


# poller = document_analysis_client.begin_analyze_document_from_url(
#     "prebuilt-document", formUrl
# )
# result = poller.result()

# print("----Key-value pairs found in document----")
# for kv_pair in result.key_value_pairs:
#     if kv_pair.key and kv_pair.value:
#         print(
#             "Key '{}': Value: '{}'".format(kv_pair.key.content, kv_pair.value.content)
#         )
#     else:
#         print("Key '{}': Value:".format(kv_pair.key.content))

# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
# print("----------------------------------------")
