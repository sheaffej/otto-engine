#!/bin/bash

PYTEST="pytest -v --cache-clear"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

echo
echo "Starting otto-engine ["$(date)"]"
./run_otto.py &> /dev/null &
echo

${PYTEST} --cov=ottoengine tests/

echo
echo "Stopping otto-engine ["$(date)"]"
kill -9 $(ps | grep run_otto.py | grep -v grep | awk '{print $1}')
echo
