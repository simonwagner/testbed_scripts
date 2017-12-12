from __future__ import absolute_import

import logging

from plumbum.commands import CommandNotFound

from .logging import logging
from .machine import default_machine, DefaultMachineLogAdapter

machine_logger = DefaultMachineLogAdapter(logging.getLogger("testbed.apt"))

def install_packages(packages, update=True):
    machine_logger.info("Installing packages: %s" % str.join(",", packages))
    apt_get = default_machine["apt-get"].with_env(DEBIAN_FRONTEND="noninteractive")
    if update:
        apt_get("-qq", "update")
    apt_get("-qq", "-y", "install", *packages)

def install_kernel_headers(update=True):
    current_kernel = default_machine["uname"]("-r").rstrip()
    install_packages(["linux-headers-%s" % current_kernel], update=update)
    
    
def add_repository(repository):
    machine_logger.info("Adding repository: %s" % repository)
    try:
        add_apt_repository = default_machine["add-apt-repository"]
    except CommandNotFound as e:
        # try to install it if it is not available
        machine_logger.info("\tadd-apt-repository is currently not installed, installing it...")
        install_packages(["software-properties-common"])
        add_apt_repository = default_machine["add-apt-repository"]
    add_apt_repository(repository)