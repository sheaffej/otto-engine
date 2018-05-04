#!/bin/bash

PYTEST="pytest -v"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

# Start otto-engine
echo "Starting otto-engine ["$(date)"]"
./run_otto.py &> /dev/null &
sleep 2

# Run Python unit tests
${PYTEST} tests/integration/

# Shutdown otto-engine
echo "Stopping otto-engine ["$(date)"]"
kill -9 $(ps | grep run_otto.py | grep -v grep | awk '{print $1}')
