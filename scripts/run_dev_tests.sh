#!/usr/bin/env bash

CONTAINER_NAME=otto-engine
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


docker run --rm \
-e PYTEST_ADDOPTS="--color=yes" \
-v $DIR/..:/app \
<<<<<<< HEAD
$CONTAINER_NAME bash -c "/app/tests/run_tests.sh $1; ls -la /app; ls -la /config"
=======
<<<<<<< HEAD
$CONTAINER_NAME /app/tests/run_tests.sh $1
=======
$CONTAINER_NAME bash -c "/app/tests/run_tests.sh $1; ls -la /app; ls -la /config"
>>>>>>> dev
>>>>>>> master
