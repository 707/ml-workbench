"""Verify a Hugging Face Space runtime catches up to the pushed repo SHA."""

from __future__ import annotations

import argparse
import os
import sys
import time

import requests


def _headers() -> dict[str, str]:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def fetch_space(space_id: str) -> dict:
    response = requests.get(
        f"https://huggingface.co/api/spaces/{space_id}",
        headers=_headers(),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def verify(space_id: str, timeout_seconds: int, poll_seconds: int) -> int:
    deadline = time.time() + timeout_seconds
    repo_sha = None

    while time.time() < deadline:
        payload = fetch_space(space_id)
        repo_sha = payload.get("sha")
        runtime = payload.get("runtime", {}) or {}
        runtime_sha = runtime.get("sha")
        stage = runtime.get("stage")

        print(
            f"space={space_id} repo_sha={repo_sha} runtime_sha={runtime_sha} stage={stage}",
            flush=True,
        )

        if repo_sha and runtime_sha == repo_sha and stage not in {"RUNNING_BUILDING", "BUILDING"}:
            return 0

        time.sleep(poll_seconds)

    print(
        f"Timed out waiting for runtime to catch up to repo SHA for {space_id}.",
        file=sys.stderr,
        flush=True,
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--poll", type=int, default=5)
    args = parser.parse_args()
    return verify(args.space, args.timeout, args.poll)


if __name__ == "__main__":
    raise SystemExit(main())
