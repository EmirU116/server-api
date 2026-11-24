"""Create and check credential files that only the installing user may read.

Shared by configure_ubuntu.py (native setup) and prepare_compose.sh (Compose).
Standard library only: both run before the project's virtual environment is
guaranteed to exist. Existing files are never overwritten.
"""

import os
import stat
from pathlib import Path


class NotPrivate(RuntimeError):
    """A fixed, safe explanation of why a path is not private."""


def require_private(path: Path, *, directory: bool = False) -> None:
    """Require a non-symlink owned by this user with mode 700 (dir) or 600 (file)."""
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != os.getuid():
        raise NotPrivate(
            f"{path.name} must be owned by this user and must not be a symlink."
        )
    mode = 0o700 if directory else 0o600
    if stat.S_IMODE(info.st_mode) != mode:
        raise NotPrivate(f"{path.name} requires permissions {mode:o}.")


def private_directory(path: Path) -> None:
    """Create the directory if needed, then require it to be private."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    require_private(path, directory=True)


def private_file(path: Path, content: str) -> None:
    """Create the file once with mode 600, then require it to be private."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with open(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
    require_private(path)
