from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import pandas as pd
from kgdata.dbpedia.datasets.meta_graph_stats import (
    get_predicate_conn_dataset as dbpedia_get_predicate_conn_dataset,
)
from kgdata.wikidata.datasets.meta_graph_stats import (
    get_predicate_conn_dataset as wikidata_get_predicate_conn_dataset,
)
from ream.actors.base import BaseActor
from ream.cache_helper import Cache, MemBackend
from ream.params_helper import NoParams
from sm.misc.funcs import assert_one_item, group_by
from sm.namespaces.utils import KGName
from sm.prelude import O
from tum.actors.data import DataActor


@dataclass
class SimpleEdge:
    prop: str
    qual: Optional[str]
    source_type: str
    target_type: Optional[str]
    freq: float
    inherit_freq: float
    total_freq: float


# mapping from qual -> prop -> list of edges
DataPropSchema = dict[Optional[str], dict[str, list[SimpleEdge]]]
# mapping from (source_type, target_type) -> list of edges
ObjectPropSchema = dict[tuple[str, str], list[SimpleEdge]]


@dataclass
class GraphSpace:
    data_props: DataPropSchema
    object_props: ObjectPropSchema

    def __repr__(self):
        return "GraphSpace(data_props=..., object_props=...)"


class GraphSpaceV1(BaseActor[NoParams]):
    VERSION = 103

    def __init__(self, params: NoParams, data_actor: DataActor):
        super().__init__(params, [data_actor])
        self.data_actor = data_actor

    @Cache.cache(backend=Cache.file.pickle(mem_persist=True, log_serde_time=True))
    def __call__(
        self,
        dataset: str,
        top_k_data_props: Optional[int] = None,
        top_k_object_props: Optional[int] = None,
    ) -> GraphSpace:
        """Get data props as well as object props"""
        used_props, used_classes = self.get_gold_schema(dataset)
        classes = self.data_actor.get_kgdb(dataset).pydb.classes.cache()
        pconns = self.get_predicate_conns(dataset)

        data_props = {
            qual: group_by(lst, lambda x: x.prop)
            for qual, lst in group_by(pconns, lambda x: x.qual).items()
        }
        object_props = group_by(pconns, lambda x: (x.source_type, x.target_type))

        new_data_props: dict[Optional[str], dict[str, list[SimpleEdge]]] = defaultdict(
            lambda: defaultdict(list)
        )
        new_object_props: dict[tuple[str, str], list[SimpleEdge]] = {}

        for qual in list(used_props) + [None]:
            if qual not in data_props:
                continue

            for prop in used_props:
                if prop not in data_props[qual]:
                    continue

                # combination of (source & target types) that can be found in the dataset
                lst = [
                    conn
                    for conn in data_props[qual][prop]
                    if conn.source_type in used_classes
                    and (conn.target_type is None or conn.target_type in used_classes)
                ]

                newlst: list[SimpleEdge] = []
                # to count the frequency of each (source & target types) combination with inheritance, we need
                # to search their ancestors
                descendants = {
                    source: {
                        target: assert_one_item(tmp1)
                        for target, tmp1 in group_by(
                            tmp, lambda x: x.target_type
                        ).items()
                    }
                    for source, tmp in group_by(lst, lambda x: x.source_type).items()
                }
                ancestors = {
                    source: {
                        target: assert_one_item(tmp1)
                        for target, tmp1 in group_by(
                            tmp, lambda x: x.target_type
                        ).items()
                    }
                    for source, tmp in group_by(
                        data_props[qual][prop], lambda x: x.source_type
                    ).items()
                }

                for des_sourceid, des_targets in descendants.items():
                    des_source = classes[des_sourceid]

                    inheriting_ancestors = {
                        anc_sourceid: anc_targets
                        for anc_sourceid, anc_targets in ancestors.items()
                        if anc_sourceid in des_source.ancestors
                    }
                    for des_targetid, des_conn in des_targets.items():
                        if des_targetid is not None:
                            des_target = classes[des_targetid]
                        else:
                            des_target = None

                        newrecord = SimpleEdge(
                            prop=prop,
                            qual=qual,
                            source_type=des_sourceid,
                            target_type=des_targetid,
                            freq=des_conn.freq,
                            inherit_freq=des_conn.freq,
                            total_freq=-1,
                        )

                        for anc_sourceid, anc_targets in inheriting_ancestors.items():
                            for anc_targetid, anc_conn in anc_targets.items():
                                if des_targetid is None:
                                    if anc_targetid is None:
                                        newrecord.inherit_freq += anc_conn.freq
                                else:
                                    assert des_target is not None
                                    if anc_targetid in des_target.ancestors:
                                        newrecord.inherit_freq += anc_conn.freq

                        newlst.append(newrecord)

                if len(newlst) > 0:
                    new_data_props[qual][prop] = sorted(
                        newlst, key=lambda x: x.inherit_freq, reverse=True
                    )

            # update total frequency -- this is to normalize
            # the likelihood of choosing source given a prop.
            total_freq = sum(
                edge.inherit_freq
                for edges in new_data_props[qual].values()
                for edge in edges
            )
            for edges in new_data_props[qual].values():
                for edge in edges:
                    edge.total_freq = total_freq

        for (source_type, target_type), conns in object_props.items():
            if (
                target_type is None
                or source_type not in used_classes
                or target_type not in used_classes
            ):
                continue

            conns = [
                conn
                for conn in conns
                if conn.prop in used_props
                and (conn.qual is None or conn.qual in used_props)
            ]

            total_freq = sum(conn.freq for conn in conns)
            new_object_props[source_type, target_type] = sorted(
                [
                    SimpleEdge(
                        conn.prop,
                        conn.qual,
                        conn.source_type,
                        conn.target_type,
                        conn.freq,
                        conn.freq,
                        total_freq,
                    )
                    for conn in conns
                ],
                key=lambda x: x.inherit_freq,
                reverse=True,
            )

        if top_k_data_props is not None:
            new_data_props = {
                qual: {prop: lst1[:top_k_data_props] for prop, lst1 in dict1.items()}
                for qual, dict1 in new_data_props.items()
            }
        if top_k_object_props is not None:
            new_object_props = {
                k: lst1[:top_k_object_props] for k, lst1 in new_object_props.items()
            }

        return GraphSpace(new_data_props, new_object_props)

    def get_space_as_df(
        self,
        dataset: str,
        top_k_data_props: Optional[int] = None,
        top_k_object_props: Optional[int] = None,
    ):
        kgdb = self.data_actor.get_kgdb(dataset)
        kgns = kgdb.kgns
        classes = kgdb.pydb.classes.cache()
        props = kgdb.pydb.props.cache()

        fmt_pid = lambda pid: (
            f"{pid} ({props[pid].label})"
            if kgns.has_encrypted_name(pid)
            else kgns.get_rel_uri(kgns.id_to_uri(pid))
        )
        fmt_cid = lambda cid: (
            f"{cid} ({classes[cid].label})"
            if kgns.has_encrypted_name(cid)
            else kgns.get_rel_uri(kgns.id_to_uri(cid))
        )

        gspace = self(dataset, top_k_data_props, top_k_object_props)
        data_props, object_props = gspace.data_props, gspace.object_props
        return pd.DataFrame(
            [
                {
                    "prop": fmt_pid(prop),
                    "qual": fmt_pid(qual) if qual is not None else None,
                    "source_type": fmt_cid(item.source_type),
                    "target_type": (
                        fmt_cid(item.target_type)
                        if item.target_type is not None
                        else None
                    ),
                    "freq": item.freq,
                    "inherit_freq": item.inherit_freq,
                    "total_freq": item.total_freq,
                }
                for qual in data_props
                for prop, lst in data_props[qual].items()
                for item in lst
            ]
        ), pd.DataFrame(
            [
                {
                    "prop": fmt_pid(item.prop),
                    "qual": fmt_pid(item.qual) if item.qual is not None else None,
                    "source_type": fmt_cid(source_type),
                    "target_type": fmt_cid(target_type),
                    "freq": item.freq,
                    "inherit_freq": item.inherit_freq,
                    "total_freq": item.total_freq,
                }
                for (source_type, target_type), lst in object_props.items()
                for item in lst
            ]
        )

    @Cache.cache(backend=MemBackend())
    def get_predicate_conns(self, dataset: str):
        kgname = self.data_actor.get_kgname(dataset)
        if kgname == KGName.Wikidata:
            return wikidata_get_predicate_conn_dataset(with_dep=False).get_list()
        if kgname == KGName.DBpedia:
            return dbpedia_get_predicate_conn_dataset(with_dep=False).get_list()
        raise NotImplementedError(f"kgname={kgname}")

    @Cache.cache(backend=MemBackend())
    def get_gold_schema(
        self,
        dataset: str,
    ) -> tuple[set[str], set[str]]:
        """Get classes and predicates that are in the gold models."""
        examples = self.data_actor(dataset)
        kgdb = self.data_actor.get_kgdb(dataset)
        kgns = kgdb.kgns

        used_props = set()
        used_classes = set()

        for ex in examples:
            for sm in ex.sms:
                for edge in sm.iter_edges():
                    if not kgns.is_uri_in_main_ns(edge.abs_uri):
                        continue
                    pid = kgns.uri_to_id(edge.abs_uri)
                    used_props.add(pid)

                for node in sm.iter_nodes():
                    if not isinstance(node, O.ClassNode):
                        continue
                    if not kgns.is_uri_in_main_ns(node.abs_uri):
                        continue
                    cid = kgns.uri_to_id(node.abs_uri)
                    used_classes.add(cid)
        return used_props, used_classes
