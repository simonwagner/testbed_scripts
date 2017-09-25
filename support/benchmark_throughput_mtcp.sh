source "${DIR}/support/tools.sh"

# HOST_A: sends traffic to HOST_B via mTCP user space stack in libmoon
# HOST_B: receives traffic from HOST_A on linux TCP stack and records the throughput

function prepare_mtcp_thoughput_benchmark {
    # setup HOST_A
    echo "Preparing test directory $TEST_DIR on $HOST_A"
    ssh $HOST_A "TEST_DIR=${TEST_DIR} ${REMOTE_SUPPORT_DIR}/prepare_testdir.sh"

    echo "Creating libmoon config from template $LIBMOON_DPDK_CONFIG_TEMPLATE_FILE..."
    ${DIR}/support/template.py -t ${LIBMOON_DPDK_CONFIG_TEMPLATE_FILE} -o /tmp/dpdk-mtcp-conf.lua -v LIBMOON_IF_PCI_ADDRESS="$LIBMOON_IF_PCI_ADDRESS" -v LIBMOON_CORE_MAPPING="$LIBMOON_CORE_MAPPING"

    echo "Uploading dpdk config template file $LIBMOON_DPDK_CONFIG_TEMPLATE_FILE to $HOST_A..."
    scp /tmp/dpdk-mtcp-conf.lua $HOST_A:/tmp/dpdk-mtcp-conf.lua
	
	echo "Binding nic at $LIBMOON_IF_PCI_ADDRESS to igb_uio driver..."
	ssh -n $HOST_A "${HOST_A_LIBMOON_DIR}/deps/dpdk/tools/dpdk-devbind.py --bind igb_uio $LIBMOON_IF_PCI_ADDRESS"
    
    # setup HOST_B
    echo "Preparing test directory $TEST_DIR on $HOST_B"
    ssh $HOST_B "TEST_DIR=${TEST_DIR} ${REMOTE_SUPPORT_DIR}/prepare_testdir.sh"

    echo "Configuring network interface on $HOST_B: [$BENCHMARK_IF_PCI_ADDRESS]: $BENCHMARK_IF_IP_ADDRESS netmask $BENCHMARK_IF_IP_NETMASK"
    ssh $HOST_B "${REMOTE_SUPPORT_DIR}/configure_if_by_pci.sh $BENCHMARK_IF_PCI_ADDRESS $BENCHMARK_IF_IP_ADDRESS $BENCHMARK_IF_IP_NETMASK"
    echo "Setting the limit for file descriptors huge value"
    #1048576 is the maximum limit according to http://stackoverflow.com/questions/1212925/on-linux-set-maximum-open-files-to-unlimited-possible
    #1048576
    ssh $HOST_B "sysctl -w fs.file-max=1048576"
    ssh $HOST_B "sysctl -w net.ipv4.tcp_max_orphans=0" #make sure connections do not linger on
    
    echo "Killing any remaining processes that might still be running from a previous run"
    ssh $HOST_A "killall libmoon > /dev/null || exit 0"
    ssh $HOST_B "killall server-bench > /dev/null || exit 0"
}

function run_mtcp_throughput_benchmark {
    local CORES_COUNT=$1
    local CONNECTIONS_PER_CORE=$2
    local SNDBUFFER=$3
    
    echo "------------------------------------------------------------------"
    echo "RUNNING BENCHMARK cores: $CORES_COUNT connection/core: $CONNECTIONS_PER_CORE sndbuffer: $SNDBUFFER"

    SERVERBENCH_PID_FILE="${TEST_DIR}/pid/$( get_pid_file_name "benchmark-server-bench" )"
    LIBMOON_PID_FILE="${TEST_DIR}/pid/$( get_pid_file_name "libmoon-mtcp" )"
    BENCHMARK_NAME="cores_${CORES_COUNT}_conn_${CONNECTIONS_PER_CORE}_sndbuff_${SNDBUFFER}"

    # cleanup HOST_A
    echo "Setting number of huge pages to $LIBMOON_HUGEPAGES_NR on $HOST_A"
    ssh $HOST_A "echo $LIBMOON_HUGEPAGES_NR > /proc/sys/vm/nr_hugepages"
    echo "Freeing currently reserved huge pages..."
    ssh $HOST_A 'rm -rf /dev/hugepages/rtemap_*'
    
    BENCHMARK_RESULT="${TEST_DIR}/results/${TEST_ID}_${BENCHMARK_NAME}.csv"
    echo "Storing benchmark result at $BENCHMARK_RESULT"

    # run benchmark

    echo "Starting server-bench on host $HOST_B..."
    ssh $HOST_B "sysctl -w net.ipv4.tcp_fin_timeout=2"
    ssh $HOST_B "echo 'root hard nofile 1048576' >> /etc/security/limits.conf"
    ssh $HOST_B "echo 'root soft nofile 1048576' >> /etc/security/limits.conf"
    ssh -n $HOST_B "( $HOST_B_BENCHMARKS_DIR/server-bench $BENCHMARK_PORT --machine --sum-only 2> $BENCHMARK_RESULT > ${TEST_DIR}/log/benchmark-$BENCHMARK_NAME.log ) & echo \$! > $SERVERBENCH_PID_FILE" > "${LOG_DIR}/server-bench-start-$HOST_B-$BENCHMARK_NAME.log 2>&1" &
    BENCHMARK_SSH_PID=$!

    echo "Starting mtcp on $HOST_A connecting to $BENCHMARK_IF_IP_ADDRESS:$BENCHMARK_PORT on nic pci@$LIBMOON_IF_PCI_ADDRESS ($LIBMOON_IF_IP_ADDRESS netmask $LIBMOON_IF_IP_NETMASK)"
    echo "${HOST_A_LIBMOON_DIR}/build/libmoon ${HOST_A_LIBMOON_DIR}/examples/mtcp/mtcp-echo.lua --dpdk-config=/tmp/dpdk-mtcp-conf.lua -p 0 -a $LIBMOON_IF_IP_ADDRESS -m $LIBMOON_IF_IP_NETMASK -H $BENCHMARK_IF_IP_ADDRESS -P $BENCHMARK_PORT -c $CORES_COUNT -n $CONNECTIONS_PER_CORE --send-buffer $SNDBUFFER"
    ssh -n $HOST_A "( ${HOST_A_LIBMOON_DIR}/build/libmoon ${HOST_A_LIBMOON_DIR}/examples/mtcp/mtcp-echo.lua --dpdk-config=/tmp/dpdk-mtcp-conf.lua -p 0 -a $LIBMOON_IF_IP_ADDRESS -m $LIBMOON_IF_IP_NETMASK -H $BENCHMARK_IF_IP_ADDRESS -P $BENCHMARK_PORT -c $CORES_COUNT -n $CONNECTIONS_PER_CORE --send-buffer $SNDBUFFER > ${TEST_DIR}/log/mtcp-echo-$BENCHMARK_NAME.log 2>&1 ) & echo \$! > $LIBMOON_PID_FILE"  > "${LOG_DIR}/mtcp-start-$HOST_A-$BENCHMARK_NAME.log 2>&1" &
    LIBMOON_SSH_PID=$!
    
    ACCEPT_CON_SLEEP=$( bc <<< "$CONNECTIONS_PER_CORE * $CORES_COUNT / 650")
    echo "Waiting $ACCEPT_CON_SLEEP sec for connections to be accepted..."
    sleep $ACCEPT_CON_SLEEP

    echo "Running benchmark for $BENCHMARK_SECONDS seconds..."
    for i in $( seq 0 5 $BENCHMARK_SECONDS); do echo -n "$i "; sleep 5; done
    echo "...done"

    echo "Stopping libmoon..."
    # have to send SIGINT twice for libmoon to really quit
    remote_kill_pidfile $HOST_A SIGINT $LIBMOON_PID_FILE || echo "kill libmoon: libmoon process not found, did the test fail?"
    sleep 5
    remote_kill_pidfile $HOST_A SIGINT $LIBMOON_PID_FILE || true

    echo "Stopping benchmark-server..."
    remote_kill_pidfile $HOST_B SIGINT $SERVERBENCH_PID_FILE || echo "kill benchmark: benchmark process not found, did the test fail?"

    echo -n "waiting for background SSH connections to finish..."
    wait $BENCHMARK_SSH_PID $LIBMOON_SSH_PID
    echo "done"

    echo "Uploading results from $HOST_B..."
    ssh $HOST_B "cat ${BENCHMARK_RESULT}"
    
    echo "Sleeping for 4sec to let connections timeout"
    sleep 4
    
    echo "------------------------------------------------------------------"
}

