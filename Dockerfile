FROM python:3.12-slim

# install required system libraries
RUN apt update && apt install -y ca-certificates curl git lz4

ARG UID=1000
ARG GID=1000

RUN groupadd -f -g $GID criticalmaas && useradd -ms /bin/bash criticalmaas -u $UID -g $GID
# add user to docker group
RUN usermod -aG docker criticalmaas

USER criticalmaas

ENV PATH="/home/criticalmaas/.local/bin:${PATH}"

# install libraries
RUN mkdir -p /home/criticalmaas/tum/tum && \
    touch /home/criticalmaas/tum/tum/__init__.py
ADD pyproject.toml /home/criticalmaas/tum/
ADD poetry.lock /home/criticalmaas/tum/
ADD README.md /home/criticalmaas/tum/

RUN cd /home/criticalmaas/tum && pip install .

ADD --chown=criticalmaas:criticalmaas tum /home/criticalmaas/tum/tum

RUN cd /home/criticalmaas/tum && pip install .