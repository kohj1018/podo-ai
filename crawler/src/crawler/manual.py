"""T-012 manual — jobs_manual 폴백 파서.

스크래핑 실패 시 수동 JD(=== JOB === 블록)를 동일 raw 형식으로 변환.
SPEC §9-1 jobs_manual.md 동등 경로.
"""

from __future__ import annotations

import re

RawJob = dict[str, str]

_JOB_SEP = re.compile(r"===\s*JOB\s*===", re.IGNORECASE)
_FIELD_RE = re.compile(
    r"^(job_id|company|title|url)\s*:\s*(.+)$", re.MULTILINE | re.IGNORECASE
)


def parse_manual(text: str) -> list[RawJob]:
    """=== JOB === 구분자로 분리된 수동 JD 텍스트를 raw 공고 list로 변환.

    각 블록에서 job_id / company / title / url 필드를 파싱하고
    나머지 텍스트를 raw_text로 사용한다.
    필수 필드(job_id, company, title, url) 중 하나라도 없으면 해당 블록 스킵.
    """
    blocks = _JOB_SEP.split(text)
    results: list[RawJob] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        fields: dict[str, str] = {}
        for m in _FIELD_RE.finditer(block):
            fields[m.group(1).lower()] = m.group(2).strip()

        if not all(k in fields for k in ("job_id", "company", "title", "url")):
            continue

        # 필드 선언 줄을 제거한 나머지를 raw_text로
        raw_text = _FIELD_RE.sub("", block).strip()
        results.append(
            {
                "job_id": fields["job_id"],
                "company": fields["company"],
                "title": fields["title"],
                "url": fields["url"],
                "raw_text": raw_text,
            }
        )
    return results
