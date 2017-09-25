function get_pid_file_name {
    local BASENAME=$1
    
    echo get_postfixed_file_name $BASENAME "pid"
}

function get_postfixed_file_name {
    local BASENAME=$1
    local EXT=$2
    
    echo "$BASENAME-`date -u +"%Y-%m-%dT%H-%M-%S"`.$EXT"
}

function remote_kill_pidfile {
    local HOST=$1
    local SIGNAL=$2
    local PIDFILE=$3
    
    ssh $HOST 'kill -s ' $SIGNAL '$( cat ' $PIDFILE ') > /dev/null 2> /dev/null'
}