#!/usr/bin/env bash

CONTAINER_NAME=otto-engine

docker run --rm \
-e PYTEST_ADDOPTS="--color=yes" \
-v `pwd`/..:/app \
$CONTAINER_NAME /app/tests/run_tests.sh $1
