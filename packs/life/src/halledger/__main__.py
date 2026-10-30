"""`python -m halledger`: the life pack command line limited to the ledger module."""

import sys

from halhub import pack

sys.exit(pack.main("life", ("ledger",)))
