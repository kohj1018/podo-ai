"""T-040 PII Safety Pass — milestone §5 졸업 게이트.

알려진 PII fixture를 마스킹→채점한 뒤 전 표면 6곳에 raw PII 0건임을 literal scan으로 검증한다:
  1. resumes.content (DB)            2. ranking_runs.result (JSONB 전문)
  3. recommendations (scalar)        4. 애플리케이션 로그(캡처)
  5. .cache/llm (runtime)            6. 커밋 웜캐시 ai/worker/fixtures/llm_cache

마스킹 통제(resumes.content)는 ADR-105 정합 known-value 오라클로 생성(마스커 *패턴* 정확성은
T-036 단위테스트, 실 NestJS 마스커 end-to-end는 stabilize E2E가 실증). 본 게이트의 핵심은
*하류 표면*(특히 ranking_runs.result — F-014 §7 주 누출 표면)이 채점 후에도 raw PII 0임을 보장.

DATABASE_URL 없으면 skip. 채점은 fake call_fn(무키, M2 패턴). 트랜잭션 rollback 멱등.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable

import psycopg
import pytest

from core import db
from worker.__main__ import run

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pii_resume.txt"

# fixture에 심은 알려진 raw PII 값 — 6표면 어디에도 나타나면 안 된다(literal scan 대상).
PII_VALUES = [
    "홍길동",
    "hong@example.com",
    "010-1234-5678",
    "900101-1234567",
    "hong-blog.tistory.com",
]

# 채점 extractive 검증 통과용 — 마스킹본에 verbatim 보존되는 경력 인용(PII 아님).
_QUOTE = "React 18 프로젝트에서 3년간 프론트엔드 개발"


def _mask_known(raw: str) -> str:
    """알려진 PII 값을 ADR-105 플레이스홀더로 치환(테스트 오라클 — 고정 fixture 전용)."""
    masked = raw
    for value, placeholder in (
        ("홍길동", "[MASKED_NAME]"),
        ("hong@example.com", "[MASKED_EMAIL]"),
        ("010-1234-5678", "[MASKED_PHONE]"),
        ("900101-1234567", "[MASKED_RRN]"),
        ("https://hong-blog.tistory.com/about", "[MASKED_URL]"),
    ):
        masked = masked.replace(value, placeholder)
    return masked


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    c = db.connect()
    try:
        yield c
        c.rollback()
    finally:
        c.close()


def _seed_jobs(cur: psycopg.Cursor[tuple[Any, ...]]) -> list[int]:
    rows = [
        ("toss", "Toss", "Frontend Engineer", "프론트엔드 채용 공고"),
        ("kakao", "Kakao", "Backend Engineer", "백엔드 채용 공고"),
    ]
    ids: list[int] = []
    for src, company, title, raw in rows:
        cur.execute(
            "INSERT INTO job_postings (source, company, title, url, raw_text) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (src, company, title, f"https://example.test/{title}", raw),
        )
        r = cur.fetchone()
        assert r is not None
        ids.append(int(r[0]))
    return ids


def _structured_fake() -> Callable[..., Any]:
    evidence_resp = {
        "evidence": [
            {
                "evidence_id": "E1",
                "title": "Experience",
                "source_section": "Experience",
                "exact_quote": _QUOTE,
                "normalized_summary": "React 3년",
            }
        ]
    }
    req = {
        "requirement_id": "R1",
        "requirement_text": "React 개발 경험",
        "requirement_type": "required",
        "requirement_nature": "technical",
        "prerequisite_status": "prerequisite",
    }
    match_resp = {
        "matches": [
            {
                "requirement_id": "R1",
                "requirement_type": "required",
                "matched_evidence_ids": ["E1"],
                "match_level": "direct",
                "confidence": "high",
                "explanation": "React 직접 매칭",
                "risk_note": "",
            }
        ]
    }

    def fn(
        system: str,
        user: str,
        validate: Callable[[dict[str, Any]], dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        cache_label: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        role_family = "frontend" if "Frontend" in user else "backend"
        jd_resp = {
            "requirements": [req],
            "preferred_requirements": [],
            "role_family": role_family,
        }
        for resp in (evidence_resp, jd_resp, match_resp, {"verified": []}):
            try:
                return validate(resp)
            except Exception:
                continue
        raise AssertionError("fake에 매칭되는 응답 없음")

    return fn


def _listwise_fake(job_ids: list[int]) -> Callable[..., str]:
    ranking = [{"job_id": str(j), "reason": "r"} for j in job_ids]

    def _call(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"ranking": ranking, "uncertainty_notes": ""})

    return _call


def _pairwise_fake() -> Callable[..., str]:
    def _call(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"winner": "a", "confidence": "high", "reason": "t"})

    return _call


def _scan_db_surfaces(
    conn: psycopg.Connection[tuple[Any, ...]], run_id: int, resume_id: int
) -> dict[str, str]:
    """DB 표면(resumes.content / ranking_runs.result / recommendations)을 텍스트로 회수."""
    out: dict[str, str] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT content FROM resumes WHERE id = %s", (resume_id,))
        row = cur.fetchone()
        out["resumes.content"] = str(row[0]) if row else ""
        cur.execute("SELECT result::text FROM ranking_runs WHERE id = %s", (run_id,))
        row = cur.fetchone()
        out["ranking_runs.result"] = str(row[0]) if row else ""
        cur.execute(
            "SELECT coalesce(status, '') || ' ' || coalesce(domain_alignment, '') "
            "FROM recommendations WHERE run_id = %s",
            (run_id,),
        )
        out["recommendations"] = " ".join(str(r[0]) for r in cur.fetchall())
    return out


def _scan_cache_dir(path: Path) -> str:
    """캐시 디렉토리 내 모든 .json 내용을 이어붙여 반환(없으면 빈 문자열)."""
    if not path.is_dir():
        return ""
    parts: list[str] = []
    for f in path.glob("*.json"):
        parts.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def test_AC_1_all_surfaces_literal_scan_zero(
    conn: psycopg.Connection[tuple[Any, ...]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """알려진 PII fixture → 마스킹→채점 후 6표면 모두 raw PII 0건."""
    raw = _FIXTURE.read_text(encoding="utf-8")

    # fixture sanity: 알려진 PII가 raw에 실재 → scan이 유의미(부재 문자열 스캔 아님)
    for value in PII_VALUES:
        assert value in raw, f"fixture에 PII {value!r} 부재 — scan 무의미"

    masked = _mask_known(raw)

    # 마스킹 통제: 마스킹본에 raw PII 0 (resumes.content에 흐르기 전 보장)
    for value in PII_VALUES:
        assert value not in masked, f"마스킹 누락: {value!r}"

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO resumes (content, masked, source, upload_format) "
            "VALUES (%s, true, 'upload', 'txt') RETURNING id",
            (masked,),
        )
        rrow = cur.fetchone()
        assert rrow is not None
        rid = int(rrow[0])
        job_ids = _seed_jobs(cur)

    # 채점(무키 fake) — ranking_runs.result/recommendations/로그 표면을 채운다.
    run_id = run(
        conn,
        resume_id=rid,
        structured_call_fn=_structured_fake(),
        listwise_call_fn=_listwise_fake(job_ids),
        pairwise_call_fn=_pairwise_fake(),
    )
    captured = capsys.readouterr()
    app_log = captured.out + captured.err

    # 6표면 수집
    surfaces = _scan_db_surfaces(conn, run_id, rid)
    surfaces["app_log"] = app_log
    surfaces[".cache/llm"] = _scan_cache_dir(_ROOT / ".cache" / "llm")
    surfaces["warm_cache"] = _scan_cache_dir(
        _ROOT / "ai" / "worker" / "fixtures" / "llm_cache"
    )

    # 전 표면 literal scan = 0
    for surface_name, text in surfaces.items():
        for value in PII_VALUES:
            assert value not in text, (
                f"raw PII {value!r}가 {surface_name} 표면에 누출됨 (PII Safety Pass 실패)"
            )
