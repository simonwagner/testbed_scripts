SCRIPT="$( basename "${BASH_SOURCE[0]}" )"
                                                                                
                                                                                
echo "[$SCRIPT] free $HOST_A / $HOST_B"                                                   
testbed-nodes free -f $HOST_A                                                   
testbed-nodes free -f $HOST_B                                                   
sleep 1                                                                         
                                                                                
echo "[$SCRIPT] allocating $HOST_A / $HOST_B"                                                
testbed-nodes allocate -i $TEST_IMAGE -t $TEST_ID $HOST_A
testbed-nodes allocate -i $TEST_IMAGE -t $TEST_ID $HOST_B
sleep 1

if [ -z "$SKIP_TESTBED_BOOT" ]; then
    # boot hosts
    echo "[$SCRIPT] shutting down $HOST_A / $HOST_B"                                                
    testbed-nodes shutdown $HOST_A
    testbed-nodes shutdown $HOST_B
    sleep 1
    echo "[$SCRIPT] booting $HOST_A / $HOST_B"
    testbed-nodes boot $HOST_A
    testbed-nodes boot $HOST_B
    sleep 1
else
    echo "[$SCRIPT] SKIP rebooting $HOST_A / $HOST_B"
fi                                                                         
                                                                                
echo "[$SCRIPT] waiting for $HOST_A"                                                      
testbed-nodes waituntilready $HOST_A                                            
echo "[$SCRIPT] $HOST_A is ready"                                                         

echo "[$SCRIPT] waiting for $HOST_B"
testbed-nodes waituntilready $HOST_B
echo "[$SCRIPT] $HOST_B is ready"

sleep 5