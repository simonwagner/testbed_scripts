from __future__ import absolute_import

import threading
from logging import LoggerAdapter
from contextlib import contextmanager

from plumbum.machines import local as local_machine

tls = threading.local()

def get_default_machine_stack():
    default_machine_stack = getattr(tls, "default_machine_stack", None)
    if default_machine_stack is None:
        default_machine_stack = []
        tls.default_machine_stack = default_machine_stack
    return default_machine_stack

def get_default_machine():
    default_machine_stack = get_default_machine_stack()
    if len(default_machine_stack) > 0:
        return default_machine_stack[-1]
    else:
        return local_machine

def push_default_machine(machine):
    default_machine_stack = get_default_machine_stack()
    default_machine_stack.append(machine)

def pop_default_machine():
    default_machine_stack = get_default_machine_stack()
    default_machine_stack.pop()

@contextmanager
def make_default_machine(machine):
    push_default_machine(machine)
    yield machine
    pop_default_machine()

class DefaultMachine(object):
    proxied_attrs = frozenset(("cwd", "env", "path"))

    def __getitem__(self, items):
        return get_default_machine()[items]
    
    def __getattr__(self, attr):
        if attr in DefaultMachine.proxied_attrs:
            return getattr(get_default_machine(), attr)
        else:
            raise AttributeError("%r object has no attribute %r" %
                                     (self.__class__, attr))
    

default_machine = DefaultMachine()

# Logging support
def get_default_machine_name():
    current_default_machine = get_default_machine()
    if current_default_machine == local_machine:
        return "local"
    else:
        return str(current_default_machine)

class DefaultMachineLogAdapter(LoggerAdapter):
    def __init__(self, logger):
        super(DefaultMachineLogAdapter, self).__init__(logger, {})
    """
    This example adapter expects the passed in dict-like object to have a
    'connid' key, whose value in brackets is prepended to the log message.
    """
    def process(self, msg, kwargs):
        extras = kwargs.get("extra", {})

        if not "machinename" in extras:
            extras["machinename"] = get_default_machine_name()

        kwargs["extra"] = extras
        return msg, kwargs

class HostLogAdapter(LoggerAdapter):
    def __init__(self, logger, host):
        super(HostLogAdapter, self).__init__(logger, {})
        self._machinename = str(host.machine)
    """
    This example adapter expects the passed in dict-like object to have a
    'connid' key, whose value in brackets is prepended to the log message.
    """
    def process(self, msg, kwargs):
        extras = kwargs.get("extra", {})

        if not "machinename" in extras:
            extras["machinename"] = self._machinename

        kwargs["extra"] = extras
        return msg, kwargs

