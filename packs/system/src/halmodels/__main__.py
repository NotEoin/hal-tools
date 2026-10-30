"""`python -m halmodels`: the system pack command line limited to the models module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("models",)))
