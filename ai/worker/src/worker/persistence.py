"""worker/persistence.py — worker DB 영속 어댑터 (T-022, ARCH §3-2 규칙1·3).

worker는 자기 소유 테이블(ranking_runs·recommendations)에만 write한다(규칙1).
job_postings·resumes는 read. result는 build_report(SPEC §12) 산출을 verbatim JSONB로
저장한다(파싱·변형 금지, 규칙3). GS-1(결정론)은 DB 경로를 통과해도 보존된다 —
동일 입력 → 동일 result·recommendations(복합키 upsert + held 정렬).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import psycopg

from core.models import Resume
from worker import config
from worker.report import build_report

# M2 단일 스코어링/랭킹 모드 + 캐시 키 버전 (ranking_runs 복합키 구성요소).
SCORING_MODE = "pairwise_bt"
DEFAULT_RANKING_MODE = "domain_fit_bt"
CACHE_KEY_VERSION = "v1"

_INSERT_REC = (
    "INSERT INTO recommendations "
    "(run_id, job_posting_id, rank_position, fit_level, domain_alignment, status) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)


def _job_set_hash(jobs: list[dict[str, Any]]) -> str:
    """공고 집합의 결정적 해시 — 정렬된 job_id로 sha256 (SPEC §8 키 결정성)."""
    h = hashlib.sha256()
    for jid in sorted(str(j["job_id"]) for j in jobs):
        h.update(jid.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def load_jobs(conn: psycopg.Connection[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """job_postings를 run_scoring 입력 형식으로 읽는다(job_id = DB id 문자열)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, source, company, title, url, raw_text "
            "FROM job_postings ORDER BY id"
        )
        rows = cur.fetchall()
    return [
        {
            "job_id": str(r[0]),
            "source": r[1],
            "company": r[2],
            "title": r[3],
            "url": r[4],
            "raw_text": r[5],
        }
        for r in rows
    ]


def load_resume(conn: psycopg.Connection[tuple[Any, ...]], resume_id: int) -> Resume:
    """DB 마스킹 이력서(resumes.content)를 run_scoring 입력 Resume로 읽는다.

    content는 이미 마스킹본(직접 식별자 제거 — T-036). 도메인은 M3 기본값
    (업로드 이력서 자동 도메인 분류는 비범위 — T-037 §8 / seed 기본과 동일).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT content FROM resumes WHERE id = %s", (resume_id,))
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"resume_id={resume_id} 없음 (resumes에 미존재)")
    # T-066: 하드코딩 제거 — domains는 빈 list 반환.
    # 도메인 분류는 pipeline.run_scoring에서 extract_evidence 직후 수행된다.
    return Resume(raw_text=str(row[0]))


def persist_run(
    conn: psycopg.Connection[tuple[Any, ...]],
    resume_id: int,
    jobs: list[dict[str, Any]],
    result: dict[str, Any],
    *,
    ranking_mode: str = DEFAULT_RANKING_MODE,
) -> int:
    """run_scoring 산출을 ranking_runs(JSONB) + recommendations에 영속, run_id 반환.

    복합키 upsert(재실행 시 1행). recommendations = scored(ranking 순서) + held(pending,
    fit_level NULL, scored 뒤). 커밋은 호출자가 관리(conn).
    """
    # T-066: 분류 결과(내부 키)를 build_report 전에 pop — 저장 result(§12 계약) 미오염.
    resume_domains = result.pop("_resume_domains", None)
    report = build_report(result)  # SPEC §12 JSONB 계약 — verbatim 저장
    result_json = json.dumps(report, ensure_ascii=False)
    job_set_hash = _job_set_hash(jobs)

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ranking_runs "
            "(resume_id, job_set_hash, model, prompt_version, scoring_mode, "
            "ranking_mode, cache_key_version, result) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb) "
            "ON CONFLICT (resume_id, job_set_hash, model, prompt_version, "
            "scoring_mode, ranking_mode, cache_key_version) "
            "DO UPDATE SET result = EXCLUDED.result "
            "RETURNING id",
            (
                resume_id,
                job_set_hash,
                config.OPENAI_MODEL,
                config.PROMPT_VERSION,
                SCORING_MODE,
                ranking_mode,
                CACHE_KEY_VERSION,
                result_json,
            ),
        )
        row = cur.fetchone()
        assert row is not None
        run_id = int(row[0])

        # 재upsert 시 중복 방지 — 기존 projection 삭제 후 재생성(결정적 재현)
        cur.execute("DELETE FROM recommendations WHERE run_id = %s", (run_id,))

        ranking = report["final_ranking"]["ranking"]
        for i, fr in enumerate(ranking):
            cur.execute(
                _INSERT_REC,
                (
                    run_id,
                    int(fr["job_id"]),
                    i,
                    fr["fit_level"],
                    fr.get("domain_alignment"),
                    "scored",
                ),
            )
        # held — 보류 공고(LLM miss). 결정적 순서(정렬) + fit_level NULL + scored 뒤.
        held_ids = sorted(report["pending_job_ids"], key=lambda j: int(j))
        for k, jid in enumerate(held_ids):
            cur.execute(
                _INSERT_REC,
                (run_id, int(jid), len(ranking) + k, None, None, "held"),
            )

    # T-066: 이력서 도메인 분류 결과 영속(worker 단일 writer — resume_domains).
    if resume_domains is not None:
        _upsert_resume_domains(conn, resume_id, resume_domains)
    return run_id


def _upsert_resume_domains(
    conn: psycopg.Connection[tuple[Any, ...]],
    resume_id: int,
    domains: dict[str, Any],
) -> None:
    """도메인 분류 결과를 resume_domains에 멱등 upsert(worker 단일 writer, §3-2)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO resume_domains "
            "(resume_id, primary_domains, secondary_domains, confidence, "
            "classifier_version) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (resume_id) DO UPDATE SET "
            "primary_domains = EXCLUDED.primary_domains, "
            "secondary_domains = EXCLUDED.secondary_domains, "
            "confidence = EXCLUDED.confidence, "
            "classifier_version = EXCLUDED.classifier_version",
            (
                resume_id,
                list(domains.get("primary_domains", [])),
                list(domains.get("secondary_domains", [])),
                str(domains.get("confidence", "low")),
                str(domains.get("classifier_version", "")),
            ),
        )
