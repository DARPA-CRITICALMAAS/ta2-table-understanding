from ream.prelude import ActorGraph, ReamWorkspace, configure_loguru
from sm.misc.ray_helper import set_ray_init_args
from tum.actors.data import DataActor, DataActorArgs
from tum.actors.db import DBActor, DBActorArgs, KGDBArgs
from tum.actors.semanticmodel import (
    MinmodGraphGenerationActor,
    MinmodGraphGenerationActorArgs,
    MinmodGraphInferenceActor,
    MinmodGraphInferenceActorArgs,
    MinmodTableTransformationActor,
    MinmodTableTransformationActorArgs,
)
from tum.config import REAM_DIR

ReamWorkspace.init(REAM_DIR)

set_ray_init_args(log_to_driver=False)
configure_loguru()

G = ActorGraph.auto(
    [
        DBActor,
        DataActor,
        MinmodGraphGenerationActor,
        MinmodGraphInferenceActor,
        MinmodTableTransformationActor,
    ],
    auto_naming=True,
)

__all__ = [
    "G",
    "DBActor",
    "DBActorArgs",
    "KGDBArgs",
    "DataActor",
    "DataActorArgs",
    "MinmodGraphGenerationActor",
    "MinmodGraphInferenceActor",
    "MinmodGraphGenerationActorArgs",
    "MinmodGraphInferenceActorArgs",
    "MinmodTableTransformationActor",
    "MinmodTableTransformationActorArgs",
]
