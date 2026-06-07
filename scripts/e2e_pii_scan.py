"""scripts/e2e_pii_scan.py — E2E 실 파이프라인 PII 표면 스캔 (QA-M3-006 종결).

T-040 PII Safety Pass는 *known-value 오라클*로 surface-1을 만들지만, 본 스캔은
**실 RegexResumeMasker(NestJS)** 가 업로드 시 만든 `resumes.content` 와 worker가
그 마스킹본으로 채점해 쓴 `ranking_runs.result`(F-014 §7 주 누출 표면)를 *실 DB에서*
읽어 fixture의 알려진 raw PII가 0건인지 검증한다 — milestone §5 #3·#7 "실 masker
end-to-end" 변을 닫는다(scripts/e2e.mjs phase 6에서 호출).

출력은 순수 ASCII — Windows cp949 콘솔의 인코딩 에러/깨짐을 회피한다.
호출: E2E_RESUME_ID=<id> DATABASE_URL=... uv run python scripts/e2e_pii_scan.py
"""

from __future__ import annotations

import os
import sys

from core.db import fetch_all

# pii_resume.txt(T-040 fixture)의 알려진 raw PII — 마스킹/채점 후 0건이어야.
# fixture 변경 시 함께 갱신한다(테스트 오라클 — T-040 fixture와 동일 값).
PII_LITERALS = [
    "홍길동",
    "hong@example.com",
    "010-1234-5678",
    "900101-1234567",
    "hong-blog.tistory.com",
]

_RESULT_SQL = """
    SELECT result::text FROM ranking_runs
    WHERE resume_id = %s ORDER BY id DESC LIMIT 1
"""


def main() -> int:
    resume_id = int(os.environ["E2E_RESUME_ID"])

    content_rows = fetch_all("SELECT content FROM resumes WHERE id = %s", (resume_id,))
    result_rows = fetch_all(_RESULT_SQL, (resume_id,))
    surfaces = {
        "resumes.content": content_rows[0][0] if content_rows else "",
        "ranking_runs.result": result_rows[0][0] if result_rows else "",
    }

    # 빈 표면을 무오류로 통과시키지 않는다 — 업로드/마스킹이 실제로 일어났는지 sanity.
    masked = surfaces["resumes.content"]
    if not masked:
        print(
            f"[pii-scan] FAIL: resumes.content(id={resume_id}) empty - upload missing"
        )
        return 1
    if "[MASKED_" not in masked:
        print(
            f"[pii-scan] FAIL: resumes.content(id={resume_id}) has no [MASKED_] token"
        )
        return 1

    leaks: list[str] = []
    for name, text in surfaces.items():
        for pii in PII_LITERALS:
            if pii in (text or ""):
                leaks.append(f"{name} <- {pii!r}")

    if leaks:
        print("[pii-scan] FAIL: raw PII found (real-masker end-to-end leak):")
        for leak in leaks:
            print(f"  - {leak}")
        return 1

    print(
        f"[pii-scan] OK: resumes.content + ranking_runs.result"
        f"(resume_id={resume_id}) - 0 raw PII across 5 fixture literals"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
