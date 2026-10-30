"""`python -m haltasks`: the organiser pack command line limited to the tasks module."""

import sys

from halhub import pack

sys.exit(pack.main("organiser", ("tasks",)))
