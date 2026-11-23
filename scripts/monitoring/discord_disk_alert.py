"""Report one Discord alert per root disk usage breach on the EC2 host."""

import argparse
import http.client
import json
import os
import re
import shutil
import socket
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit


class AlertError(Exception):
    """A configuration or delivery problem safe to print to the journal."""


def webhook_path(url: str) -> str:
    """Accept only a direct HTTPS Discord webhook with no query or fragment."""
    try:
        parts = urlsplit(url)
    except ValueError:
        raise AlertError("Configure a valid HTTPS Discord webhook.") from None
    if (
        parts.scheme != "https"
        or parts.netloc != "discord.com"
        or parts.query
        or parts.fragment
        or not re.fullmatch(r"/api/webhooks/[0-9]+/[A-Za-z0-9_-]+", parts.path)
    ):
        raise AlertError("Configure a valid HTTPS discord.com channel webhook.")
    return parts.path


def send_alert(path: str, message: str) -> None:
    """Keep the webhook path private. The HTTP client never follows redirects."""
    connection = http.client.HTTPSConnection("discord.com", timeout=8)
    try:
        body = json.dumps({"content": message, "allowed_mentions": {"parse": []}})
        connection.request(
            "POST",
            f"{path}?wait=true",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        status = connection.getresponse().status
    except (OSError, http.client.HTTPException):
        raise AlertError("Could not reach Discord over HTTPS. Will retry.") from None
    finally:
        connection.close()
    if not 200 <= status < 300:
        raise AlertError(
            f"Discord returned HTTP {status}. Check the webhook and rate limits."
        )


def save_state(state: Path, content: str) -> None:
    """Replace state atomically so an interrupted write leaves readable state."""
    with NamedTemporaryFile(dir=state.parent, delete=False, mode="w") as temporary:
        path = Path(temporary.name)
        try:
            temporary.write(content)
            temporary.close()
            path.replace(state)
        finally:
            path.unlink(missing_ok=True)


def check_disk(threshold: int, path: str, state: Path) -> str:
    """Rearm on recovery. A failed delivery leaves the breach eligible for retry."""
    _, used_bytes, available_bytes = shutil.disk_usage("/")
    usable_bytes = used_bytes + available_bytes
    if not usable_bytes:
        raise AlertError("The root filesystem has no measurable disk capacity.")
    used = used_bytes / usable_bytes * 100
    try:
        previous = state.read_text(encoding="utf-8")
    except FileNotFoundError:
        previous = "clear"

    if previous not in {"clear", "alerted"}:
        raise AlertError("Disk alert state is invalid. Inspect it before resuming.")
    if used < threshold:
        if previous == "alerted":
            save_state(state, "clear")
        return f"Root disk usage {used:.1f}% is below {threshold}%."
    if previous == "alerted":
        return f"Already alerted for this root disk breach ({used:.1f}%)."

    send_alert(
        path,
        f"ServerWatch: {socket.gethostname()} root disk usage is {used:.1f}% "
        f"(threshold {threshold}%). Check available disk space.",
    )
    save_state(state, "alerted")
    return f"Discord alert delivered for root disk usage {used:.1f}%."


def read_webhook(file: Path) -> str:
    try:
        return webhook_path(file.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        raise AlertError("Could not read the private webhook file.") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-webhook", type=Path)
    parser.add_argument("--threshold", type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.threshold <= 100:
        parser.error("--threshold must be between 1 and 100")
    try:
        if args.validate_webhook:
            read_webhook(args.validate_webhook)
        else:
            credentials = Path(os.environ["CREDENTIALS_DIRECTORY"])
            state = Path(os.environ["STATE_DIRECTORY"]) / "disk-state"
            print(
                check_disk(args.threshold, read_webhook(credentials / "webhook"), state)
            )
    except AlertError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    except (KeyError, OSError, UnicodeError):
        print("[FAIL] Could not access disk usage or systemd state.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
