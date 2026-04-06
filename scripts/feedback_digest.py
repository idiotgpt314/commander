#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "feedback-digest.json"
REPO = "idiotgpt314/commander"


def gh_json(args):
    result = subprocess.run(
        ["gh", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip(), "items": []}
    try:
        return {"items": json.loads(result.stdout or "[]")}
    except Exception:
        return {"error": "invalid-json", "items": []}


def main():
    issues = gh_json(
        [
            "issue",
            "list",
            "--repo",
            REPO,
            "--limit",
            "100",
            "--json",
            "number,title,labels,updatedAt,state",
        ]
    )
    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            REPO,
            "--limit",
            "100",
            "--json",
            "number,title,reviewDecision,updatedAt,state",
        ]
    )
    digest = {
        "repo": REPO,
        "issues": issues["items"],
        "pull_requests": prs["items"],
        "issue_count": len(issues["items"]),
        "pull_request_count": len(prs["items"]),
    }
    OUT.write_text(json.dumps(digest, indent=2))
    print(OUT)


if __name__ == "__main__":
    main()
