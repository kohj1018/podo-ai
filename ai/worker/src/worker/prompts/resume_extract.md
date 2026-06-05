You extract structured **evidence items** from a candidate's resume.

## Hard rules
- Use ONLY the resume text given below. NEVER invent, infer, or embellish facts.
- `exact_quote` MUST be copied **verbatim** (character-for-character) from the resume text. Do not paraphrase inside `exact_quote`.
- If you are unsure whether something is in the resume, leave it out.
- Output JSON only. No markdown, no commentary.

## Granularity
- Create one evidence item per distinct, meaningful unit: each work experience, each project, each notable achievement, each education entry, each award/certification, each activity.
- Prefer several focused items over one giant item. A single job or project may yield multiple evidence items if it contains distinct accomplishments (e.g., a latency optimization vs. a monorepo refactor).

## Output schema
Return a JSON object: `{"evidence": [ <EvidenceItem>, ... ]}`

Each EvidenceItem:
- `evidence_id`: short stable id you assign, e.g. "E1", "E2", ...
- `title`: short human label (e.g. "NAVER LABS 인턴 - 카메라 스트리밍 지연 최적화")
- `source_section`: the resume heading this came from (e.g. "Experience", "Projects")
- `exact_quote`: a verbatim span copied from the resume that backs this item (keep it focused; you may join a few consecutive bullet lines with "\n")
- `normalized_summary`: your own 1-2 sentence neutral summary
- `skills`: array of concrete skills/technologies mentioned for this item (verbatim tokens, e.g. ["React", "WebTransport"])
- `domain`: array of domains/areas (e.g. ["frontend", "infra", "robotics"]) — only if evident
- `evidence_type`: one of "work_experience" | "project" | "education" | "award" | "activity" | "other"
- `strength`: one of "strong" | "medium" | "weak"
  - "strong": professional/production work, real users at scale, measurable outcomes, internships at companies
  - "medium": substantial personal/team projects with real usage, coursework with depth
  - "weak": short activities, early/small projects, unquantified claims
- `recency`: a date or year string if the resume states one (e.g. "2025"); otherwise null

## Resume text
<<<RESUME
{{RESUME_TEXT}}
RESUME

Return ONLY the JSON object.
