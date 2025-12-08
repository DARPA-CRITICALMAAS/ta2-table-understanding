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

if [ ! -d "$PROJECT_DIR/volumes/certs" ]; then
    mkdir -p $PROJECT_DIR/volumes/certs
    cd $PROJECT_DIR/volumes/certs
    openssl req -x509 -newkey rsa:4096 -keyout privkey.pem -out fullchain.pem -sha256 -days 3650 -nodes -subj "/C=XX/ST=StateName/L=CityName/O=CompanyName/OU=CompanySectionName/CN=CommonNameOrHostname"
fi

HTPASSWD_FILE="$PROJECT_DIR/volumes/certs/.htpasswd"
if [ ! -f "$HTPASSWD_FILE" ]; then
    USERNAME="sand"
    PASSWORD=$(openssl rand -base64 12)

    if command -v htpasswd >/dev/null 2>&1; then
        htpasswd -B -b -c "$HTPASSWD_FILE" "$USERNAME" "$PASSWORD"
    elif command -v openssl >/dev/null 2>&1; then
        HASH=$(openssl passwd -apr1 "$PASSWORD")
        printf '%s:%s\n' "$USERNAME" "$HASH" > "$HTPASSWD_FILE"
    else
        printf '%s:%s\n' "$USERNAME" "$PASSWORD" > "$HTPASSWD_FILE"
        echo "Warning: neither htpasswd nor openssl found; storing plaintext password" >&2
    fi

    chmod 600 "$HTPASSWD_FILE"
    echo "Created $HTPASSWD_FILE (user: $USERNAME). Password: $PASSWORD"
fi