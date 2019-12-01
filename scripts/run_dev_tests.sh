#!/usr/bin/env bash

CONTAINER_NAME=otto-engine
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


docker run --rm \
-e PYTEST_ADDOPTS="--color=yes" \
-v $DIR/..:/app \
$CONTAINER_NAME /app/tests/run_tests.sh $1
