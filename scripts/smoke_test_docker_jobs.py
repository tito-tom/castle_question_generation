
"""
Docker persistence smoke test for CASTLE QA Studio.

Checks that an inference job remains available after
the FastAPI container is recreated.
"""

import argparse
import json
import re
import subprocess
import sys
import time

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def request_json(base_url: str, path: str) -> dict:
    """
    Retrieve a JSON response from the API.
    """

    url = f"{base_url.rstrip('/')}{path}"

    with urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Unexpected HTTP status: {response.status}"
            )

        return json.load(response)


def wait_for_api(
    base_url: str,
    timeout_seconds: int = 90,
) -> None:
    """
    Wait until FastAPI becomes healthy.
    """

    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            health = request_json(
                base_url,
                "/api/v1/health",
            )

            if health.get("status") == "ok":
                return

        except (HTTPError, URLError, TimeoutError, OSError):
            pass

        time.sleep(2)

    raise RuntimeError(
        "FastAPI did not become healthy in time"
    )


def recreate_api_container() -> None:
    """
    Recreate only the FastAPI service.

    Persistent host-mounted data should survive.
    """

    command = [
        "docker",
        "compose",
        "up",
        "-d",
        "--no-deps",
        "--force-recreate",
        "api",
    ]

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Docker persistence of a CASTLE GPU job."
        )
    )

    parser.add_argument(
        "--job-id",
        required=True,
        help="Existing inference job ID.",
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )

    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the API container during the test.",
    )

    args = parser.parse_args()

    if not re.fullmatch(
        r"job_[0-9a-f]{32}",
        args.job_id,
    ):
        parser.error("Invalid job ID format")

    job_path = f"/api/v1/jobs/{args.job_id}"

    # Step 1: Retrieve the existing job.
    before = request_json(
        args.base_url,
        job_path,
    )

    if before.get("job_id") != args.job_id:
        raise RuntimeError(
            "Job ID does not match the requested job"
        )

    print("[PASS] Existing job retrieved")
    print("Job ID:", before["job_id"])
    print("Status:", before["status"])

    # Step 2: Optionally recreate the container.
    if args.recreate:
        print("\nRecreating FastAPI container...")

        recreate_api_container()

        wait_for_api(args.base_url)

        print("[PASS] API restarted successfully")

    # Step 3: Retrieve the same job again.
    after = request_json(
        args.base_url,
        job_path,
    )

    # These fields must survive container recreation.
    stable_fields = (
        "job_id",
        "job_type",
        "analysis_id",
        "created_at",
    )

    for field in stable_fields:
        if before.get(field) != after.get(field):
            raise RuntimeError(
                f"Job field changed unexpectedly: {field}"
            )

    print("[PASS] Job data preserved")
    print("Status after test:", after["status"])

    print("\nDocker job persistence test PASSED")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())

    except (
        HTTPError,
        URLError,
        OSError,
        ValueError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as error:
        print(
            f"[FAIL] {error}",
            file=sys.stderr,
        )
        sys.exit(1)
