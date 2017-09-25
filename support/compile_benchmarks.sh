#!/bin/bash

SCRIPT="$( basename "${BASH_SOURCE[0]}" )"

if [ ! -d "$BENCHMARKS_DIR" ]; then
  echo "[$SCRIPT] Directory for benchmakrs does not exist: $BENCHMARKS_DIR"
fi

pushd .

# compile libmoon

echo "[$SCRIPT] Compiling benchmarks from $BENCHMARKS_DIR..."
cd $BENCHMARKS_DIR

# switch to gcc-6 so we have the same compiler that we used for development
export CC=gcc-6
export GCC=g++-6

./build.sh

popd