<!-- 구조 변경 시 README.md와 README_ko.md를 동시에 갱신한다. 본문은 짧게, 깊은 정의는 docs/ 링크로 둔다. -->
# podo-ai

**Language: English | [한국어](README_ko.md)**

A SaaS that automatically collects developer job postings (starting with companies' official career pages) and scores each posting's **fit** and **pass likelihood** against the user's resume — with consistent, source-grounded reasoning. The first target user is a junior / new-grad developer job seeker.

> **Single thesis**: a *wrong* score is more damaging than a *missing* score. Score **consistency** and **evidence factuality** are the trust gate that takes priority over every other feature. See [DISCOVERY.md](docs/10-charter/DISCOVERY.md) (SSOT) and [PROJECT_CHARTER.md](docs/10-charter/PROJECT_CHARTER.md).

## Problem

Junior developer job seekers (1) miss new / closing postings while manually checking 7+ scattered channels every day, (2) cannot gauge pass likelihood when "open to juniors" postings hide real experience requirements, and (3) overestimate fit because JD keywords overlap while the actual required depth is unreadable. (Charter §3)

## MVP scope (gate-first)

- **Collect** — direct pipeline for 2 official career pages (Toss, Daangn) + coverage transparency panel + new/closing diff. (F1–F3)
- **Score** — deterministic cached scoring (temperature=0 / version-pinned), relative ranking, JD-quote-grounded evidence, resume↔JD mapping. (F4–F7)
- Pass likelihood is shown as a **5-level color band**, not an exact %.

Out of scope (Charter §5): full multi-channel coverage, resume/cover-letter authoring, absolute pass-probability calibration, scheduling / auto-apply, collaboration.

## Release gates (Charter §6)

- **GS-1 consistency** (🔴 blocking) — same (resume, JD) input → score variance 0 on cache hit; top-k order variance 0 on recompute.
- **GS-2 accuracy** (🔴 blocking) — hallucinated-requirement rate ≤ 2% in the shown evidence (≥30 sample).
- **GS-3 ranking validity** (🟡 post-launch) — recommended top group's pass rate > bottom group, measured after launch.

## Status

Early bootstrap. **Stack is undecided** — no stack-specific automation (hooks / CI / lint / test) has been added yet. All discovery assumptions (A-1…A-12) are **unverified** (pre-interview, pre-research). See the [assumption tracker](docs/10-charter/DISCOVERY.md) §12.

## Docs

- [DISCOVERY.md](docs/10-charter/DISCOVERY.md) — persona / pain / scenarios (SSOT)
- [PROJECT_CHARTER.md](docs/10-charter/PROJECT_CHARTER.md) — scope, goals, non-goals, success gates
- [ARCHITECTURE_OVERVIEW.md](docs/20-system/ARCHITECTURE_OVERVIEW.md) — modules (Collector / Scorer / Feed) + dependency rules
- [ADR-100](docs/90-decisions/project/ADR-100-initial-project-decisions.md) — initial decisions (trust gate, no 4-layer, deterministic cache)
- [WORKFLOW.md](docs/00-meta/WORKFLOW.md) · [STRUCTURE.md](docs/00-meta/STRUCTURE.md) — document-first dev process (inherited from the harness)

## Next steps

This project was bootstrapped from a document-first agentic harness. Recommended next command: `/bootstrap-stack` to lock the stack (the deterministic cache store and crawling approach must be chosen against GS-1 / A-1), then `/plan-workitem M1`.

## License

MIT
