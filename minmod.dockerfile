FROM debian:bookworm-slim

# install required system libraries
RUN apt update && apt install -y ca-certificates curl git lz4

ARG UID=1000
ARG GID=1000

RUN groupadd -f -g $GID criticalmaas && useradd -ms /bin/bash criticalmaas -u $UID -g $GID

USER criticalmaas

WORKDIR /criticalmaas

RUN git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data && \
    git clone --depth 1 https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg && \
    mkdir data