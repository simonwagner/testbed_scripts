#!/bin/bash

# This is my local helper to upload code to kaunas so that
# I can run tests with it
set -e

USER=wagnersi
HOST=kaunas

LIBMOON_DIR="/Users/simon/Dropbox/Studium/Masterarbeit/Code/libmoon"
BENCHMARK_DIR="/Users/simon/Dropbox/Studium/Masterarbeit/Code/benchmarks"
TESTBEDSCRIPTS_DIR="/Users/simon/Dropbox/Studium/Masterarbeit/Code/testbed_scripts"

RSYNC_OPT="--info=progress2 --no-inc-recursive -acz -e ssh --delete"

rsync $RSYNC_OPT $LIBMOON_DIR/ $USER@$HOST:~/Code/libmoon/
rsync $RSYNC_OPT $BENCHMARK_DIR/ $USER@$HOST:~/Code/benchmarks/
rsync $RSYNC_OPT $TESTBEDSCRIPTS_DIR/ $USER@$HOST:~/Code/testbed_scripts/