from __future__ import absolute_import

from ..machine import default_machine, DefaultMachineLogAdapter
from ..utils import timestamped_logfile_path
from ..logging import logging
from .. import apt

machine_logger = DefaultMachineLogAdapter(logging.getLogger("testbed.benchmarks"))
logger = logging.getLogger("testbed.benchmarks")

DEPENDENCIES = [
    "gcc-6",
    "g++-6",
    "gdb",
    "make",
    "libtbb-dev",
    "lshw",
]

def install_deps():
    machine_logger.info("Installig dependencies for benchmarks")
    apt.add_repository("ppa:ubuntu-toolchain-r/test")
    apt.install_packages(DEPENDENCIES)
    
    # make sure that the compiler is gcc 6
    machine_logger.info("Setting default compiler to GCC 6")
    default_machine["update-alternatives"]("--install", "/usr/bin/gcc", "gcc", "/usr/bin/gcc-6", "60",
                                           "--slave", "/usr/bin/g++", "g++", "/usr/bin/g++-6")
    default_machine["update-alternatives"]("--set", "gcc", "/usr/bin/gcc-6")
    
def compile(benchmarks_dir, logdir=None):
    machine_logger.info("Compiling benchmarks in '%s'..." % benchmarks_dir)
    if logdir is not None:
        logger.info("Compiling logs will be available in '%s'" % logdir)
    with default_machine.cwd(benchmarks_dir):
        (default_machine["./build.sh"] > timestamped_logfile_path(logdir, "build-benchmarks"))()

def popen(benchmarks_dir, config):
    benchmark_path = os.path.join(benchmarks_dir, "server-bench")
    benchmark = default_machine[benchmark_path]
    
    