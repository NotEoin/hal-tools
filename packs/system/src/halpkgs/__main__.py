"""`python -m halpkgs`: the system pack command line limited to the packages module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("packages",)))
