FROM python:3.11-slim

# install required system libraries
RUN apt update && apt install -y ca-certificates curl git lz4

ARG UID=1000
ARG GID=1000

RUN groupadd -f -g $GID criticalmaas && useradd -ms /bin/bash criticalmaas -u $UID -g $GID

USER criticalmaas

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/home/criticalmaas/.local/bin:/home/criticalmaas/.cargo/bin:${PATH}"

# install libraries
RUN mkdir -p /home/criticalmaas/tum/tum && \
    touch /home/criticalmaas/tum/tum/__init__.py
ADD pyproject.toml /home/criticalmaas/tum/
ADD README.md /home/criticalmaas/tum/

RUN cd /home/criticalmaas/tum && pip install .
RUN pip install web-sand sand-drepr

ADD --chown=criticalmaas:criticalmaas tum /home/criticalmaas/tum/tum

RUN cd /home/criticalmaas/tum && pip install .