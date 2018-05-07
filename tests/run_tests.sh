#!/bin/bash

PYTEST="pytest -v"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

echo

# Start otto-engine
echo "Starting otto-engine ["$(date)"]"
./run_otto.py &> /dev/null &
echo "Waiting 5 seconds for Flask server to start..."
sleep 5

echo;echo;
echo "~~~~~ Running Unit Tests ~~~~~";echo
${PYTEST} tests/unit/

echo;echo;
echo "~~~~~ Running Integration Tests ~~~~~";echo
${PYTEST} tests/integration/

# Shutdown otto-engine
echo
echo "Stopping otto-engine ["$(date)"]"
kill -9 $(ps | grep run_otto.py | grep -v grep | awk '{print $1}')
echo
