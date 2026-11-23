"""POST actual local host measurements, then sleep five seconds and repeat."""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPException
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def load_collector_token(env_file: Path) -> str:
    """Load the collector credential privately; never send the reader token."""
    from app.core.config import load_settings
    from app.core.security import load_token
    from dotenv import load_dotenv

    if not env_file.is_file():
        raise RuntimeError("Missing local configuration.")
    load_dotenv(env_file, override=False)
    settings = load_settings()
    token = load_token(
        settings.collector_token, settings.collector_token_file, "Collector"
    )
    if token is None:
        raise RuntimeError("Configure a collector token.")
    return token.get_secret_value()


def collect_sample() -> dict[str, str | float | int]:
    """Measure this machine, including disk usage on the home drive/filesystem.

    A brief CPU sampling interval avoids psutil's meaningless first nonblocking
    reading. Timestamp the completed sample so it precedes the API receipt time.
    """
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage(Path.home().anchor).percent
    uptime = max(0, int(time.time() - psutil.boot_time()))
    return {
        "collected_at": datetime.now(UTC).isoformat(),
        "cpu_percent": cpu,
        "memory_percent": memory,
        "disk_percent": disk,
        "uptime_seconds": uptime,
    }


def post_sample(sample: dict, token: str, api_port: int = 8000) -> int:
    """POST only to the local API, with a timeout and no redirect following."""
    body = json.dumps(sample, allow_nan=False).encode()
    connection = HTTPConnection("127.0.0.1", api_port, timeout=3)
    try:
        connection.request(
            "POST",
            "/api/v1/metrics",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        return connection.getresponse().status
    finally:
        connection.close()


def run_collector(token: str, api_port: int = 8000) -> None:
    """Keep the local test deliberately simple: collect, send, sleep, repeat.

    Failed samples are skipped, with the next fresh sample attempted after the
    sleep. This is not a durable queue or an exactly timed production scheduler.
    Only safe status messages are printed, never credentials or response bodies.
    """
    while True:
        try:
            status = post_sample(collect_sample(), token, api_port)
            if status == 201:
                print("PASS: Local measurement recorded.", flush=True)
            else:
                print(
                    f"WARN: Metrics POST returned HTTP {status}. "
                    "Check the API, migration, and collector token; retrying.",
                    flush=True,
                )
        except (OSError, ValueError, HTTPException, psutil.Error):
            print("WARN: Could not collect/send measurements; retrying.", flush=True)
        time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--api-port", type=int, default=8000, help="Loopback HTTP port")
    args = parser.parse_args()
    if not 1 <= args.api_port <= 65535:
        parser.error("--api-port must be between 1 and 65535")
    try:
        token = load_collector_token(args.env_file)
    except Exception:
        raise SystemExit(
            "FAIL: Check local .env and SERVERWATCH_COLLECTOR_TOKEN "
            "or SERVERWATCH_COLLECTOR_TOKEN_FILE."
        ) from None
    print("Local collector started. Collect -> POST -> sleep 5s. Ctrl+C stops it.")
    try:
        run_collector(token, args.api_port)
    except KeyboardInterrupt:
        print("Local collector stopped.")


if __name__ == "__main__":
    main()
