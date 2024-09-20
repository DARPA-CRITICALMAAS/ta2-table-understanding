from pathlib import Path

import pandas as pd
import serde.csv
from rdflib import RDFS
from sm.dataset import Dataset
from sm.evaluation.cpa_cta_metrics import PrecisionRecallF1, cpa, cta
from sm.evaluation.sm_metrics import precision_recall_f1
from sm.namespaces.utils import KGName
from tum.actors.entry import *
from tum.config import CRITICAL_MAAS_DIR
from tum.namespace import MNDRNamespace
from tum.sm.dsl.main import save_training_data

test_exs = Dataset(
    CRITICAL_MAAS_DIR / "ta2-table-understanding/data/training_set/minmod.zip"
).load()
kgns = MNDRNamespace.create()

version = 112
output = []
id_props = set([str(RDFS.label)])

outcpa = []
outcta = []
out = []

for i, test_ex in enumerate(test_exs):
    train_ds = f"dsl-exclude-{test_ex.id}"
    train_exs = [ex for ex in test_exs if ex.id != test_ex.id]

    save_training_data(train_ds, train_exs, kgns)

    minmod_actor = G.create_actor(
        MinmodTableTransformationActor,
        [
            DBActorArgs(
                kgdbs=[
                    KGDBArgs(
                        name=KGName.Generic,
                        version="20231130",
                        datadir=CRITICAL_MAAS_DIR / "data/minmod/databases",
                    )
                ]
            ),
            DataActorArgs(skip_unk_ont_ent=True, skip_no_sm=True),
            MinmodGraphGenerationActorArgs(
                # model="logistic-regression",
                model="random-forest-100",
                train_dsquery=train_ds,
                top_n_stypes=2,
            ),
            MinmodGraphInferenceActorArgs(),
        ],
    )
    graphinf_actor = minmod_actor.graphinfer_actor

    sm = minmod_actor.graphinfer_actor(test_ex.table)
    # cpares = cpa(test_ex.sms[0], sm, id_props)
    # ctares = cta(test_ex.sms[0], sm, id_props)
    out.append(precision_recall_f1(test_ex.sms[0], sm))

    print(test_ex.id)
    sm.print()
    # outcpa.append(cpares)
    # outcta.append(ctares)
    print(out[-1].precision, out[-1].recall, out[-1].f1)
    # print(cpares.precision, cpares.recall, cpares.f1)
    # print(ctares.precision, ctares.recall, ctares.f1)
    # output.append(
    #     {
    #         "cpa": (cpares.precision, cpares.recall, cpares.f1),
    #         "cta": (ctares.precision, ctares.recall, ctares.f1),
    #     }
    # )

print(PrecisionRecallF1.avg(out))
# print(PrecisionRecallF1.avg(outcpa))
# print(PrecisionRecallF1.avg(outcta))
