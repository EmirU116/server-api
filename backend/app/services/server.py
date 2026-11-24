"""Read native host identity without a database or shell commands."""

import json
from pathlib import Path

from pydantic import ValidationError

from app.host_identity import (
    ContainerIdentityUnavailable,
    ServerInfoUnavailable,
    read_host_info,
)
from app.schemas.server import ServerInfo
from app.services.errors import UnknownServer

__all__ = [
    "ContainerIdentityUnavailable",
    "IncompleteHostIdentity",
    "ServerInfoUnavailable",
    "ServerService",
    "read_host_info",
]


class IncompleteHostIdentity(ServerInfoUnavailable):
    public_message = (
        "The operating system returned incomplete host identity information."
    )


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
