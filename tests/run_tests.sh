#!/bin/bash

PYTEST="pytest -v"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

# Ensure Home Assistant is running
HASS_PID=$(ps | grep python | grep hass | grep -v grep | cut -d " " -f 1)
if [[ -z $HASS_PID ]]; then
    echo
    echo "Home Assistant is not running...exiting"
    echo
    exit 1
fi

# Start otto-engine
echo "Starting otto-engine ["$(date)"]"
./run_otto.py &> /dev/null &
sleep 2

# Run Python unit tests
${PYTEST} tests/integration/test_rule_persistence.py

# Shutdown otto-engine
echo "Stopping otto-engine ["$(date)"]"
kill -9 $(ps | grep run_otto.py | grep -v grep | cut -d " " -f 1)
