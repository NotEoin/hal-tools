"""`python -m halfeeds`: the online pack command line limited to the feeds module."""

import sys

from halhub import pack

sys.exit(pack.main("online", ("feeds",)))
