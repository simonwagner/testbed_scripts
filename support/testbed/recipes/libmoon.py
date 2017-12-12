from __future__ import absolute_import

import os

from ..logging import logging
from ..machine import default_machine, DefaultMachineLogAdapter
from ..utils import timestamped_logfile_path
from .. import apt

machine_logger = DefaultMachineLogAdapter(logging.getLogger("testbed.libmoon"))
logger = logging.getLogger("testbed.libmoon")

MTCP_EXCLUDE_CORES = frozenset((0,))

DEPENDENCIES = [
    "pciutils",
    "libjemalloc-dev",
    "libnuma-dev",
    "cmake",
    "psmisc",
    "python",
    "gcc-6",
    "g++-6",
    "gdb",
    "automake",
    "autoconf",
]

def install_deps():
    machine_logger.info("Installig dependencies for libmoon")
    apt.add_repository("ppa:ubuntu-toolchain-r/test")
    apt.install_packages(DEPENDENCIES)
    apt.install_kernel_headers()
    
    # make sure that the compiler is gcc 6
    machine_logger.info("Setting default compiler to GCC 6")
    default_machine["update-alternatives"]("--install", "/usr/bin/gcc", "gcc", "/usr/bin/gcc-6", "60",
                                           "--slave", "/usr/bin/g++", "g++", "/usr/bin/g++-6")
    default_machine["update-alternatives"]("--set", "gcc", "/usr/bin/gcc-6")
    
def compile(libmoon_dir, logdir=None):
    machine_logger.info("Compiling libmoon in '%s'..." % libmoon_dir)
    if logdir is not None:
        logger.info("Compiling logs will be available in '%s'" % logdir)
    with default_machine.cwd(libmoon_dir):
        (default_machine["./build.sh"] > timestamped_logfile_path(logdir, "build-libmoon"))()
        # compile the netcat sample app
        with default_machine.cwd("./deps/mtcp/apps/netcat"):
            (default_machine["make"] > timestamped_logfile_path(logdir, "build-mtcp-netcat"))()

def bind_netif_driver_by_pci(libmoon_dir, pci_address, driver="igb_uio"):
    #${HOST_A_LIBMOON_DIR}/deps/dpdk/tools/dpdk-devbind.py --bind igb_uio $LIBMOON_IF_PCI_ADDRESS
    machine_logger.info("Binding NIC pci@%s to driver %s" % (pci_address, driver))
    dpdk_devbind_path = os.path.join(libmoon_dir, "deps/dpdk/tools/dpdk-devbind.py")
    default_machine[dpdk_devbind_path]("--bind", driver, pci_address)

def clear_and_set_huge_pages_nr(huge_pages_nr):
    machine_logger.info("Freeing currently reserved huge pages...")
    #clear huge pages
    huge_pages_dir = default_machine.path("/dev/hugepages/")
    for file_path in huge_pages_dir.glob("rte_*"):
        file_path.delete()
    
    #set huge pages number
    machine_logger.info("Setting number of huge pages to %d..." % huge_pages_nr)
    nr_hugepages_path = default_machine.path("/proc/sys/vm/nr_hugepages")
    nr_hugepages_path.write(str(huge_pages_nr))

def mtcp_core_mapping(machine=default_machine):
    return "(0-3)@0," + hyperthreading_core_mapping_for_machine(machine, start_at=4, exclude=MTCP_EXCLUDE_CORES)

def hyperthreading_core_mapping_for_machine(machine, start_at=0, exclude=set()):
    cpus = cpus_on_machine(machine)
    thread_siblings_list = thread_siblings_on_machine(machine, exclude=exclude)
    
    groupings = []
    current = start_at
    for thread_siblings in thread_siblings_list:
        for cpu in thread_siblings:
            groupings.append("%d@%d" % (current, cpu))
            current += 1
    return str.join(",", groupings)

def available_mtcp_cores(machine):
    thread_siblings_list = thread_siblings_on_machine(machine, exclude=MTCP_EXCLUDE_CORES)
    return sum(len(thread_siblings) for thread_siblings in thread_siblings_list)

def thread_siblings_on_machine(machine, exclude=set()):
    cpus = cpus_on_machine(machine)
    thread_siblings_set = frozenset(thread_siblings_for_cpu_on_machine(machine, cpu) for cpu in cpus) # remove duplicates
    thread_siblings_list = [thread_siblings for thread_siblings in thread_siblings_set 
                            if not any(cpu in exclude for cpu in thread_siblings)]
    thread_siblings_list.sort()
    
    return thread_siblings_list
    
def thread_siblings_for_cpu_on_machine(machine, cpu):
    siblings_str = machine.path("/sys/bus/cpu/devices/cpu%d/topology/thread_siblings_list" % cpu).read()
    siblings = [int(item) for item in siblings_str.split(",")]
    siblings.sort()
    return tuple(siblings)

def cpus_on_machine(machine):
    cpu_dirs = machine.path("/sys/bus/cpu/devices/").glob("cpu*")
    cpus = [int(cpu_dir.name[3:]) for cpu_dir in cpu_dirs]
    
    return cpus
    

def run(libmoon_dir, config):
    pass