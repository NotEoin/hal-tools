"""`python -m halphone`: the comms pack command line limited to the phone module."""

import sys

from halhub import pack

sys.exit(pack.main("comms", ("phone",)))
