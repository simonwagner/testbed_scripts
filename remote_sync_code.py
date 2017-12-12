#!/usr/bin/env python
import argparse
import os

import yaml
from plumbum import FG

class ConfigLoader(yaml.Loader):
    def __init__(self, stream):
        self._root = os.path.dirname(stream.name)
        yaml.Loader.__init__(self, stream)
        self.add_constructor("!relpath", ConfigLoader.relpath)

    def relpath(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        return os.path.abspath(filename)

argparser = argparse.ArgumentParser()
argparser.add_argument("--host", "-H", required=True)
argparser.add_argument("--user", "-u", required=True)
argparser.add_argument("--config", "-c", type=argparse.FileType(), required=True)

RSYNC_OPTS = "--info=progress2 --no-inc-recursive -acz -e ssh --delete".split()

def main():
    from plumbum.cmd import rsync

    args = argparser.parse_args()
    
    config = yaml.load(args.config, Loader=ConfigLoader)

    rsync = rsync.bound_command(*RSYNC_OPTS)
    
    for sync_task in config:
        local = sync_task["local"]
        remote = sync_task["remote"]
        
        if not remote.endswith("/"):
            remote += "/"
        if not local.endswith("/"):
            local += "/"
        
        rsync[local, "{user}@{host}:{remote}".format(user=args.user,
                                                     host=args.host,
                                                     remote=remote)] & FG

if __name__ == "__main__":
    main()