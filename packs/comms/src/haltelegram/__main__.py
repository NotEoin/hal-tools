"""`python -m haltelegram`: the comms pack command line limited to the telegram module."""

import sys

from halhub import pack

sys.exit(pack.main("comms", ("telegram",)))
