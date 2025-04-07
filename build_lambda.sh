#!/bin/sh
set -eo pipefail
project_name='token-dispenser'
poetry build
poetry run pip install \
  --upgrade \
  -t build \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --only-binary=:all: \
  dist/*.whl

cd build
zip -r ../dist/token-dispenser_lambda.zip . -x '*.pyc'
