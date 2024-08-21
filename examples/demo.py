from collections import defaultdict
from pathlib import Path

import pandas as pd
import serde.csv
from sm.dataset import Dataset
from sm.namespaces.utils import KGName
from sm.prelude import O

from tum.actors.entry import *
from tum.config import CRITICAL_MAAS_DIR

meta_prop_file = (
    CRITICAL_MAAS_DIR / "ta2-table-understanding/data/meta_property/data.csv"
)

actor = G.create_actor(
    MinmodTableTransformationActor,
    [
        DBActorArgs(
            kgdbs=[
                KGDBArgs(
                    name=KGName.Generic,
                    version="20231130",
                    datadir=CRITICAL_MAAS_DIR / "data/databases",
                )
            ]
        ),
        DataActorArgs(skip_unk_ont_ent=True, skip_no_sm=True),
        MinmodGraphGenerationActorArgs(
            train_dsquery="darpa-criticalmaas",
            meta_prop_file=CRITICAL_MAAS_DIR
            / "ta2-table-understanding/data/meta_property/data.csv",
            top_n_stypes=2,
        ),
        MinmodGraphInferenceActorArgs(),
    ],
)

test_exs = Dataset(CRITICAL_MAAS_DIR / "ta2-table-understanding/examples").load()

with actor.data_actor.use_examples(
    "darpa-criticalmaas",
    Dataset(CRITICAL_MAAS_DIR / "ta2-table-understanding/data/known_models").load(),
    prefix="",
):
    for test_ex in test_exs:
        with actor.data_actor.use_example(
            test_ex.id,
            test_ex,
        ) as testquery:
            sm = actor.graphinfer_actor(testquery)[0]
            # sm = test_ex.sms[0]
            print("=" * 80)
            print(testquery)
            sm.print()
            # print(
            #     actor.gen_drepr_model(
            #         test_ex.table, sm, actor.data_actor.get_kgdb(testquery)
            #     ).to_lang_yml(use_json_path=True)
            # )
