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

**M1 (algorithm port)** and **M2 (service wiring)** are implemented: the verified fit-ranking algorithm now runs end-to-end as a service — crawl → worker scoring (deterministic, cache-based) → Postgres → API serving → feed UI with 5-level fit badges, JD-quote evidence, and a coverage panel. The whole pipeline is reproducible locally **offline / keyless** via `pnpm e2e` (see below). Stack ([ADR-101](docs/90-decisions/project/ADR-101-stack-selection.md)) and design system ([DESIGN.md](docs/20-system/DESIGN.md), concept "포도 친구") are locked. **A-1 (crawling feasibility) verified** (2026-06-04); the other discovery assumptions (A-2…A-12) remain **unverified** (pre-interview). See the [assumption tracker](docs/10-charter/DISCOVERY.md) §12.

## Local E2E (offline, keyless)

A single command runs the full pipeline against committed fixtures with **zero external LLM calls** (deterministic LLM responses are replayed from a committed warm cache):

```bash
pnpm e2e        # docker compose up → prisma migrate → crawl(fixture) → score(warm cache) → serve → assert feed/coverage
```

Prerequisites: Docker, Node ≥18 (`pnpm install`), and `uv` (Python). The crawl step uses `crawler/fixtures/seed_jobs.txt` instead of live Toss/Daangn APIs, and scoring replays `ai/worker/fixtures/llm_cache` — so no network and no `OPENAI_API_KEY` are needed.

**One-time warm-cache seed (key holder only):** the committed warm cache is generated once by a key holder. With `OPENAI_API_KEY` set, run `pnpm e2e:warm` and commit the produced `ai/worker/fixtures/llm_cache/*.json`. After that, `pnpm e2e` and the `e2e-smoke` CI gate pass keyless. The same code path runs with or without a key — only cache hit vs. miss differs.

## Docs

- [DISCOVERY.md](docs/10-charter/DISCOVERY.md) — persona / pain / scenarios (SSOT)
- [PROJECT_CHARTER.md](docs/10-charter/PROJECT_CHARTER.md) — scope, goals, non-goals, success gates
- [ARCHITECTURE_OVERVIEW.md](docs/20-system/ARCHITECTURE_OVERVIEW.md) — modules (Collector / Scorer / Feed) + dependency rules
- [ADR-100](docs/90-decisions/project/ADR-100-initial-project-decisions.md) — initial decisions (trust gate, no 4-layer, deterministic cache) · [ADR-101](docs/90-decisions/project/ADR-101-stack-selection.md) — stack selection
- [DESIGN.md](docs/20-system/DESIGN.md) — UI design system SSOT (tokens / components / motion)
- [WORKFLOW.md](docs/00-meta/WORKFLOW.md) · [STRUCTURE.md](docs/00-meta/STRUCTURE.md) — document-first dev process (inherited from the harness)

## Next steps

M1 and M2 are implemented. To run the pipeline locally, use `pnpm e2e` (see [Local E2E](#local-e2e-offline-keyless)). The next milestone (M3) is not yet scoped — define it from the [DISCOVERY](docs/10-charter/DISCOVERY.md) §13 opportunity backlog (`/discover-product --update`), then **`/plan-workitem M3`** to decompose it.

## License

MIT
