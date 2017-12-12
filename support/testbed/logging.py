from __future__ import absolute_import

import logging

DEFAULT_FIELD_STYLES = {
    'name': {
        'color': 'white'
    },
    'asctime': {
        'color': 'blue'
    },
    'machinename' : {
        'color': 'magenta'
    }
}

def setup():
    import coloredlogs
    coloredlogs.install(fmt='%(asctime)s %(levelname)-8s %(name)-18s [%(machinename)-20s]: %(message)s',
                        field_styles=DEFAULT_FIELD_STYLES)
    # Custom Logger that always adds machinename if it does not exist in extras
    # so that formatting will always work
    class TestbedLogger(logging.getLoggerClass()):
        def makeRecord(self, *args, **kwargs):
            rv = super(TestbedLogger, self).makeRecord(*args, **kwargs)
            if "machinename" not in rv.__dict__:
                rv.__dict__["machinename"] = ""
            return rv

    logging.setLoggerClass(TestbedLogger)

setup()