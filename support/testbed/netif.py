from __future__ import absolute_import

import re

from .machine import default_machine, get_default_machine_name, DefaultMachineLogAdapter
from .logging import logging

machine_logger = DefaultMachineLogAdapter(logging.getLogger("testbed.netif"))


def configure_netif_by_pci(pci_address, ip_address, netmask):
    netif = netif_for_pci_address(pci_address)
    if netif is None:
        machine_logger.error("No network device found at PCI address %s" % pci_address)
        raise Exception("No network device found at PCI address %s on machine %s" % (pci_address, get_default_machine_name()))
    configure_netif(netif, ip_address, netmask)


def configure_netif(netif, ip_address, netmask):
    #ifconfig = default_machine["ifconfig"]
    #ifconfig(netif, ip_address, "netmask", netmask)
    netmask_length = netmask_to_cidr(netmask)
    
    ip = default_machine["ip"]
    ip("addr", "add", "%s/%d" % (ip_address, netmask_length), "dev", netif)
    ip("link", "set", "dev", netif, "up")

def netmask_to_cidr(netmask):
    #this is stupid but good enough
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])
    

def reset_netif_by_pci(pci_address):
    netif = netif_for_pci_address(pci_address)
    if netif is None:
        machine_logger.error("No network device found at PCI address %s" % pci_address)
        raise Exception("No network device found at PCI address %s on machine %s" % (pci_address, get_default_machine_name()))
    reset_netif(netif)

def reset_netif(netif):
    default_machine["ip"]("address", "flush", "dev", netif)


def netif_for_pci_address(pci_address):
    lshw = default_machine["lshw"]
    for line in lshw("-c", "network", "-businfo", "-quiet").splitlines():
        if not line.startswith("pci@"):
            continue
        bus_info, device, clazz, description = line.split(None, 3)
        if bus_info == "pci@%s" % pci_address:
            return device
    return None
