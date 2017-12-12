from __future__ import absolute_import

from ..logging import logging
from ..machine import make_default_machine, default_machine, DefaultMachineLogAdapter
from .. import apt 

machine_logger = DefaultMachineLogAdapter(logging.getLogger("testbed.controller"))
logger = logging.getLogger("testbed.controller")

def install_base_packages(config, hosts):
    for host in hosts:
        with make_default_machine(host.machine):
            apt.install_packages(config.controller.node_dependencies)
