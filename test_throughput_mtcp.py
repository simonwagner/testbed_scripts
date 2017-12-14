#!/usr/bin/env python

from __future__ import absolute_import

import argparse
import os.path
import time
import signal
from string import Template
import math

from concurrent.futures import ThreadPoolExecutor
from plumbum.path.utils import copy as copy_path
from plumbum.machines import local as local_machine

from testbed.logging import logging
import testbed.conf
import testbed.apt
import testbed.utils
from testbed.utils import BGT
import testbed.machine
import testbed.netif
from testbed.machine import make_default_machine
import testbed.recipes.libmoon
import testbed.recipes.controller
import testbed.recipes.benchmarks
from testbed.host import Host, allocate_all, boot_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("testbed.test")

argparser = argparse.ArgumentParser()
argparser.add_argument("--config", default=testbed.conf.default_conf_path_for_script(__file__))
argparser.add_argument("--skip-boot", action="store_true")
argparser.add_argument("--skip-prepare", action="store_true")
argparser.add_argument("--skip-compile-libmoon", action="store_true")
argparser.add_argument("--skip-compile-server-bench", action="store_true")
argparser.add_argument("--force-node-allocation", "-f", action="store_true")

def debug(sig, frame):
    testbed.utils.print_stacktrace()

def main():
    signal.signal(signal.SIGUSR1, debug)
    
    args = argparser.parse_args()
    logger.info("Loading config from %s" % args.config)
    config = testbed.conf.load(args.config)
    logdir = config.controller.logdir
    resultsdir = config.controller.resultsdir
    
    if logdir is not None:
        testbed.utils.mkdir_ignore_existing(logdir)
    testbed.utils.mkdir_ignore_existing(resultsdir)
    
    logger.info("Clearing results directory %s", config.controller.resultsdir)
    testbed.utils.clear_directory(config.controller.resultsdir)
    
    libmoon_host = Host(config.libmoon.host)
    benchmarks_host = Host(config.benchmarks.host)
    with allocate_all([libmoon_host, benchmarks_host], force=args.force_node_allocation):
        if not args.skip_boot:
            boot_all(
                (libmoon_host, config.libmoon.image),
                (benchmarks_host, config.benchmarks.image)
            )
        if not args.skip_prepare:
            #install base requirements
            testbed.recipes.controller.install_base_packages(config, hosts=[libmoon_host, benchmarks_host])
        
            testbed.utils.do_parallel(
                lambda: prepare_libmoon(libmoon_host, config=config, logdir=logdir, skip_compile=args.skip_compile_libmoon),
                lambda: prepare_benchmarks(benchmarks_host, config=config, logdir=logdir, skip_compile=args.skip_compile_server_bench)
            )

        run(libmoon_host=libmoon_host, benchmarks_host=benchmarks_host, config=config, logdir=logdir, resultsdir=resultsdir)

def prepare_libmoon(libmoon_host, config, logdir, skip_compile=False):
    #prepare libmoon
    libmoon_remote_dir = os.path.join(config.libmoon.testdir, "libmoon")
    libmoon_host.push(config.libmoon.dir, libmoon_remote_dir, make_dir=True, delete=not skip_compile)
    
    with make_default_machine(libmoon_host.machine):
        #compile libmoon
        if not skip_compile:
            testbed.recipes.libmoon.install_deps()
            testbed.recipes.libmoon.compile(libmoon_remote_dir, logdir=logdir)
        #configure interface
        testbed.recipes.libmoon.bind_netif_driver_by_pci(libmoon_dir=libmoon_remote_dir,
                                                         pci_address=config.libmoon.interface.pci_address)
        #configure huge pages
        testbed.recipes.libmoon.clear_and_set_huge_pages_nr(config.libmoon.huge_pages_nr)

def prepare_benchmarks(benchmarks_host, config, logdir, skip_compile=False):
    #prepare benchmarks
    benchmarks_remote_dir = os.path.join(config.benchmarks.testdir, "benchmarks")
    benchmarks_host.push(config.benchmarks.dir, benchmarks_remote_dir, make_dir=True, delete=not skip_compile)
    
    with make_default_machine(benchmarks_host.machine):
        #compile benchmarks
        if not skip_compile:
            testbed.recipes.benchmarks.install_deps()
            testbed.recipes.benchmarks.compile(benchmarks_remote_dir, logdir=logdir)
        #configure interface
        testbed.netif.reset_netif_by_pci(config.benchmarks.interface.pci_address)
        for ip_address in config.benchmarks.interface.ip_addresses:
            testbed.netif.configure_netif_by_pci(pci_address=config.benchmarks.interface.pci_address,
                                                 ip_address=ip_address,
                                                 netmask=config.benchmarks.interface.ip_netmask)
        #configure sysctl vars
        testbed.utils.set_sysctl({
            "fs.file-max": "1048576", # 1048576 is the maximum limit according to http://stackoverflow.com/questions/1212925/on-linux-set-maximum-open-files-to-unlimited-possible
            "net.ipv4.tcp_max_orphans": "0", # make sure connections do not linger on
            "net.ipv4.tcp_fin_timeout": "2",
        })

def result_file_name_for(cores, concurrency, sendbuffer):
    return "cores_%d_conn_%d_sndbuff_%d.csv" % (cores, concurrency, sendbuffer)

def run(libmoon_host, benchmarks_host, config, logdir, resultsdir):
    for cores in range(1, testbed.recipes.libmoon.available_mtcp_cores(libmoon_host.machine) + 1):
        #[10, 50, 100, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500]
        for concurrency in xrange(1, 200, 5):
            run_test(libmoon_host, benchmarks_host, config, logdir, 
                     concurrency=concurrency/cores,
                     cores=cores,
                     resultfile=os.path.join(resultsdir, result_file_name_for(cores=cores, concurrency=concurrency/cores*cores, sendbuffer=0)))

def run_test(libmoon_host, benchmarks_host, config, logdir, resultfile, concurrency, cores):
    benchmarks_logger = benchmarks_host.getLogger("testbed.test")
    libmoon_logger = libmoon_host.getLogger("testbed.test")
    
    executor = ThreadPoolExecutor(max_workers=2)
    benchmark_future, benchmark_pidfile = start_server_benchmark(executor, benchmarks_host, config, logdir, resultfile="/tmp/result.csv")
    time.sleep(1) # wait a while, so we can be sure that the benchmark is running
    libmoon_future, libmoon_pidfile = start_libmoon(executor, libmoon_host, config, logdir, concurrency=concurrency, cores=cores)
    time.sleep(90)
    
    #stop benchmark
    if not benchmark_future.ready():
        benchmarks_logger.info("sending SIGTERM and waiting for server-bench to exit")
        testbed.utils.send_signal(pid_file=benchmark_pidfile, signal="SIGTERM", machine=benchmarks_host.machine)
    benchmark_future.wait()
    benchmarks_logger.info("server-bench has finished")
    if not libmoon_future.ready():
        libmoon_logger.info("sending SIGTERM and waiting for libmoon to exit")
        testbed.utils.send_signal(pid_file=libmoon_pidfile, signal="SIGTERM", machine=libmoon_host.machine, times=2)
    libmoon_future.wait()
    libmoon_logger.info("libmoon has finished")
    executor.shutdown()
    
    #download results locally
    copy_path(
        benchmarks_host.machine.path("/tmp/result.csv"),
        local_machine.path(resultfile)
    )

def start_libmoon(executor, libmoon_host, config, logdir, concurrency, cores, log_postfix=""):
    libmoon_logger = libmoon_host.getLogger("testbed.test")
    libmoon_path = os.path.join(config.libmoon.testdir, "libmoon", "build", "libmoon")
    libmoon_script_path = os.path.join(config.libmoon.testdir, "libmoon", "examples", "mtcp", "mtcp-client.lua")
    libmoon_config_path = os.path.join(config.libmoon.testdir, "dpdk-config.lua")
    
    #write config
    template_str = local_machine.path(config.libmoon.dpdk_config_template_file).read()
    template = Template(template_str)
    core_mapping = testbed.recipes.libmoon.mtcp_core_mapping(machine=libmoon_host.machine)
    
    libmoon_logger.info("core mapping: %s" % core_mapping)
    libmoon_logger.info("writing libmoon config to %s" % libmoon_config_path)
    libmoon_config = template.substitute({"LIBMOON_CORE_MAPPING": core_mapping})
    libmoon_host.machine.path(libmoon_config_path).write(libmoon_config)
    
    
    
    libmoon_cmd = libmoon_host.machine[libmoon_path][libmoon_script_path,
                                                     "--dpdk-config=%s" % libmoon_config_path,
                                                     "--pidfile", "/tmp/libmoon.pid",
                                                     "--dpdk-port", "pci@%s" % config.libmoon.interface.pci_address,
                                                     "--address", config.libmoon.interface.ip_address,
                                                     "--netmask", config.libmoon.interface.ip_netmask,
                                                     "--port", config.benchmarks.port,
                                                     "--concurrency", str(concurrency),
                                                     "--cores", str(cores)]
    libmoon_cmd = libmoon_cmd["--host"]
    for ip_address in config.benchmarks.interface.ip_addresses:
        libmoon_cmd = libmoon_cmd[ip_address]

    libmoon_cmd = libmoon_cmd > testbed.utils.timestamped_logfile_path(logdir, "libmoon" + log_postfix)
    
    libmoon_logger.info("will run libmoon: %s", str(libmoon_cmd))
    libmoon_future = libmoon_cmd & BGT(executor, retcode=[0, 134])
    
    return libmoon_future, "/tmp/libmoon.pid"

def start_server_benchmark(executor, benchmarks_host, config, logdir, resultfile, log_postfix=""):
    benchmarks_logger = benchmarks_host.getLogger("testbed.test")
    benchmarks_path = os.path.join(config.benchmarks.testdir, "benchmarks", "server-bench")
    benchmark_cmd = benchmarks_host.machine[benchmarks_path]["--pidfile", "/tmp/server-bench.pid", "--sum-only", "--machine"][str(config.benchmarks.port)]
    benchmark_cmd = benchmark_cmd["--resultfile", resultfile]
    benchmark_cmd = benchmark_cmd > testbed.utils.timestamped_logfile_path(logdir, "server_bench" + log_postfix)

    benchmarks_logger.info("will run server-bench: %s", str(benchmark_cmd))
    benchmark_future = benchmark_cmd & BGT(executor)
    
    return benchmark_future, "/tmp/server-bench.pid"


if __name__ == "__main__":
    main()