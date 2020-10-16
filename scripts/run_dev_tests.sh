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
-e TRAVIS_JOB_ID \
-e TRAVIS_BRANCH \
-e COVERALLS_REPO_TOKEN \
-v $MYDIR/..:/app \
$IMAGE_NAME \
pytest -v /app/tests/unit
# pytest -v --cov=ottoengine /app/tests/unit

# if [[ ! -z ${TRAVIS_JOB_ID} ]]; then
#     coveralls
# fi

# Exit if only running unit tests
if [[ $1 == 'unit' ]]; then
    exit
fi


echo
echo "~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Running Integration Tests"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~"
# Create the otto-engine server
docker rm -f $CONTAINER_NAME || echo
docker run -d --name $CONTAINER_NAME -v $MYDIR/../config.ini:/config/config.ini $IMAGE_NAME /app/run_otto.py test
sleep 1

# Run the integration tests against the server
docker exec -it $CONTAINER_NAME pytest -v /app/tests/integration

# Show output and clean up
docker exec -it $CONTAINER_NAME bash -c "ls -la /app; ls -la /config"
docker stop $CONTAINER_NAME
echo
echo "To see otto-engine logs:  docker logs otto-engine"
echo
