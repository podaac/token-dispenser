#!/bin/sh
project_name='token-dispenser'
poetry build
poetry run pip install --upgrade -t package dist/*.whl
cd package ; zip -r ../artifact.zip . -x '*.pyc'
cd ..
mv artifact.zip  ./dist/${project_name}_lambda.zip
rm -rf package
