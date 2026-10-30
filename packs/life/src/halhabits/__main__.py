"""`python -m halhabits`: the life pack command line limited to the habits module."""

import sys

from halhub import pack

sys.exit(pack.main("life", ("habits",)))
