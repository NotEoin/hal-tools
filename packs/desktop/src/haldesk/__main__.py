"""`python -m haldesk`: the desktop pack command line limited to the desktop module."""

import sys

from halhub import pack

sys.exit(pack.main("desktop", ("desktop",)))
