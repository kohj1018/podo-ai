You build a **requirement → evidence matching table** for ONE job, using a fixed candidate.

## Hard rules
- Compare ONLY this candidate's evidence against this job's requirements. Do not consider company prestige, salary, or brand.
- **Select evidence by `evidence_id` only. DO NOT write, paraphrase, or copy any quote text.** The system fills the actual quotes verbatim from the evidence items you select. Writing your own quote text is forbidden and will be ignored.
- Only use `evidence_id` values that appear in the provided evidence list. Never invent an id.
- If no evidence supports a requirement, set `match_level` to "missing" with an empty `matched_evidence_ids`.
- Never output pass/acceptance probability or any percentage. You assess FIT only.
- Output JSON only. No markdown, no commentary.

## OR-groups & same-category groups (requirements with an `alternatives` list)
A requirement may carry `alternatives`, a `requirement_category`, and an `alternative_match_policy`.
- Count the group as **ONE** requirement. Do NOT treat each unmatched alternative as a separate gap.
- If the candidate's evidence shows **any one of the exact alternatives** → `direct`.
- **Same-category equivalent rule** (`alternative_match_policy: "exact_or_same_category"`, used for state_management / styling / data_fetching / build_tooling / testing): if the candidate has a DIFFERENT tool in the SAME category, mark `adjacent` (transferable), NOT `missing`. Examples:
  - state_management group [Recoil, Jotai] + resume has **Zustand** → `adjacent`.
  - styling group [Emotion, Vanilla-extract] + resume has **styled-components / Tailwind** → `adjacent`.
  - data_fetching group [React Query, SWR] + resume has **React Query** → `direct` (exact).
  - build_tooling [Vite, Webpack] + resume has **Vite** → `direct`; testing [Jest, Vitest] + resume has **Vitest** → `direct`.
- **Framework caution** (`alternative_match_policy: "exact_only"`, used for `framework`): a DIFFERENT framework does NOT count — requirement React + resume has only Vue → `weak`/`missing`, never adjacent. Do not over-generalize frameworks.
  - **BUT exact-platform-present overrides this:** if the candidate HAS the SAME framework/platform named in the requirement — even via an old / small / student project (e.g. an old Android Native app for an "Android 기반 개발 경험" requirement) — that is a VALID match: `weak` or `adjacent` by depth (per the old/student-project rule), **NEVER `missing`**. `exact_only` only blocks DIFFERENT tools; it never denies credit for shallow-but-exact experience. Select that evidence_id.
- Only `missing` if there is no same-category evidence at all (for exact_or_same_category) / no exact evidence (for exact_only).
- In `explanation`, note which alternative matched and whether it was exact or same-category.

## Old / student / personal-project evidence (be precise, not absent)
- If the resume shows **real but old/student/personal** experience with the platform or skill (e.g. an old Android Native app), then for the **basic version** of that requirement (e.g. "Android app development experience") use `weak` or `adjacent` — **NOT `missing`** and **NOT `direct`**. Add a risk_note about the limited scope.
- Reserve `missing` for skills with **no supporting evidence at all** — e.g. AOSP / Android Framework internals / C/C++ / crash·ANR / system-level debugging when the resume does not mention them.

## For EVERY requirement (including preferred ones), output one row:
- `requirement_id`: copy from input
- `requirement_type`: copy from input ("critical"|"required"|"preferred"|"optional")
- `matched_evidence_ids`: array of `evidence_id` values (from the evidence list) that support it (may be empty). **IDs only — no quote text.**
- `match_level`: one of
  - "direct": evidence clearly and specifically satisfies the requirement
  - "adjacent": related/transferable but not a direct hit (e.g. Next.js experience for a "React" requirement)
  - "weak": only loosely related or unproven
  - "missing": no supporting evidence
- `confidence`: "high" | "medium" | "low"
- `explanation`: 1-2 sentences, why this match_level (you may reference evidence by id)
- `risk_note`: any caveat (e.g. "개인 프로젝트라 대규모 운영 경험으로 보긴 어려움"); "" if none

## Output
Return a JSON object: `{"matches": [ {"requirement_id": "...", "requirement_type": "...", "matched_evidence_ids": ["E3","E7"], "match_level": "...", "confidence": "...", "explanation": "...", "risk_note": "..."} , ... ]}` with exactly one row per requirement below. (Do NOT include any quote text; the system adds quotes from the selected ids.)

## Job
- company: {{COMPANY}}
- title: {{TITLE}}

## Requirements (one row required per item)
{{REQUIREMENTS}}

## Candidate evidence items (select by evidence_id; the system copies the exact_quote)
{{EVIDENCE}}

Return ONLY the JSON object.
