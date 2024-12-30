import os
from collections import defaultdict
from functools import partial
from io import StringIO
from pathlib import Path
from typing import cast

import orjson
from drepr.models.prelude import DRepr
from kgdata.dataset import Dataset
from kgdata.db import GenericDB, build_database, deser_from_dict, ser_to_dict
from kgdata.dbpedia.datasets.ontology_dump import aggregated_triples
from kgdata.misc.resource import RDFResource, assert_not_bnode
from kgdata.models.entity import Entity, EntityLabel, Statement
from kgdata.models.multilingual import MultiLingualString, MultiLingualStringList
from kgdata.spark.extended_rdd import ExtendedRDD
from rdflib import RDFS, SKOS, Graph
from tum.config import (
    CRITICAL_MAAS_DIR,
    DATA_DIR,
    DATA_REPO,
    KG_ETL_FILE,
    KG_OUTDIR,
    ONTOLOGY_FILE,
)
from tum.db import MNDRDB

from statickg.main import ETLPipelineRunner
from statickg.models.etl import ETLOutput
from statickg.models.repository import GitRepository
from statickg.services.drepr import DReprService, DReprServiceInvokeArgs

kgbuilder = ETLPipelineRunner.from_config_file(
    KG_ETL_FILE,
    KG_OUTDIR,
    GitRepository(DATA_REPO),
    overwrite_config=False,
)


def get_rdf_resources(ttl_file: Path) -> list[RDFResource]:
    g = Graph()
    g.parse(ttl_file, format="ttl")

    source2triples = defaultdict(list)
    for s, p, o in g:
        source2triples[s].append((s, p, o))

    resources = [aggregated_triples(x) for x in source2triples.items()]
    return resources


def entities():
    ds = Dataset(
        DATA_DIR / "entities/*.gz",
        deserialize=partial(deser_from_dict, Entity),
        name="entities",
        dependencies=[],
    )

    if not ds.has_complete_data():
        # execute task that generates entities
        (task,) = [
            task
            for task in kgbuilder.etl.pipeline
            if task.service == "predefined entities"
        ]
        args: DReprServiceInvokeArgs = cast(DReprServiceInvokeArgs, task.args)
        kgbuilder.services[task.service](kgbuilder.repo, args, ETLOutput())

        entities = []
        for dpath in args["output"].get_path().iterdir():
            for resource in get_rdf_resources(dpath):
                (label,) = resource.props.pop(str(RDFS.label))
                (description,) = resource.props.pop(str(RDFS.comment), [""])
                aliases = [str(x) for x in resource.props.pop(str(SKOS.altLabel), [])]

                entities.append(
                    Entity(
                        id=resource.id,
                        label=MultiLingualString.en(str(label)),
                        description=MultiLingualString.en(description),
                        aliases=MultiLingualStringList({"en": aliases}, "en"),
                        props={
                            pid: [
                                Statement(assert_not_bnode(value), {}, [])
                                for value in values
                            ]
                            for pid, values in resource.props.items()
                        },
                    )
                )
        entities = [orjson.dumps(e.to_dict()) for e in entities]
        ExtendedRDD.parallelize(entities).save_like_dataset(
            ds, trust_dataset_dependencies=True
        )

    return ds


def classes():
    ds = Dataset(
        DATA_DIR / "classes/*.gz",
        deserialize=partial(deser_from_dict, Entity),
        name="classes",
        dependencies=[],
    )

    if not ds.has_complete_data():
        classes, props, _ = MNDRDB.parse_ontology(ONTOLOGY_FILE)
        classes = [orjson.dumps(e.to_dict()) for e in classes.values()]
        ExtendedRDD.parallelize(classes).save_like_dataset(
            ds, trust_dataset_dependencies=True
        )

    return ds


def props():
    ds = Dataset(
        DATA_DIR / "props/*.gz",
        deserialize=partial(deser_from_dict, Entity),
        name="props",
        dependencies=[],
    )

    if not ds.has_complete_data():
        classes, props, _ = MNDRDB.parse_ontology(ONTOLOGY_FILE)
        props = [orjson.dumps(e.to_dict()) for e in props.values()]
        ExtendedRDD.parallelize(props).save_like_dataset(
            ds, trust_dataset_dependencies=True
        )

        print(props)
    return ds


def entity_labels() -> Dataset[EntityLabel]:
    ds = Dataset(
        DATA_DIR / "entity_labels/*.gz",
        deserialize=partial(deser_from_dict, EntityLabel),
        name="entity-labels",
        dependencies=[entities()],
    )

    if not ds.has_complete_data():
        (
            entities()
            .get_extended_rdd()
            .map(lambda ent: EntityLabel(ent.id, str(ent.label)))
            .map(ser_to_dict)
            .save_like_dataset(ds, auto_coalesce=True, shuffle=True)
        )
    return ds


if __name__ == "__main__":
    # import dotenv

    # dotenv.load_dotenv(
    #     Path(__file__).parent.parent / "scripts/geochem.env", override=True
    # )

    for ds in ["entities", "classes", "props", "entity_labels"]:
        build_database(
            f"tum.make_db.{ds}",
            lambda: getattr(GenericDB(DATA_DIR / "databases", read_only=False), ds),
            compact=True,
        )
