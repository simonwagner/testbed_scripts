#!/bin/bash
set -e

export DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export TEST_ID="throughput_mtcp"

if [ -e "${DIR}/conf_throughput_mtcp.sh" ]; then
    echo "Loading configuration..."
    . "${DIR}/conf_throughput_mtcp.sh"
fi

# set default parameters
if [ -z "$TEST_IMAGE" ]; then
    export TEST_IMAGE="ubuntu-16.04"
fi

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
else
    echo "Skipping reboot of testbed"
fi

HOSTS="$HOST_A $HOST_B"

mkdir -p "${LOG_DIR}"

# create test directory
ssh $HOST_A "mkdir -p $TEST_DIR"

# upload support scripts
echo "Uploading support scripts..."
export SUPPORT_DIR=${DIR}/support/
export REMOTE_SUPPORT_DIR=$TEST_DIR/support
. "${DIR}/support/upload_support.sh"

if [ -z "$SKIP_COMPILING" ]; then
    # upload libmoon and compile it
    echo "Uploading libmoon source code to $HOST_A..."
    ssh $HOST_A "mkdir -p $TEST_DIR/libmoon"
    rsync $RSYNC_OPT ${LIBMOON_DIR}/ $HOST_A:$TEST_DIR/libmoon
    export HOST_A_LIBMOON_DIR=$TEST_DIR/libmoon

    echo "Installing dependencies on $HOST_A..."
    ssh $HOST_A "$REMOTE_SUPPORT_DIR/install_deps_libmoon.sh"
    echo "Compiling libmoon on $HOST_A..."
    ssh $HOST_A "LIBMOON_DIR=$HOST_A_LIBMOON_DIR $TEST_DIR/support/compile_libmoon.sh"

    # upload benchmark and compile it
    echo "Uploading benchmark source code to $HOST_B..."
    rsync $RSYNC_OPT ${BENCHMARKS_DIR}/ $HOST_B:$TEST_DIR/benchmarks
    export HOST_B_BENCHMARKS_DIR=${TEST_DIR}/benchmarks

    echo "Installing dependencies on $HOST_B..."
    ssh $HOST_B "$TEST_DIR/support/install_deps_benchmarks.sh"
    echo "Compiling benchmark on $HOST_B"
    ssh $HOST_B "BENCHMARKS_DIR=$HOST_B_BENCHMARKS_DIR $REMOTE_SUPPORT_DIR/compile_benchmarks.sh"
else
    echo "Skipping compilation"
fi

if [ ! -z "$SKIP_BENCHMARK" ]; then
    echo "Skipping benchmark, exiting..."
    exit 0
fi

echo "Starting Throughput Benchmark..."

. "${DIR}/support/benchmark_throughput_mtcp.sh"

prepare_mtcp_thoughput_benchmark

#measure sendbuffer

#for BENCHMARK_SNDBUFFER in $( seq 8192 20480 250000 ); do
#    CORES=1
#    CONNECTIONS_PER_CORE=1
#    run_mtcp_throughput_benchmark $CORES $CONNECTIONS_PER_CORE $BENCHMARK_SNDBUFFER
#done
#
#exit 0

# measure throughput
BENCHMARK_SNDBUFFER=1460
for CORES in 1 2 3; do
    #NOTE:
    #There are 2 limits to the number of connections you can create
    #1. The number of connections from one dst IP to one src IP is limited to 2^16 connections (max. number of possible ports)
    #2. The number of available fd on dst HOST, which is 1024*1024 on Linux
    for CONNECTIONS in 1 50 100 500 1000 2500 5000 75000 10000 15000 20000 25000 30000 35000 40000 45000 50000 55000 60000; do
        CONNECTIONS_PER_CORE=$( python -c "from __future__ import division; from math import ceil; print int(ceil($CONNECTIONS / $CORES))" )

        run_mtcp_throughput_benchmark $CORES $CONNECTIONS_PER_CORE $BENCHMARK_SNDBUFFER
    done
done

