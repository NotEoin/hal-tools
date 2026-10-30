"""`python -m halcontacts`: the life pack command line limited to the contacts module."""

import sys

from halhub import pack

sys.exit(pack.main("life", ("contacts",)))
