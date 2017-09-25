#!/bin/sh

PCI_ADDRESS=$1
IP=$2
NETMASK=$3

echo "lshw -c network -businfo -quiet | grep \"pci@$1\" | awk '{print $2}'"
IF=`lshw -c network -businfo -quiet | grep "pci@$1" | awk '{print $2}'`
echo "Network interface: $IF"
if [ -z "$IF" ]; then
    echo "No network interface found at $PCI_ADDRESS"
    exit 1
fi

ifconfig $IF $IP netmask $NETMASK

exit 0