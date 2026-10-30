"""`python -m halrgb`: the desktop pack command line limited to the rgb module."""

import sys

from halhub import pack

sys.exit(pack.main("desktop", ("rgb",)))
