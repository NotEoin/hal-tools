"""`python -m halmail`: the comms pack command line limited to the mail module."""

import sys

from halhub import pack

sys.exit(pack.main("comms", ("mail",)))
