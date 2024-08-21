from pathlib import Path

import pandas as pd
import serde.csv
from sm.dataset import Dataset
from sm.namespaces.utils import KGName

from tum.actors.entry import *
from tum.config import CRITICAL_MAAS_DIR

test_exs = Dataset(CRITICAL_MAAS_DIR / "ta2-table-understanding/examples").load()
version = 112


for test_ex in test_exs:
    train_dataset = f"darpa-criticalmaas-{version}-ex-{test_ex.id}"
    minmod_actor = G.create_actor(
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
                train_dsquery=train_dataset,
                meta_prop_file=CRITICAL_MAAS_DIR
                / "ta2-table-understanding/data/meta_property/data.csv",
                top_n_stypes=2,
            ),
            MinmodGraphInferenceActorArgs(),
        ],
    )
    graphinf_actor = minmod_actor.graphinfer_actor

    test_exs = Dataset(CRITICAL_MAAS_DIR / "ta2-table-understanding/examples").load()

    with graphinf_actor.data_actor.use_examples(
        train_dataset,
        Dataset(CRITICAL_MAAS_DIR / "ta2-table-understanding/data/known_models").load()
        + [ex for ex in test_exs if ex.id != test_ex.id],
        prefix="",
    ):
        with graphinf_actor.data_actor.use_example(
            test_ex.id,
            test_ex,
        ) as testquery:
            sm = graphinf_actor(testquery)[0]
            print("=" * 80)
            print(testquery)
            sm.print()
