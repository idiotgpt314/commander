# Commander Maintainers

## Core Loop

1. Pull open issues, PR reviews, and discussions into a digest
2. Group duplicates and identify repeated failures
3. Escalate bugs and regressions before feature work
4. Run the Commander Council rubric before expanding surface area
5. Ship the smallest safe fix, verify it locally, then update packaging

## Required Signals

- GitHub issues labeled `bug`
- GitHub issues labeled `feature`
- PR review feedback
- package install failures
- hotkey summon failures
- distro-specific breakage

## Automation

- use `scripts/feedback_digest.py` to build a review/issue digest
- use `scripts/council_report.py` to rank fixes and features from that digest
- use the `commander-maintainer` skill for autonomous triage and fixes
- use the `commander-council` skill to debate roadmap items cleanly
