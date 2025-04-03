#!/bin/bash
set -eo pipefail
pip install \
  --upgrade \
  -t /package \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --only-binary=:all: \
  /dist/*.whl

cd /package
zip -r /dist/token-dispenser_lambda.zip . -x '*.pyc'
