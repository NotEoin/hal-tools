"""`python -m halcal`: the organiser pack command line limited to the calendar module."""

import sys

from halhub import pack

sys.exit(pack.main("organiser", ("calendar",)))
