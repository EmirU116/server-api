"""Describe the machine running Python using only the standard library.

Shared by the server API and scripts/setup/prepare_compose.sh. The Compose
preparation runs with the system Python, so this module must not import
third-party packages.
"""

import platform
from pathlib import Path


class ServerInfoUnavailable(Exception):
    """The host metadata source could not provide a complete identity."""

    public_message = "The operating system could not provide native host information."


class ContainerIdentityUnavailable(ServerInfoUnavailable):
    public_message = (
        "The API is running in a container without a native host identity source."
    )


def read_host_info() -> dict[str, str]:
    """Read the machine running Python, never present a container as the host.

    Native deployment is supported first. A container deployment needs a host
    metadata source before this function can truthfully describe the EC2 host.
    These common container markers are a guard, not universal detection.
    """
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        raise ContainerIdentityUnavailable

    os_type = platform.system()
    os_name = os_type
    os_version = platform.release()

    if os_type == "Linux":
        release = platform.freedesktop_os_release()
        os_name = release.get("NAME", "")
        os_version = release.get("VERSION_ID", "")

    return {
        "hostname": platform.node(),
        "os_type": os_type,
        "os_name": os_name,
        "os_version": os_version,
        "architecture": platform.machine(),
    }
