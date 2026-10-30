"""`python -m halpower`: the system pack command line limited to the power module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("power",)))
