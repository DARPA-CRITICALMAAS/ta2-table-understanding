from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypeAlias

from graph.retworkx import BaseEdge, BaseNode, RetworkXStrDiGraph

from sm.dataset import FullTable
from sm.misc.funcs import assert_not_null


class CGNode(BaseNode[str]):
    def __init__(
        self,
        id: str,
        is_statement_node: bool,
        is_column_node: bool,
        is_entity_node: bool,
        is_literal_node: bool,
        is_in_context: bool,
        column_index: Optional[int],
        value: Optional[str],
    ):
        super().__init__(id)
        self.is_statement_node = is_statement_node
        self.is_column_node = is_column_node
        self.is_entity_node = is_entity_node
        self.is_literal_node = is_literal_node
        self.is_in_context = is_in_context
        self.column_index = column_index  # not null if is_column_node=True
        self.value = value  # will be URI if it's entity/class, or value if it's literal

    @property
    def is_class_node(self) -> bool:
        return (
            not self.is_entity_node
            and not self.is_column_node
            and not self.is_statement_node
            and not self.is_literal_node
        )


class CGEdge(BaseEdge[str, str]):
    def __init__(self, id: int, source: str, target: str, key: str, score: float):
        super().__init__(id, source, target, key)
        self.score = score


CGEdgeTriple: TypeAlias = tuple[str, str, str]


class CGraph(RetworkXStrDiGraph[str, CGNode, CGEdge]):
    """A temporary copied version of the candidate graph in Rust for running post-processing"""

    def remove_dangling_statement(self):
        """Remove statement nodes that have no incoming nodes or no outgoing edges"""
        for s in self.nodes():
            if s.is_statement_node and (
                self.in_degree(s.id) == 0 or self.out_degree(s.id) == 0
            ):
                self.remove_node(s.id)

    def remove_standalone_nodes(self):
        """Remove nodes that do not any incoming / outgoing edges"""
        for u in self.nodes():
            if self.degree(u.id) == 0:
                self.remove_node(u.id)
