#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIGEST = ROOT / "feedback-digest.json"
OUT = ROOT / "council-report.json"


def score_issue(issue):
    labels = {label.get("name", "").lower() for label in issue.get("labels", [])}
    title = issue.get("title", "").lower()
    score = 0
    if "bug" in labels:
        score += 80
    if "feature" in labels:
        score += 35
    if "needs-triage" in labels:
        score += 10
    if "needs-council" in labels:
        score += 8
    if "crash" in title or "summon" in title or "hotkey" in title:
        score += 25
    if "package" in title or "debian" in title or "arch" in title:
        score += 18
    return score


def council_summary(digest):
    issues = digest.get("issues", [])
    prs = digest.get("pull_requests", [])

    ranked_issues = sorted(
        [
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "labels": [label.get("name") for label in issue.get("labels", [])],
                "updated_at": issue.get("updatedAt"),
                "state": issue.get("state"),
                "score": score_issue(issue),
                "kind": "bug" if "bug" in {label.get("name", "").lower() for label in issue.get("labels", [])} else "feature",
            }
            for issue in issues
        ],
        key=lambda item: item["score"],
        reverse=True,
    )

    top_bugs = [item for item in ranked_issues if item["kind"] == "bug"][:3]
    top_features = [item for item in ranked_issues if item["kind"] == "feature"][:3]

    release_ready = not top_bugs
    remove_or_postpone = (
        "Delay non-core settings and surface-area changes until summon reliability, packaging, and provider switching are stable."
        if top_bugs
        else "Remove any duplicate settings that do not affect summon speed or operator clarity."
    )

    return {
        "repo": digest.get("repo"),
        "generated_from": str(DIGEST),
        "issue_count": len(issues),
        "pull_request_count": len(prs),
        "top_bugs": top_bugs,
        "top_features": top_features,
        "release_recommendation": "release" if release_ready else "hold",
        "rationale": "No open bug reports in the digest." if release_ready else "Open bug reports still outrank feature expansion.",
        "simplify_or_postpone": remove_or_postpone,
    }


def main():
    if not DIGEST.exists():
        raise SystemExit(f"missing digest: {DIGEST}")
    digest = json.loads(DIGEST.read_text())
    report = council_summary(digest)
    OUT.write_text(json.dumps(report, indent=2))
    print(OUT)


if __name__ == "__main__":
    main()
