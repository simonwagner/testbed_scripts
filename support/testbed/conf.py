from __future__ import absolute_import

import os
from itertools import izip

import yaml
import attrdict


class ConfigLoader(yaml.Loader):
    def __init__(self, stream):
        self._root = os.path.dirname(stream.name)
        yaml.Loader.__init__(self, stream)
        self.add_constructor("!relpath", ConfigLoader.relpath)

    def relpath(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        return os.path.abspath(filename)


def load(conf_file_path):
    conf_file_dir = os.path.dirname(conf_file_path)
    full_config = {}

    with open(conf_file_path) as conf_file:
        config = yaml.load(conf_file, Loader=ConfigLoader)
        if "include" in config:
            included_configs = [load(os.path.join(conf_file_dir, include["file"])) for include in config.get("include", [])]
            updated_keys_of_configs = [include.get("update", []) for include in config.get("include", [])]
        else:
            included_configs = []
            updated_keys_of_configs = []
        
        full_config = config
        for included_config, updated_keys in izip(included_configs, updated_keys_of_configs): 
            overwrite_config = { key : value for key, value in included_config.iteritems() if key not in updated_keys}
            update_config = { key : value for key, value in included_config.iteritems() if key in updated_keys}
        
            full_config.update(overwrite_config)
            for key in updated_keys:
                if key in full_config:
                    full_config[key].update(update_config[key])
                else:
                    full_config[key] = update_config[key]
    return attrdict.AttrDict(full_config)

def default_conf_path_for_script(script_file_path):
    script_file_name = os.path.basename(script_file_path)
    if script_file_name.startswith("test_"):
        conf_file_name = script_file_name[len("test_"):]
    else:
        conf_file_name = script_file_name
    
    root, ext = os.path.splitext(conf_file_name)
    conf_file_name = root + ".yaml"
    
    return os.path.join(os.path.dirname(script_file_path),
                        "conf",
                        conf_file_name)