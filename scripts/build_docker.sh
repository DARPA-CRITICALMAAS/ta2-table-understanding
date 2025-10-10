#!/bin/bash

set -e

SCRIPT_DIR=$(dirname "$0")
PROJECT_DIR=$(realpath "$SCRIPT_DIR/..")

export DATA_REPO_COMMIT_ID=$(git ls-remote "https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data.git" "refs/heads/main" | awk '{print $1}')
export KG_REPO_COMMIT_ID=$(git ls-remote "https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg.git" "refs/heads/main" | awk '{print $1}')
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

docker compose build

if [ ! -d "$PROJECT_DIR/volumes/data" ]; then
    mkdir -p $PROJECT_DIR/volumes/data
    container_id=$(docker run --rm -d minmod-sand sleep 60)
    docker cp "$container_id:/home/criticalmaas/data" $PROJECT_DIR/volumes/
    docker stop "$container_id"
fi