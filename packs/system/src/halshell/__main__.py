"""`python -m halshell`: the system pack command line limited to the shell module."""

import sys

from halhub import pack

sys.exit(pack.main("system", ("shell",)))
