#!/usr/bin/env bash

IMAGE="sheaffej/otto-engine"
CONTAINER_NAME="otto-engine"

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker rm -f $CONTAINER_NAME

docker run  -it \
--name $CONTAINER_NAME \
--net host \
-e TZ=$TZ \
-v $MYDIR/../config.ini:/config/config.ini:ro \
-v /home/jsheaffe/otto-rules:/json_rules:rw \
--restart always \
$IMAGE


