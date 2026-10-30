"""`python -m halbrief`: the organiser pack command line limited to the briefing module."""

import sys

from halhub import pack

sys.exit(pack.main("organiser", ("briefing",)))
