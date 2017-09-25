#!/usr/bin/env python
import sys
import argparse
import re
from string import Template

argparser = argparse.ArgumentParser()
argparser.add_argument("--template", "-t", type=argparse.FileType("r"))
argparser.add_argument("--output", "-o", type=argparse.FileType("w"), default=sys.stdout)
argparser.add_argument("--var", "-v", dest="vars", action="append", default=[])

VAR_EXP_RE = re.compile("([A-Za-z_][A-Za-z0-9_]*)=(.*)")

def main():
    args = argparser.parse_args()
    
    template = Template(args.template.read())
    args.template.close()
    
    vars_dict = {}
    
    for var in args.vars:
        var_match = VAR_EXP_RE.match(var)
        if var_match is None:
            raise ValueError("'%s' is not a valid expression" % var)
        
        var_name = var_match.group(1)
        var_value = var_match.group(2)
        
        vars_dict[var_name] = var_value

    result = template.substitute(vars_dict)
    
    args.output.write(result)
    args.output.close()

if __name__ == "__main__":
    main()