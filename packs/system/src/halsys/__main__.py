"""`python -m halsys`: the system pack command line limited to the system module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("system",)))
