"""Sends an alert through hal-notify when it is installed, else to the desktop and ntfy.

Reads the ntfy topic from the [notify] table of the shared config.
"""

import logging
import shutil
import subprocess
import urllib.request

from halkit import paths
from halkit.config import ConfigError, read_toml

log = logging.getLogger(__name__)


def notify(title: str, body: str = "", urgent: bool = False, speak: bool = False) -> None:
    """Sends a notification; never raises."""
    hal = shutil.which("hal-hub")
    if hal:
        args = [
            hal,
            "notify_send",
            f"title={title}",
            f"body={body}",
            f"urgent={urgent}",
            f"speak={speak}",
        ]
        try:
            if subprocess.run(args, capture_output=True, timeout=20).returncode == 0:
                return
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        subprocess.run(
            ["notify-send", "-a", "Hal", *(["-u", "critical"] if urgent else []), title, body],
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        topic = read_toml(paths.config_file()).get("notify", {}).get("ntfy_topic", "")
    except ConfigError:
        log.exception("notify config is invalid; skipping the phone channel")
        topic = ""
    if topic:
        headers = {"Title": title.encode(), **({"Priority": "high"} if urgent else {})}
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    f"https://ntfy.sh/{topic}", data=body.encode(), headers=headers
                ),
                timeout=10,
            )
        except OSError:
            pass
