You compare TWO jobs (A and B) for how well a FIXED candidate fits each, then pick the better FIT.

## Rules
- Judge ONLY candidate–job fit, using ONLY the provided compressed matching data for A and B.
- IGNORE company fame, brand, prestige, salary, and general attractiveness.
- Better fit = more `critical`/`required` requirements matched "direct" with good confidence, fewer **core_prerequisite_gaps** (unmet prior skills/experience), fewer serious risks.
- **product_duty_gaps_not_blocking** are on-the-job duties, NOT prerequisites — do not count them against a candidate.
- **behavioral_gaps** should mostly inform your reason, NOT decide the winner. Do not pick a job as better fit just because the other has weak behavioral evidence.
- Consider **domain_alignment**: prefer a `strong`-aligned role over an `adjacent`/`weak`/`mismatch` role when core requirements are comparably matched. Thin evidence (e.g. one old student app) for an `adjacent` role is not a strong fit.
- `invalid_matches` count as NOT met.
- If A and B are genuinely close, answer "tie".
- Output JSON only. No markdown, no commentary, no percentages, no pass probability.

## Output
{ "winner": "a" | "b" | "tie", "confidence": "high" | "medium" | "low", "reason": "1-2 sentence FIT-only justification" }

## JOB A
{{JOB_A}}

## JOB B
{{JOB_B}}

Return ONLY the JSON object.
