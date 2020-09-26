#!/usr/bin/env bash

IMAGE_NAME=sheaffej/otto-engine

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

pushd $MYDIR
docker build -t $IMAGE_NAME .
