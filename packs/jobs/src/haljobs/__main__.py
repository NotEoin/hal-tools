"""`python -m haljobs`: the jobs pack command line limited to the jobs module."""

import sys

from halhub import pack

sys.exit(pack.main("jobs", ("jobs",)))
