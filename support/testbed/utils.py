from __future__ import absolute_import

import os
import errno
from datetime import datetime
import sys
import traceback
import time

from plumbum import FG, RETCODE
from plumbum.commands.modifiers import ExecutionModifier
from plumbum.commands.processes import run_proc, ProcessExecutionError
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from .machine import default_machine

DEFAULT_RSYNC_ARGS = ["--info=progress2",
                      "--no-inc-recursive",
                      "-acz",
                      "-e",
                      "ssh"]

def push(local_path, user, host, remote_path, delete=True):
    rsync = default_machine["rsync"][DEFAULT_RSYNC_ARGS]
    if delete:
        rsync = rsync["--delete"]

    rsync[local_path, "%s@%s:%s" % (user, host, remote_path)] & FG

def pull(user, host, remote_path, local_path, delete=True):
    rsync = default_machine["rsync"][DEFAULT_RSYNC_ARGS]
    if delete:
        rsync = rsync["--delete"]

    rsync["%s@%s:%s" % (user, host, remote_path), local_path] & FG

def timestamped_logfile_path(dir, postfix):
    if dir is None:
        # yeah, this is hacky but it makes the code so much nicer
        return "/dev/null"
    t = datetime.now()
    ts = t.strftime("%Y-%m-%d_%H-%M-%S")
    filename = ts + "_" + postfix + ".log"
    return os.path.join(dir, filename)

def clear_directory(dir, machine=default_machine):
    path = default_machine.path(dir)
    for entry in path.iterdir():
        entry.delete()

def mkdir_ignore_existing(path):
    default_machine["mkdir"]("-p", path)

def set_sysctl(sysctl_dict):
    for key, value in sysctl_dict.iteritems():
        default_machine["sysctl"]("-w", "%s=%s" % (key, value))

def results_of_futures(futures, timeout=None):
    return [future.result(timeout=timeout) for future in futures]

def do_parallel(*jobs):
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        futures = [executor.submit(job) for job in jobs]
        return results_of_futures(futures)

def send_signal(pid_file, signal, machine=default_machine, times=1):
    for i in range(times):
        machine["pkill"]("-%s" % signal, "-F", pid_file, retcode=[0,1])
        if times == 1:
            break
        if (machine["pkill"]["--count", "-F", pid_file] & RETCODE) == 1:
            # no matching process exists anymore, so we exit now
            break

def print_stacktrace():
    print >> sys.stderr, "\n*** STACKTRACE - START ***\n"
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# ThreadID: %s" % threadId)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename,
                                                        lineno, name))
            if line:
                code.append("  %s" % (line.strip()))

    for line in code:
        print >> sys.stderr, line
    print >> sys.stderr, "\n*** STACKTRACE - END ***\n"

# plumbum has issues with its background processes, so we implement our own
# we call it BGT for BackGround Threaded
class ProcessFuture(object):
    """Represents a "future result" of a running process. It basically wraps a ``Popen``
    object and the expected exit code, and provides poll(), wait(), returncode, stdout,
    and stderr.
    """
    def __init__(self, proc, future, timeout=None):
        self.proc = proc
        self._future = future
        self._returncode = None
        self._stdout = None
        self._stderr = None
        self._timeout = timeout

    def __repr__(self):
        return "<ProcessFuture %r (%s)>" % (self.proc.argv, self._returncode if self.ready() else "running",)

    def poll(self):
        """Polls the underlying process for termination; returns ``False`` if still running,
        or ``True`` if terminated"""
        if self.proc.poll() is not None:
            self.wait()
        return self._returncode is not None
    ready = poll

    def wait(self):
        """Waits for the process to terminate; will raise a
        :class:`plumbum.commands.ProcessExecutionError` in case of failure"""
        if self._returncode is not None:
            return
        self._returncode, self._stdout, self._stderr = self._future.result()

    @property
    def stdout(self):
        """The process' stdout; accessing this property will wait for the process to finish"""
        self.wait()
        return self._stdout

    @property
    def stderr(self):
        """The process' stderr; accessing this property will wait for the process to finish"""
        self.wait()
        return self._stderr

    @property
    def returncode(self):
        """The process' returncode; accessing this property will wait for the process to finish"""
        self.wait()
        return self._returncode

class BGT(ExecutionModifier):
    def __init__(self, executor, retcode=0, timeout=None, **kwargs):
        self.retcode = retcode
        self.kwargs = kwargs
        self.timeout = timeout
        self._executor = executor

    def __rand__(self, cmd):
        proc = cmd.popen(**self.kwargs)
        future = self._executor.submit(self.run, proc)
        return ProcessFuture(proc, future, timeout=self.timeout)

    def run(self, proc):
        return run_proc(proc, self.retcode, self.timeout)