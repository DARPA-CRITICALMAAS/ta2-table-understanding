# Overview

This library provides algorithms for creating semantic descriptions of mineral-related tables for data extraction. It also integrates with [SAND](https://github.com/usc-isi-i2/sand) to interactively curate the semantic descriptions.

## Installation

We use [poetry](https://python-poetry.org/) as our package manager (you need to have it installed on your machine first). To install the library and its dependencies, run `poetry install` in the root directory of this repository. Then, you can run `poetry shell` to activate the virtual environment or use `poetry run <command>` to run the commands in the virtual environment.

### MinMod KG Setup

To work with [MinMod KG](https://minmod.isi.edu/), we need the [ta2-minmod-data](https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data), and the default folder structure is:

    <DARPA-CRITICALMAAS-DIR>
    ├── data                      # for storing databases
    ├── ta2-minmod-data           # ta2-minmod-data repository
    └── ta2-table-understanding   # ta2-table-understanding repository

Note: The folder structure is fully customizable. Please see the [Configuration Section](#Configuration)

With the working folder structure setup, we can build the necessary databases (entities, ontology classes, and properties) by running `poetry run python -m tum.make_db`

## Usage

Check out the [demo notebook](examples/demo.ipynb) on programmatically using the library.

Alternatively, you can use the [SAND UI](https://github.com/usc-isi-i2/sand) to load a table, create the semantic description, and extract data from the table.

## Configuration

