#!/usr/bin/env bash

IMAGE_NAME=otto-engine
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker build -t $IMAGE_NAME $DIR/..
