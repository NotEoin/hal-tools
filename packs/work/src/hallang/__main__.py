"""`python -m hallang`: the work pack command line limited to the lang module."""

import sys

from halhub import pack

sys.exit(pack.main("work", ("lang",)))
