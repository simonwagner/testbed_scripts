#!/bin/sh

# This is my local helper to download the results to my local computer

set -e

USER=wagnersi
HOST=kaunas

TESTBED_HOST=$1
TESTBED_RESULTS_PATH=/root/testbed/results/
RESULTS_FILE_PATH=$2

if [ -z "$TESTBED_HOST" ]; then
    echo "Missing test bed host name"
    echo ""
    echo "usage: $0 TESTBEDHOST RESULTSFILE"
    exit 0
fi

if [ -z "$RESULTS_FILE_PATH" ]; then
    echo "Missing results file"
    echo ""
    echo "usage: $0 TESTBEDHOST RESULTSFILE"
    exit 0
fi

echo "Downloading results from $TESTBED_HOST:$TESTBED_RESULTS_PATH to $RESULTS_FILE_PATH..."
ssh $USER@$HOST "ssh $TESTBED_HOST 'tar -C $TESTBED_RESULTS_PATH -czf - .'" > $RESULTS_FILE_PATH
echo "done"