from collections import defaultdict
from typing import Mapping, Optional, Sequence

from tum.lib.cgraph import CGEdge, CGNode, CGraph
from tum.misc import SemanticTypePrediction


class GraphGeneration:
    def __init__(
        self,
        classes: Mapping[str, Optional[int]],
        object_props: Mapping[tuple[str, str], Mapping[str, float]],
    ):
        self.classes = classes
        self.object_props = object_props

    def __call__(self, ex_stypes: Sequence[Sequence[SemanticTypePrediction]]):
        cg = CGraph()

        # construct classes
        class2cols = defaultdict(set)
        for stypes in ex_stypes:
            col = stypes[0].col_index
            for clsid in {stype.stype.class_abs_uri for stype in stypes}:
                class2cols[clsid].add(col)

        class2nodes = defaultdict(list)
        for clsid, cols in class2cols.items():
            n_classes = min(self.classes.get(clsid) or len(cols), len(cols))
            for i in range(n_classes):
                uid = cg.add_node(
                    CGNode(
                        id=f"{clsid}:{i}",
                        is_statement_node=False,
                        is_column_node=False,
                        is_entity_node=False,
                        is_literal_node=False,
                        is_in_context=False,
                        column_index=None,
                        value=clsid,
                    )
                )
                class2nodes[clsid].append(uid)

        # construct object properties
        for (source_clsid, target_clsid), preds in self.object_props.items():
            for uid in class2nodes.get(source_clsid, []):
                for vid in class2nodes.get(target_clsid, []):
                    for pred, score in preds.items():
                        cg.add_edge(
                            CGEdge(id=-1, source=uid, target=vid, key=pred, score=score)
                        )

        for stypes in ex_stypes:
            col = stypes[0].col_index
            vid = cg.add_node(
                CGNode(
                    id=f"col:{col}",
                    is_statement_node=False,
                    is_column_node=True,
                    is_entity_node=False,
                    is_literal_node=False,
                    is_in_context=False,
                    column_index=col,
                    value=None,
                )
            )
            for stype in stypes:
                for uid in class2nodes[stype.stype.class_abs_uri]:
                    cg.add_edge(
                        CGEdge(
                            id=-1,
                            source=uid,
                            target=vid,
                            key=stype.stype.predicate_abs_uri,
                            score=stype.score,
                        )
                    )

        return cg

    def validate(self):
        """Validate the graph... If we"""
        pass
