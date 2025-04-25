# Overview

This library provides algorithms for creating semantic descriptions of mineral-related tables for data extraction. It also integrates with [SAND](https://github.com/usc-isi-i2/sand) to interactively curate the semantic descriptions.

## Installation

### MinMod KG Setup

To work with [MinMod KG](https://minmod.isi.edu/), we need the [ta2-minmod-data](https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data) and [ta2-minmod-kg](https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg) repositories, and the default folder structure is:

    <DARPA-CRITICALMAAS-DIR>
    ├── data                      # for storing databases
    ├── ta2-minmod-data           # ta2-minmod-data repository
    ├── ta2-minmod-kg             # ta2-minmod-kg repository
    └── ta2-table-understanding   # ta2-table-understanding repository

To setup the above structure, you can run:

```
git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data
git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg
git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-table-understanding
mkdir data
```

To make it easier to run the next commands, we will use an environment variable `MINMOD_DIR` to denote the `<DARPA-CRITICALMAAS-DIR>` folder. If you are in the `<DARPA-CRITICALMAAS-DIR>` directory, you can run this command to set up the environment variable:

```bash
export MINMOD_DIR=$(pwd)
```

Note: The folder structure is fully customizable. Please see the [Configuration Section](#Configuration) for more information.

### Setup dependencies

We use [poetry](https://python-poetry.org/) as our package manager (you need to have it installed on your machine first). To install the library and its dependencies, run `poetry install` in the root directory of this repository. Then, you can run `poetry shell` to activate the virtual environment or use `poetry run <command>` to run the commands in the virtual environment.

```
cd ta2-table-understanding
python -m venv .venv
poetry install
cd ..
```

With the working folder structure setup, we can build the necessary databases (entities, ontology classes, and properties) by running:

```bash
export CFG_FILE=$MINMOD_DIR/ta2-minmod-kg/config.yml.template
cd ta2-table-understanding
poetry run python -m tum.make_db [--project <project=minmod>]
cd ..
```

Alternatively, you can use Docker to install the library:

```bash
cd ta2-table-understanding
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
docker compose build
cd ..
```

Then, you can run the command in Docker:

```bash
docker compose run --rm sand python -m tum.make_db
```

## Usage

How to model and publish data to MinMod Knowledge Graph: https://www.youtube.com/watch?v=iAZeKYzepSg

### API

Check out the [demo notebook](examples/demo.ipynb) on how to use the library programmatically.

### GUI

Alternatively, you can use the [SAND UI](https://github.com/usc-isi-i2/sand) to interactively load a table, create the semantic description, and extract data from the table.

To install SAND, you can run the following commands:

```bash
poetry run pip install web-sand sand-drepr
```

1. Setup SAND (run only once): `poetry run python -m sand init -d $MINMOD_DIR/data/minmod/sand.db`
2. Start SAND: `poetry run python -m sand start -d $MINMOD_DIR/data/minmod/sand.db -c $MINMOD_DIR/ta2-table-understanding/minmod.sand.yml`

If you use Docker, you can run:

```bash
docker compose run --rm sand python -m sand init -d /home/criticalmaas/data/minmod/sand.db
docker compose up
```

## Configuration

1. The working folder `<DARPA-CRITICALMAAS-DIR>` can be modified by setting the environment variable `CRITICAL_MAAS_DIR`.
2. To customize SAND, you can update the file [minmod.sand.yaml](./minmod.sand.yaml)
3. Training data to the model is stored under [data/training_set](./data/training_set) folder
