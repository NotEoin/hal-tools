"""`python -m halmedia`: the desktop pack command line limited to the media module."""

import sys

from halhub import pack

sys.exit(pack.main("desktop", ("media",)))
