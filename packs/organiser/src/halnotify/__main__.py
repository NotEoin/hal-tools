"""`python -m halnotify`: the organiser pack command line limited to the notify module."""

import sys

from halhub import pack

sys.exit(pack.main("organiser", ("notify",)))
