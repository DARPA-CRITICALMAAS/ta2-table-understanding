from __future__ import annotations

from pathlib import Path
from typing import Sequence

from dsl.dsl import DSL, DSLTable
from dsl.sm_type_db_v2 import SemanticTypeDBV2
from gpp.sem_label.isem_label import TableSemLabelAnnotation
from kgdata.models import Ontology
from libactor.cache import IdentObj
from sm.dataset import Dataset, Example, FullTable
from sm.inputs.table import ColumnBasedTable
from sm.misc.funcs import import_attr
from sm.typing import ExampleId
from smml.dataset import ColumnarDataset

from tum.sm.dsl.main import get_semantic_types

DREPR_UNK = "http://purl.org/drepr/1.0/Unknown"


class DSLSemLabelModel:

    def __init__(self, dsl: DSL, workdir: Path, top_n_stypes: int = 2):
        self.workdir = workdir
        self.dsl = dsl
        self.top_n_stypes = top_n_stypes

    @classmethod
    def load(
        cls,
        workdir: Path,
        data_dir: Path,
        model: str,
        ontology_factory: str,
        top_n_stypes: int = 2,
    ) -> DSLSemLabelModel:
        examples = [
            ex.replace_table(DSLTable.from_column_based_table(ex.table.table))
            for ex in Dataset(data_dir).load()
        ]

        ontology: Ontology = import_attr(ontology_factory)()

        dsl = DSL(
            examples,
            workdir / "dsl",
            classes=ontology.classes,
            props=ontology.props,
            model_name=model,
            semtype_db=SemanticTypeDBV2,
        )
        dsl.get_model(train_if_not_exist=True, save_train_data=True)
        return DSLSemLabelModel(
            dsl=dsl,
            workdir=workdir / "dsl",
            top_n_stypes=top_n_stypes,
        )

    def predict_dataset(
        self, dataset: ColumnarDataset, batch_size: int = 8, verbose: bool = False
    ) -> dict[ExampleId, TableSemLabelAnnotation]:
        output = {}
        tables: list[ColumnBasedTable] = dataset.columns["table"]  # type: ignore
        ontology: Ontology = dataset.references["ontology"]  # type: ignore

        # update the ontology that we are using -- this must match with the one used in the train_examples
        self.dsl.classes = ontology.classes
        self.dsl.props = ontology.props

        for table in tables:
            stypes = get_semantic_types(self.dsl, table, self.top_n_stypes)

            norm_stypes = {}
            for i, col in enumerate(table.columns):
                # convert semantic types (class, predicate) pair to list of either class or predicate
                out = {}
                for stype in stypes[i]:
                    out[stype.stype.class_abs_uri] = max(
                        out.get(stype.stype.class_abs_uri, 0), stype.score
                    )
                    out[stype.stype.predicate_abs_uri] = max(
                        out.get(stype.stype.predicate_abs_uri, 0), stype.score
                    )

                norm_stypes[col.index] = sorted(
                    out.items(), key=lambda x: x[1], reverse=True
                )

            output[table.table_id] = norm_stypes

        return output


def get_dataset():
    def func(
        examples: IdentObj[Sequence[Example[FullTable]]], ontology: IdentObj[Ontology]
    ) -> ColumnarDataset:
        columns = {"table": []}
        for ex in examples.value:
            table = ex.table.table
            columns["table"].append(table)
        return ColumnarDataset(columns, references={"ontology": ontology.value})

    return func
