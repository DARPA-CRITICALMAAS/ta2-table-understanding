#!/bin/bash

set -e

export DATA_REPO_COMMIT_ID=$(git ls-remote "https://github.com/DARPA-CRITICALMAAS/ta2-minmod-data.git" "refs/heads/main" | awk '{print $1}')
export KG_REPO_COMMIT_ID=$(git ls-remote "https://github.com/DARPA-CRITICALMAAS/ta2-minmod-kg.git" "refs/heads/main" | awk '{print $1}')
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

docker compose build