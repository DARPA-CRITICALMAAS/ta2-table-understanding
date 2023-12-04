import os

os.environ["HOME_DIR"] = "/Volumes/research/data"
os.environ["ENABLE_OSIN"] = "true"
os.environ["ENABLE_CACHE"] = "1"
os.environ["CANRANK_VERBOSE"] = "1"


from grams.actors.__main__ import (
    HOME_DIR,
    DataActorArgs,
    DBActor,
    DBActorArgs,
    G,
    KGDBArgs,
    KGName,
    PretrainedCanRankModelArgs,
)
from tum.actors.semanticmodel import (
    MinmodGraphGenerationActor,
    MinmodGraphGenerationActorArgs,
    MinmodGraphInferenceActor,
    MinmodGraphInferenceActorArgs,
)
from tum.namespace import MNDRNamespace

from sm.dataset import Dataset
from sm.namespaces.utils import KGName, register_kgns

register_kgns(KGName.Generic, MNDRNamespace.create())

G.auto_add_actor(MinmodGraphGenerationActor)
G.auto_add_actor(MinmodGraphInferenceActor)
