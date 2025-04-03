#!/bin/sh
set -eo pipefail
project_name='token-dispenser'
poetry build

# Docker doesn't like relative paths on volumes
dist_path=$(realpath dist)

docker build -t token-dispenser-build build/
docker run --volume $dist_path:/dist token-dispenser-build
