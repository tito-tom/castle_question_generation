
import argparse
import json
import re
import sys

from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def request_json(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict | None = None,
) -> tuple[int, dict]:
    """
    Send an HTTP request and return its status and JSON.
    """

    body = None
    headers = {}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url=f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )

    with urlopen(request, timeout=10) as response:
        return (
            response.status,
            json.loads(response.read()),
        )


def require(condition: bool, message: str) -> None:
    """
    Fail the smoke test when a condition is not met.
    """

    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test the CASTLE QA Studio API."
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )

    parser.add_argument(
        "--analysis-id",
        help="Optional analysis ID for question generation.",
    )

    parser.add_argument(
        "--clip-duration",
        type=float,
        help="Clip duration in seconds for generation.",
    )

    args = parser.parse_args()

    if (args.analysis_id is None) != (
        args.clip_duration is None
    ):
        parser.error(
            "--analysis-id and --clip-duration "
            "must be supplied together"
        )

    if (
        args.clip_duration is not None
        and args.clip_duration <= 0
    ):
        parser.error(
            "--clip-duration must be positive"
        )

    try:
        # Step 1: Verify the API is running.
        status, health = request_json(
            args.base_url,
            "/api/v1/health",
        )

        require(
            status == 200 and health.get("status") == "ok",
            "Health check failed",
        )

        print("[PASS] Health API")

        # Step 2: Verify analysis storage is accessible.
        status, data = request_json(
            args.base_url,
            "/api/v1/analyses",
        )

        analyses = data.get("analyses", [])

        require(
            status == 200 and isinstance(analyses, list),
            "Analysis list request failed",
        )

        require(
            len(analyses) > 0,
            "No analyses found. Check the Docker bind mount.",
        )

        print(
            f"[PASS] Analysis API ({len(analyses)} found)"
        )

        # Step 3: Retrieve an individual analysis.
        analysis_id = analyses[0]["analysis_id"]

        status, detail = request_json(
            args.base_url,
            f"/api/v1/analyses/{quote(analysis_id, safe='')}",
        )

        require(
            status == 200
            and detail.get("analysis_id") == analysis_id,
            "Analysis detail request failed",
        )

        print("[PASS] Analysis detail API")

        # Step 4: Optional question-generation check.
        if args.analysis_id is not None:
            available_ids = {
                item["analysis_id"]
                for item in analyses
            }

            require(
                args.analysis_id in available_ids,
                "Requested analysis ID was not found",
            )

            status, created = request_json(
                args.base_url,
                "/api/v1/question-generations",
                method="POST",
                payload={
                    "analysis_id": args.analysis_id,
                    "generator": "template",
                    "clip_duration_seconds": args.clip_duration,
                    "max_questions": 5,
                },
            )

            require(
                status == 201,
                "Question generation failed",
            )

            generation_id = created.get("generation_id")

            require(
                isinstance(generation_id, str)
                and re.fullmatch(
                    r"gen_[0-9a-f]{32}",
                    generation_id,
                ) is not None,
                "Invalid generation ID",
            )

            print("[PASS] Question generation API")

            # Step 5: Read the saved generation.
            status, saved = request_json(
                args.base_url,
                f"/api/v1/question-generations/{generation_id}",
            )

            require(
                status == 200 and saved == created,
                "Saved generation does not match POST result",
            )

            print("[PASS] Saved question retrieval API")
            print("Generation ID:", generation_id)

        print("\nAll requested smoke checks PASSED")
        return 0

    except (
        HTTPError,
        URLError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
    ) as error:
        print(
            f"\nSmoke test FAILED: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
