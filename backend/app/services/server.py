"""Read native host identity without a database or shell commands."""

import json
import platform
from pathlib import Path

from pydantic import ValidationError

from app.schemas.server import ServerInfo
from app.services.errors import UnknownServer


class ServerInfoUnavailable(Exception):
    """The host metadata source could not provide a complete identity."""

    public_message = "The operating system could not provide native host information."


class ContainerIdentityUnavailable(ServerInfoUnavailable):
    public_message = (
        "The API is running in a container without a native host identity source."
    )


class IncompleteHostIdentity(ServerInfoUnavailable):
    public_message = (
        "The operating system returned incomplete host identity information."
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


class ServerService:
    def __init__(
        self, server_id: int, name: str, host_identity_file: Path | None = None
    ) -> None:
        self.server_id = server_id
        self.name = name
        self.host_identity_file = host_identity_file

    def get_info(self, server_id: int | None = None) -> ServerInfo:
        """Treat missing or unreadable metadata as unavailable, not invented data."""
        if server_id is not None and server_id != self.server_id:
            raise UnknownServer

        try:
            metadata = (
                json.loads(self.host_identity_file.read_text(encoding="utf-8"))
                if self.host_identity_file is not None
                else read_host_info()
            )
            if not isinstance(metadata, dict):
                raise IncompleteHostIdentity
            if self.host_identity_file is not None:
                # The settings still own id/name. Read only host metadata fields.
                metadata = {
                    field: metadata.get(field)
                    for field in (
                        "hostname",
                        "os_type",
                        "os_name",
                        "os_version",
                        "architecture",
                    )
                }
            return ServerInfo(id=self.server_id, name=self.name, **metadata)
        except ValidationError:
            raise IncompleteHostIdentity from None
        except (OSError, ValueError):
            raise ServerInfoUnavailable from None
