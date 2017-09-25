#!/bin/sh

USER=$1
HOST=$2

if [ -z "$HOST" ] || [ -z "$USER" ] ; then
    echo "usage $0 USER HOST"
    echo ""
    echo "Will tunnel IPMI of HOST via kaunas to localhost"
    
    exit 1
fi

SOCKET_FILE_DIR=$(mktemp -d "/tmp/$(basename $0)-socket.XXXXXXXXXXXX")
SOCKET_FILE="$SOCKET_FILE_DIR/control-socket"

echo "Creating tunnel for IPMI..."

ssh -N -f -M -S $SOCKET_FILE $USER@kaunas.net.in.tum.de -p 10022 -L 8000:localhost:8000 -L 80:$HOST.ipmi.baltikum.net.in.tum.de:80 -L 443:$HOST.ipmi.baltikum.net.in.tum.de:443 -L 5900:$HOST.ipmi.baltikum.net.in.tum.de:5900
#ssh -S $SOCKET_FILE -f $USER@kaunas.net.in.tum.de -p 10022 "socat -T15 udp4-recvfrom:623,reuseaddr,fork tcp:localhost:8000"

#socat -T15 udp4-recvfrom:623,reuseaddr,fork tcp:localhost:8000 &
#CLIENT_SOCAT_PID=$!

read -p "Press ENTER to close tunnel and exit"

echo "Closing tunnel..."

ssh -S $SOCKET_FILE -O exit $USER@kaunas.net.in.tum.de
#kill $CLIENT_SOCAT_PID

echo "done"