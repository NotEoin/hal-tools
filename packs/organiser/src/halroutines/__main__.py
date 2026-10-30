"""`python -m halroutines`: the organiser pack command line limited to the routines module."""

import sys

from halhub import pack

sys.exit(pack.main("organiser", ("routines",)))
