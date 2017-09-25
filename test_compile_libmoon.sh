#!/bin/bash
set -e

export DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export TEST_ID="compile_libmoon"

if [ -e "${DIR}/conf_compile_libmoon.sh" ]; then
    echo "Loading configuration..."
    . "${DIR}/conf_compile_libmoon.sh"
fi

# set default parameters
if [ -z "$TEST_IMAGE" ]; then
    export TEST_IMAGE="ubuntu-16.04"
fi

mkdir -p "${LOG_DIR}"

RSYNC_OPT="--info=progress2 --no-inc-recursive -acz -e ssh --delete"

# validate required parameters
if [ -z "$HOST_A" ]; then
    echo "Need to set HOST_A to the name of test host"
    exit 1
fi
if [ -z "$HOST_B" ]; then
    echo "Need to set HOST_B to the name of test host"
    exit 1
fi
if [ -z "$LIBMOON_DIR" ]; then
    echo "Need to set LIBMOON_DIR to the path of libmoon"
    exit 1
fi
if [ -z "$BENCHMARKS_DIR" ]; then
    echo "Need to set BENCHMARKS_DIR to the path of benchmarks' source code"
    exit 1
fi

if [ -z "$SKIP_TESTBED_BOOT" ]; then
    # boot hosts
    . "${DIR}/support/boot_hosts.sh"
fi

HOSTS="$HOST_A $HOST_B"

# create test directory
ssh $HOST_A "mkdir -p $TEST_DIR"

# upload support scripts
echo "Uploading support scripts..."
export SUPPORT_DIR=${DIR}/support/
export REMOTE_SUPPORT_DIR=$TEST_DIR/support
. "${DIR}/support/upload_support.sh"

# upload libmoon and compile it
echo "Uploading libmoon source code to $HOST_A..."
ssh $HOST_A "mkdir -p $TEST_DIR/libmoon"
rsync $RSYNC_OPT ${LIBMOON_DIR}/ $HOST_A:$TEST_DIR/libmoon

echo "Installing dependencies on $HOST_A..."
ssh $HOST_A "$TEST_DIR/support/install_deps_libmoon.sh"
echo "Compiling libmoon on $HOST_A..."
ssh $HOST_A "LIBMOON_DIR=$TEST_DIR/libmoon $TEST_DIR/support/compile_libmoon.sh"

# upload benchmark and compile it
echo "Uploading benchmark source code to $HOST_B..."
rsync $RSYNC_OPT ${BENCHMARKS_DIR}/ $HOST_B:$TEST_DIR/benchmarks

echo "Installing dependencies on $HOST_B..."
ssh $HOST_B "$TEST_DIR/support/install_deps_benchmarks.sh"
echo "Compiling benchmark on $HOST_B"
ssh $HOST_B "BENCHMARKS_DIR=$TEST_DIR/benchmarks $TEST_DIR/support/compile_benchmarks.sh"
