"""`python -m haldev`: the work pack command line limited to the dev module."""

import sys

from halhub import pack

sys.exit(pack.main("work", ("dev",)))
