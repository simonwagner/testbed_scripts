#!/bin/bash

SCRIPT="$( basename "${BASH_SOURCE[0]}" )"

if [ ! -d "$LIBMOON_DIR" ]; then
  echo "[$SCRIPT] Directory for libmoon does not exist: $LIBMOON_DIR"
fi

pushd .

# compile libmoon

echo "[$SCRIPT] Compiling libmoon from $LIBMOON_DIR (compile log is at $LIBMOON_DIR/build.log)..."
cd $LIBMOON_DIR

# switch to gcc-6 so we have the same compiler that we used for development
export CC=gcc-6
export GCC=g++-6

./build.sh > build.log 2>&1

# compile some of the sample apps from mTCP
pushd .

echo "[$SCRIPT] Compiling mtcp netcat  (compile log is at $PWD/deps/mtcp/apps/netcat/build.log)..."
cd deps/mtcp/apps/netcat
make > build.log 2>&1

popd

popd