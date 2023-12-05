from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypeAlias

from graph.retworkx import BaseEdge, BaseNode, RetworkXStrDiGraph
from sm.dataset import FullTable
from sm.misc.funcs import assert_not_null


@dataclass
class CGNode(BaseNode[str]):
    id: str  # it is number but converted into a string

    is_statement_node: bool
    is_column_node: bool
    is_entity_node: bool
    is_literal_node: bool
    is_in_context: bool

    column_index: Optional[int]  # not null if is_column_node=True


CGEdgeTriple: TypeAlias = tuple[str, str, str]
CGEdge: TypeAlias = BaseEdge[str, str]


class CGraph(RetworkXStrDiGraph[str, CGNode, BaseEdge[str, str]]):
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
