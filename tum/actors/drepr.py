from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from pathlib import Path as PathlibPath
from typing import Annotated, Callable, Mapping

from kgdata.models import Ontology
from libactor.actor import Actor
from libactor.cache import BackendFactory, IdentObj, cache
from rdflib import XSD
from slugify import slugify
from sm.inputs.table import ColumnBasedTable
from sm.outputs.semantic_model import (
    ClassNode,
    DataNode,
    LiteralNode,
    LiteralNodeDataType,
    SemanticModel,
)

import drepr.models.sm as drepr_sm
from drepr.main import convert
from drepr.models.prelude import (
    AlignedStep,
    Alignment,
    Attr,
    CSVProp,
    DRepr,
    IndexExpr,
    OutputFormat,
    Path,
    PMap,
    Preprocessing,
    PreprocessingType,
    RangeAlignment,
    RangeExpr,
    Resource,
    ResourceDataString,
    ResourceType,
)


@dataclass
class DReprArgs:
    outdir: Path
    output_format: OutputFormat
    ident_props: Annotated[
        set[str],
        "list of properties that telling a data node contains entities (e.g., rdfs:label)",
    ] = field(default_factory=set)


class DReprActor(Actor[DReprArgs]):
    VERSION = 102

    def forward(
        self,
        table: IdentObj[ColumnBasedTable],
        sm: IdentObj[SemanticModel],
        ontology: IdentObj[Ontology],
    ) -> str:
        drepr = self.make_drepr_model(table, sm, ontology)
        if len(table.value.columns) == 0:
            # no column, no data
            return ""

        ent_columns = {
            node.col_index
            for node in get_entity_data_nodes(sm.value, self.params.ident_props)
        }
        resources = {
            "table": ResourceDataString(table.value.df.to_csv(index=False)),
            # "entity": get_entity_resource(
            #     self.appcfg, self.namespace, table, rows, ent_columns
            # ),
        }

        content = convert(
            repr=drepr,
            resources=resources,
            format=self.params.output_format,
        )
        assert isinstance(content, str)
        return content

    @cache(
        backend=BackendFactory.actor.sqlite.pickle(mem_persist=True),
    )
    def make_drepr_model(
        self,
        table_: IdentObj[ColumnBasedTable],
        sm_: IdentObj[SemanticModel],
        ontology_: IdentObj[Ontology],
    ) -> DRepr:
        table = table_.value
        sm = sm_.value
        ontology = ontology_.value

        nrows, ncols = table.shape()
        existing_attr_names = {}

        def get_attr_id(ci):
            cname = slugify(table.get_column_by_index(ci).clean_name).replace("-", "_")
            if cname == "":
                return "col_" + str(ci)
            if cname[0].isdigit():
                cname = "_" + cname

            m = re.match(r"\d+([^\d].*)", cname)
            if m is not None:
                cname = m.group(1)
            if existing_attr_names.get(cname, None) != ci:
                return cname + "_" + str(ci)

            existing_attr_names[cname] = ci
            return cname

        get_ent_attr_id = lambda ci: f"{get_attr_id(ci)}__ent"
        ent_dnodes = get_entity_data_nodes(sm, self.params.ident_props)

        attrs = [
            Attr(
                id=get_attr_id(col.index),
                resource_id="table",
                path=Path(
                    steps=[
                        RangeExpr(start=1, end=nrows + 1, step=1),
                        IndexExpr(val=col.index),
                    ]
                ),
                missing_values=[""],
            )
            for col in table.columns
        ]
        # attrs += [
        #     Attr(
        #         id=get_ent_attr_id(node.col_index),
        #         resource_id="entity",
        #         path=Path(
        #             steps=[
        #                 RangeExpr(start=1, end=nrows + 1, step=1),
        #                 IndexExpr(val=node.col_index),
        #             ]
        #         ),
        #         missing_values=[""],
        #     )
        #     for node in ent_dnodes
        # ]

        dsm = get_drepr_sm(
            sm=sm,
            ontology=ontology,
            ident_props=self.params.ident_props,
            get_attr_id=get_attr_id,
            get_ent_attr_id=get_ent_attr_id,
        )

        datatype_transformations = []
        for node in sm.nodes():
            if not isinstance(node, DataNode):
                continue

            datatypes: set = {
                ontology.props[ontology.kgns.uri_to_id(inedge.abs_uri)].datatype
                for inedge in sm.in_edges(node.id)
            }
            datatype = list(datatypes)[0] if len(datatypes) == 1 else None
            if datatype is None or not has_transformation(datatype):
                continue
            datatype_transformations.append(
                Preprocessing(
                    type=PreprocessingType.pmap,
                    value=PMap(
                        resource_id="table",
                        path=Path(
                            steps=[
                                RangeExpr(start=1, end=nrows + 1, step=1),
                                IndexExpr(val=node.col_index),
                            ]
                        ),
                        code=get_transformation(datatype),
                        change_structure=False,
                    ),
                )
            )

        aligns: list[Alignment] = []
        for ci in range(1, len(table.columns)):
            aligns.append(
                RangeAlignment(
                    source=get_attr_id(table.columns[0].index),
                    target=get_attr_id(table.columns[ci].index),
                    aligned_steps=[AlignedStep(source_idx=0, target_idx=0)],
                )
            )
        for node in ent_dnodes:
            aligns.append(
                RangeAlignment(
                    source=get_attr_id(table.columns[0].index),
                    target=get_ent_attr_id(node.col_index),
                    aligned_steps=[AlignedStep(source_idx=0, target_idx=0)],
                )
            )

        return DRepr(
            resources=[
                Resource(id="table", type=ResourceType.CSV, prop=CSVProp()),
                # Resource(id="entity", type=ResourceType.CSV, prop=CSVProp()),
            ],
            preprocessing=datatype_transformations,
            attrs=attrs,
            aligns=aligns,
            sm=dsm,
        )


def get_drepr_sm(
    sm: SemanticModel,
    ontology: Ontology,
    ident_props: set[str],
    get_attr_id: Callable[[int], str],
    get_ent_attr_id: Callable[[int], str],
) -> drepr_sm.SemanticModel:
    """Convert sm model into drepr model.

    Args:
        sm: the semantic model we want to convert
        kgns: the knowledge graph namespace
        kgns_prefixes: the prefixes of the knowledge graph namespace
        ontprop_ar: mapping from the id to ontology property
        ident_props: list of properties that telling a data node contains entities (e.g., rdfs:label)
        get_attr_id: get attribute id from column index
        get_ent_attr_id: for each entity column, to generate url, we create an extra attribute containing the entity uri, this function get its id based on the column index
    """
    nodes = {}
    edges = {}

    for node in sm.nodes():
        if isinstance(node, ClassNode):
            nodes[str(node.id)] = drepr_sm.ClassNode(
                node_id=str(node.id), label=node.rel_uri
            )
        elif isinstance(node, DataNode):
            # find data type of this node, when they have multiple data types
            # that do not agree with each other, we don't set the datatype
            # usually, that will be displayed from the UI so users know that
            datatypes = set()
            for inedge in sm.in_edges(node.id):
                datatype = ontology.props[
                    ontology.kgns.uri_to_id(inedge.abs_uri)
                ].datatype
                if datatype == "":
                    continue
                datatype = drepr_sm.DataType(datatype, ontology.kgns.prefix2ns)
                datatypes.add(datatype)

            nodes[str(node.id)] = drepr_sm.DataNode(
                node_id=str(node.id),
                attr_id=get_attr_id(node.col_index),
                data_type=next(iter(datatypes)) if len(datatypes) == 1 else None,
            )
        elif isinstance(node, LiteralNode):
            if node.datatype == LiteralNodeDataType.Entity:
                datatype = drepr_sm.PredefinedDataType.drepr_uri.value
            else:
                assert node.datatype == LiteralNodeDataType.String
                datatype = drepr_sm.PredefinedDataType.xsd_string.value

            nodes[str(node.id)] = drepr_sm.LiteralNode(
                node_id=str(node.id), value=node.value, data_type=datatype
            )

    used_ids = {x for edge in sm.edges() for x in [str(edge.source), str(edge.target)]}
    for node_id in set(nodes.keys()).difference(used_ids):
        del nodes[node_id]

    for edge in sm.edges():
        edges[len(edges)] = drepr_sm.Edge(
            edge_id=len(edges),
            source_id=str(edge.source),
            target_id=str(edge.target),
            label=edge.rel_uri,
        )

    # print(edges)

    # add drepr:uri relationship
    for node in get_entity_data_nodes(sm, ident_props):
        new_node_id = str(node.id) + ":ents"
        nodes[new_node_id] = drepr_sm.DataNode(
            node_id=new_node_id,
            attr_id=get_ent_attr_id(node.col_index),
            data_type=drepr_sm.PredefinedDataType.drepr_uri.value,
        )
        inedges = [
            inedge for inedge in sm.in_edges(node.id) if inedge.abs_uri in ident_props
        ]
        assert len(inedges) == 1
        inedge = inedges[0]
        edges[len(edges)] = drepr_sm.Edge(
            edge_id=len(edges),
            source_id=str(inedge.source),
            target_id=new_node_id,
            # special predicate telling drepr to use as uri of entity, instead of generating a blank node
            label="drepr:uri",
        )

    prefixes = ontology.kgns.prefix2ns.copy()
    prefixes.update(drepr_sm.SemanticModel.get_default_prefixes())
    return drepr_sm.SemanticModel(
        nodes=nodes,
        edges=edges,
        prefixes=prefixes,
    )


def get_entity_data_nodes(sm: SemanticModel, ident_props: set[str]) -> list[DataNode]:
    ent_dnodes = []
    for node in sm.iter_nodes():
        if not isinstance(node, DataNode):
            continue

        stypes = sm.get_semantic_types_of_column(node.col_index)
        if any(stype.predicate_abs_uri in ident_props for stype in stypes):
            ent_dnodes.append(node)

    return ent_dnodes


transdir = (PathlibPath(__file__).parent / "raw_transformations").absolute()

datatype2transformation: Mapping[str, PathlibPath] = {
    "http://www.opengis.net/ont/geosparql#wktLiteral": (
        transdir / "global_coordinate.py"
    ),
    str(XSD.int): (transdir / "integer-number.py"),
    str(XSD.decimal): (transdir / "decimal-number.py"),
}

loaded_transformations: dict[str, str] = {}


def get_transformation(datatype: str):
    global loaded_transformations
    if datatype not in loaded_transformations:
        loaded_transformations[datatype] = datatype2transformation[datatype].read_text()
    return loaded_transformations[datatype]


def has_transformation(datatype: str):
    return datatype in datatype2transformation
