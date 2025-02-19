# Overview

This library provides algorithms for creating semantic descriptions of mineral-related tables for data extraction. It also integrates with [SAND](https://github.com/usc-isi-i2/sand) to interactively curate the semantic descriptions.

## Installation

### MinMod KG Setup

To work with [MinMod KG](https://minmod.isi.edu/), we need the [ta2-minmod-data](https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data), and the default folder structure is:

    <DARPA-CRITICALMAAS-DIR>
    ├── data                      # for storing databases
    ├── ta2-minmod-data           # ta2-minmod-data repository
    └── ta2-table-understanding   # ta2-table-understanding repository

To setup the above structure, you can run:

```
git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data
git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg
git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-table-understanding
mkdir data
```

Note: The folder structure is fully customizable. Please see the [Configuration Section](#Configuration) for more information.

### Setup dependencies

We use [poetry](https://python-poetry.org/) as our package manager (you need to have it installed on your machine first). To install the library and its dependencies, run `poetry install` in the root directory of this repository. Then, you can run `poetry shell` to activate the virtual environment or use `poetry run <command>` to run the commands in the virtual environment.

```
cd ta2-table-understanding
python -m venv .venv
poetry install
```

With the working folder structure setup, we can build the necessary databases (entities, ontology classes, and properties) by running `poetry run python -m tum.make_db`

Alternatively, you can use Docker to install the library:

```bash
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
docker compose build
```

## Usage

How to model and publish data to MinMod Knowledge Graph: https://www.youtube.com/watch?v=iAZeKYzepSg

### API

Check out the [demo notebook](examples/demo.ipynb) on how to use the library programmatically.

### GUI

Alternatively, you can use the [SAND UI](https://github.com/usc-isi-i2/sand) to interactively load a table, create the semantic description, and extract data from the table.

To install SAND, you can run the following commands:

```
pip install web-sand sand-drepr
```

1. Setup SAND (run only once): `poetry run python -m sand init -d <DARPA-CRITICALMAAS-DIR>/data/minmod/sand.db`
2. Start SAND: `poetry run python -m sand start -d <DARPA-CRITICALMAAS-DIR>/data/minmod/sand.db -c <DARPA-CRITICALMAAS-DIR>/ta2-table-understanding/minmod.sand.yml`

## Configuration

1. The working folder `<DARPA-CRITICALMAAS-DIR>` can be modified by setting the environment variable `CRITICAL_MAAS_DIR`.
2. To customize SAND, you can update the file [minmod.sand.yaml](./minmod.sand.yaml)
3. Training data to the model is stored under [data/training_set](./data/training_set) folder
