"""`python -m haldevices`: the system pack command line limited to the devices module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("devices",)))
