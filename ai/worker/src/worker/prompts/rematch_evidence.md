You are doing a focused second-pass match for ONE job requirement against a fixed candidate's resume evidence.

A previous pass selected no usable evidence for this requirement. Look again carefully.

## Rules
- **Choose `evidence_id`(s) ONLY from the evidence list below. DO NOT write, paraphrase, or copy any quote text.** The system fills quotes verbatim from the ids you select.
- Only use ids that appear in the list. Never invent an id.
- Select an id if its content genuinely supports this requirement, even partially (transferable/adjacent counts — set match_level accordingly).
- If, after looking carefully, no evidence supports it at all, return an empty list with match_level "missing".
- No percentages, no pass probability. Output JSON only.

## Requirement
- requirement_text: {{REQUIREMENT_TEXT}}
- requirement_type: {{REQUIREMENT_TYPE}}
- requirement_nature: {{REQUIREMENT_NATURE}}
- alternatives (any one is enough, if non-empty): {{ALTERNATIVES}}

## Candidate evidence items
{{EVIDENCE}}

## Output (JSON only)
{ "matched_evidence_ids": ["E#", ...], "match_level": "direct|adjacent|weak|missing", "confidence": "high|medium|low", "explanation": "1 sentence" }
