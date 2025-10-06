FROM python:3.12-slim

# Install required system libraries
RUN apt update && apt install -y ca-certificates curl git lz4 openjdk-21-jre

ARG UID=1000
ARG GID=1000

RUN groupadd -f -g $GID criticalmaas && useradd -ms /bin/bash criticalmaas -u $UID -g $GID

USER criticalmaas
WORKDIR /home/criticalmaas

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/home/criticalmaas/.local/bin:/home/criticalmaas/.cargo/bin:${PATH}"

# Install dependencies
ADD --chown=$UID:$GID pyproject.toml /home/criticalmaas/tum/
ADD --chown=$UID:$GID README.md /home/criticalmaas/tum/

RUN mkdir -p /home/criticalmaas/tum/tum && \
    touch /home/criticalmaas/tum/tum/__init__.py && \
    cd /home/criticalmaas/tum && pip install . && \
    pip install web-sand sand-drepr  && \
    pip uninstall -y tum && \
    rm -rf tum

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
    git fetch --depth 1 origin ${KG_REPO_COMMIT_ID} \
    && ( [ -z "${KG_REPO_COMMIT_ID}" ] || git checkout ${KG_REPO_COMMIT_ID} )