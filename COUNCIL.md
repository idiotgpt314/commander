# Commander Council

The Commander Council exists to keep feature work clean, useful, and supportable.

## Members

- Product Steward: rejects clutter and protects the core launcher flow
- Reliability Lead: prioritizes hotkeys, packaging, startup, and recovery paths
- Operator Advocate: represents power-user workflows and repeated real tasks
- Release Lead: checks packaging, distro support, migration risk, and docs

## Decision Rules

- Reliability beats novelty
- One new surface must justify itself against startup cost and UI complexity
- A feature that adds settings must remove ambiguity, not create it
- Bug fixes from real user reports outrank speculative features
- Packaging and upgrade safety are first-class product concerns

## Intake Order

1. Crashers and summon-path failures
2. Packaging regressions
3. Review feedback from merged PRs
4. Repeated bug reports
5. Repeated feature requests
6. Marketing or monetization work that does not degrade the free product

## Weekly Output

- top 3 bugs
- top 3 candidate features
- one release/no-release recommendation
- one thing to remove, simplify, or postpone

## Automation Path

1. run `scripts/feedback_digest.py`
2. run `scripts/council_report.py`
3. feed the report into the maintainer skill
4. ship fixes before adding surface area
