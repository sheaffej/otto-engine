#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR/..

echo
echo "~~~~~~~~~~~~~~~~~~"
echo "Running Unit Tests"
echo "~~~~~~~~~~~~~~~~~~"
pytest -v --cache-clear --cov=ottoengine tests/unit

# Exit if only running unit tests
if [[ $1 == 'unit' ]]; then
    exit
fi


echo
echo "~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Running Integration Tests"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~"

# Check that JSON_RULES_DIR is empty before proceeding
JSON_RULES_DIR=`grep JSON_RULES_DIR config.ini | cut -d'=' -f2`
if [ -n "$(ls $JSON_RULES_DIR/*.json 2>/dev/null)" ]; then 
    echo
    echo "Aborting: JSON Rules Dir is not empty"
    ls -1 $JSON_RULES_DIR/*.json
    echo
    exit 1
fi

echo
echo "Starting otto-engine ["$(date)"]"
./run_otto.py test &> run_otto.log &
# ./run_otto.py test 

# Let async engine setup complete before proceeding
sleep 1

echo
pytest -v --cache-clear tests/integration

