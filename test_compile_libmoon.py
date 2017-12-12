#!/usr/bin/env python

from __future__ import absolute_import

import argparse
import os.path

from testbed.logging import logging
import testbed.conf
import testbed.apt
import testbed.utils
import testbed.machine
from testbed.machine import make_default_machine
import testbed.recipes.libmoon
import testbed.recipes.controller
from testbed.host import Host, allocate_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("testbed.test")

argparser = argparse.ArgumentParser()
argparser.add_argument("--config", default=testbed.conf.default_conf_path_for_script(__file__))
argparser.add_argument("--skip-boot", action="store_true")
argparser.add_argument("--force-node-allocation", "-f", action="store_true")

def main():
    args = argparser.parse_args()
    logger.info("Loading config from %s" % args.config)
    config = testbed.conf.load(args.config)
    logdir = config.controller.logdir
    
    if logdir is not None:
        testbed.utils.mkdir_ignore_existing(logdir)
    
    libmoon_host = Host(config.libmoon.host)
    with allocate_all([libmoon_host], force=args.force_node_allocation):
        if not args.skip_boot:
            libmoon_host.boot(config.libmoon.image)
        
        #install base requirements
        testbed.recipes.controller.install_base_packages(config, hosts=[libmoon_host])
        #prepare libmoon
        libmoon_remote_dir = os.path.join(config.libmoon.testdir, "libmoon")
        libmoon_host.push(config.libmoon.dir, libmoon_remote_dir, make_dir=True)
        
        #compile libmoon
        with make_default_machine(libmoon_host.machine):
            testbed.recipes.libmoon.install_deps()
            testbed.recipes.libmoon.compile(libmoon_remote_dir, logdir=logdir)

if __name__ == "__main__":
    main()