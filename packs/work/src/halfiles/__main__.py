"""`python -m halfiles`: the work pack command line limited to the files module."""

import sys

from halhub import pack

sys.exit(pack.main("work", ("files",)))
