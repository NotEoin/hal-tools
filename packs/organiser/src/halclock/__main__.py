"""`python -m halclock`: the organiser pack command line limited to the clock module."""

import sys

from halhub import pack

sys.exit(pack.main("organiser", ("clock",)))
