from __future__ import absolute_import

from contextlib import contextmanager

from plumbum import SshMachine
from concurrent.futures import ThreadPoolExecutor

from .logging import logging
from .machine import default_machine, DefaultMachineLogAdapter, HostLogAdapter
from .utils import push, pull, results_of_futures

machine_logger = DefaultMachineLogAdapter(logging.getLogger("testbed.host"))

class Host(object):
    def __init__(self, name, user="root"):
        self._name = name
        self._user = user
        self._machine = None
        
    @property
    def name(self):
        return self._name
    
    def allocate(self, force=False):
        pos = default_machine["pos"]
        
        if force:
            self.free(force=True)

        machine_logger.info("Allocating host %s" % self._name)
        pos("allocations", "allocate", self._name)
    
    def boot(self, image, bootparams={}):
        pos = default_machine["pos"]
        
        self._machine = None

        bootparam_strings = ["%s=%s" % (key, value) for key, value in bootparams.iteritems()]
        pos("nodes", "image", self._name, image, *bootparam_strings)
        machine_logger.info("Booting host %s with %s (cmdline: %s)..." % (self._name,
                                                                  image,
                                                                  str.join(" ", bootparam_strings)))
        pos("nodes", "stop", self._name)
        pos("nodes", "start", self._name)
        machine_logger.info("Host %s is up" % self._name)
    
    def shutdown(self):
        pos = default_machine["pos"]

        pos("nodes", "stop", self._name)
        self._machine = None
    
    def free(self, force=False):
        pos = default_machine["pos"]
        if force:
            pos("allocations", "free", "-f", self._name)
        else:
            pos("allocations", "free", self._name)
    
    def push(self, local_path, remote_path, make_dir=False, delete=True):
        machine_logger.info("Pushing '%s' to %s:'%s'" % (local_path, self._name, remote_path))
        if make_dir:
            self.machine["mkdir"]("-p", remote_path)
        push(local_path, self._user, self._name, remote_path, delete=delete)
    
    def pull(self, remote_path, local_path, delete=True):
        machine_logger.info("Pulling '%s' to %s:'%s'" % (self._name, remote_path, local_path))
        pull(self._user, self._name, remote_path, local_path, delete=delete)
    
    def connect(self):
        return SshMachine(self._name, user=self._user)
    
    def getLogger(self, topic):
        return HostLogAdapter(logging.getLogger(topic), host=self)
    
    @property
    def machine(self):
        if self._machine is None:
            self._machine = self.connect()
        return self._machine

@contextmanager
def allocate_all(hosts, force=False):
    for host in hosts:
        host.allocate(force=force)
    yield
    for host in hosts:
        host.free()

def boot_all(*hosts_with_images_and_boot_params):
    """Boot hosts in parallel"""
    futures = []
    with ThreadPoolExecutor(max_workers=len(hosts_with_images_and_boot_params)) as executor:
        for tuple in hosts_with_images_and_boot_params:
            host, image = tuple[:2]
            if len(tuple) >= 3:
                bootparams = tuple[2]
            else:
                bootparams = {}
            future = executor.submit(host.boot, image, bootparams=bootparams)
            futures.append(future)
        # wait for the hosts to boot, this will throw any exceptions that occured during boot
        results_of_futures(futures) 