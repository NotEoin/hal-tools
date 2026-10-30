"""`python -m halnet`: the system pack command line limited to the network module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("network",)))
