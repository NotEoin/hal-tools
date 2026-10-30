"""`python -m halweb`: the online pack command line limited to the web module."""

import sys

from halhub import pack

sys.exit(pack.main("online", ("web",)))
