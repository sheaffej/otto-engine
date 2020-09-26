#!/usr/bin/env bash
set -e

IMAGE_NAME=sheaffej/otto-engine
CONTAINER_NAME=otto-engine

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo
echo "~~~~~~~~~~~~~~~~~~"
echo "Running Unit Tests"
echo "~~~~~~~~~~~~~~~~~~"
docker run --rm \
-v $MYDIR/..:/app \
$IMAGE_NAME \
pytest -v --cov=ottoengine /app/tests/unit

# Exit if only running unit tests
if [[ $1 == 'unit' ]]; then
    exit
fi


echo
echo "~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Running Integration Tests"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~"
docker rm -f $CONTAINER_NAME 2> /dev/null
docker run -d --name $CONTAINER_NAME $IMAGE_NAME /app/run_otto.py test
sleep 1
docker exec -it $CONTAINER_NAME pytest -v /app/tests/integration
docker exec -it $CONTAINER_NAME bash -c "ls -la /app; ls -la /config"
docker stop $CONTAINER_NAME

echo
echo "To see otto-engine logs:  docker logs otto-engine"
echo
