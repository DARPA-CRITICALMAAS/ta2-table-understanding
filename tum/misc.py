from dataclasses import dataclass

from sm.outputs.semantic_model import SemanticType


@dataclass
class SemanticTypePrediction:
    stype: SemanticType
    score: float
    col_index: int
    col_name: str
