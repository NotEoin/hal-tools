"""`python -m halscreen`: the desktop pack command line limited to the screen module."""

import sys

from halhub import pack

sys.exit(pack.main("desktop", ("screen",)))
