FROM python:3.12-slim

# Install required system libraries
RUN apt update && apt install -y ca-certificates curl git lz4 openjdk-21-jre build-essential

ARG UID=1000
ARG GID=1000

RUN groupadd -f -g $GID criticalmaas && useradd -ms /bin/bash criticalmaas -u $UID -g $GID

USER criticalmaas
WORKDIR /home/criticalmaas

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
# Install UV
RUN pip install uv

ENV PATH="/home/criticalmaas/.local/bin:/home/criticalmaas/.cargo/bin:${PATH}"

# Install dependencies
ADD --chown=$UID:$GID pyproject.toml /home/criticalmaas/tum/
ADD --chown=$UID:$GID uv.lock /home/criticalmaas/tum/
ADD --chown=$UID:$GID README.md /home/criticalmaas/tum/

RUN mkdir -p /home/criticalmaas/tum/tum && \
    touch /home/criticalmaas/tum/tum/__init__.py && \
    cd /home/criticalmaas/tum && uv sync --group sand

# Setup MinMod KG
RUN git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data && \
    git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg && \
    mkdir data

ARG DATA_REPO_COMMIT_ID
ARG KG_REPO_COMMIT_ID

RUN cd ta2-minmod-data && \
    git fetch --depth 1 origin ${DATA_REPO_COMMIT_ID} && \
    ( [ -z "${DATA_REPO_COMMIT_ID}" ] || git checkout ${DATA_REPO_COMMIT_ID} )

RUN cd ta2-minmod-kg && \
    git fetch --depth 1 origin ${KG_REPO_COMMIT_ID} && \
    ( [ -z "${KG_REPO_COMMIT_ID}" ] || git checkout ${KG_REPO_COMMIT_ID} )


ENV CFG_FILE=/home/criticalmaas/ta2-minmod-kg/config.yml.template

# Setup necessary data for SAND to work with MinMod KG
ADD --chown=$UID:$GID tum /home/criticalmaas/tum/tum
ADD --chown=$UID:$GID schema /home/criticalmaas/tum/schema
ADD --chown=$UID:$GID minmod.sand.yml /home/criticalmaas/tum/
ADD --chown=$UID:$GID geochem.sand.yml /home/criticalmaas/tum/
ADD --chown=$UID:$GID data/gpp /home/criticalmaas/data/gpp

# setup MinMod
RUN uv run --project tum python -m tum.make_db --project minmod && \
    uv run --project tum python -m sand init -d ./data/minmod/sand.db

# setup Geochem
RUN ONTOLOGY_FILE=/home/criticalmaas/tum/schema/geochem.ttl uv run --project tum python -m tum.make_db --project geochem && \
    uv run --project tum python -m sand init -d ./data/geochem/sand.db

ADD --chown=$UID:$GID data/minmod/units_and_commodities.json /home/criticalmaas/data/minmod