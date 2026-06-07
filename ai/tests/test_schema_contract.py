"""폴리글랏 schema-contract test (T-021 AC-2) — R6 schema drift 가드의 컴파일-타임 대체.

갓 마이그레이션한 DB(T-020)에 붙어 worker/crawler 의존 컬럼·타입 존재를 assert한다.
의존 컬럼이 누락(drop)되면 red — 폴리글랏 무음 drift를 차단(GS R6).
DATABASE_URL 없으면 skip(로컬 게이트) — CI(schema-contract.yml)가 주입.
"""

from __future__ import annotations

import os

import pytest

from core import db

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)


def _columns(table: str) -> dict[str, str]:
    rows = db.fetch_all(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return {str(r[0]): str(r[1]) for r in rows}


def test_AC_2_dependent_columns_present_else_fail() -> None:
    """worker/crawler 의존 컬럼·타입이 있으면 green, 누락 시 red(R6 drift 가드)."""
    # job_postings (crawler 의존)
    jp = _columns("job_postings")
    for col in (
        "source",
        "company",
        "title",
        "url",
        "raw_text",
        "role_family",
        "diff_status",
        "fetched_at",
    ):
        assert col in jp, f"job_postings.{col} 누락 (crawler 의존)"

    # ranking_runs (worker): result jsonb + 7컬럼 복합 unique
    rr = _columns("ranking_runs")
    assert rr.get("result") == "jsonb", (
        f"ranking_runs.result != jsonb: {rr.get('result')}"
    )
    for col in (
        "resume_id",
        "job_set_hash",
        "model",
        "prompt_version",
        "scoring_mode",
        "ranking_mode",
        "cache_key_version",
    ):
        assert col in rr, f"ranking_runs.{col} 누락 (캐시 키 구성요소)"
    uniq = db.fetch_all(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'ranking_runs' "
        "AND indexdef LIKE '%UNIQUE%' AND indexdef LIKE '%cache_key_version%'"
    )
    assert uniq, "ranking_runs 7컬럼 복합 unique 누락 (GS-1-through-DB 캐시 hit)"

    # recommendations (feed projection — cross-LLM P0)
    rec = _columns("recommendations")
    for col in (
        "run_id",
        "job_posting_id",
        "rank_position",
        "fit_level",
        "domain_alignment",
        "status",
    ):
        assert col in rec, f"recommendations.{col} 누락 (정렬 feed projection)"
    idx = db.fetch_all(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'recommendations' "
        "AND indexdef LIKE '%run_id%rank_position%'"
    )
    assert idx, "recommendations (run_id, rank_position) 인덱스 누락 (current-run 커서)"
    # held(M2-repair-6) 불변식: fit_level은 NULL 허용 — 가짜 점수 금지. R6 가드 확장(QA-M2-008).
    nullable = db.fetch_all(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'recommendations' AND column_name = 'fit_level'"
    )
    assert nullable and nullable[0][0] == "YES", (
        "recommendations.fit_level이 nullable 아님 — held NULL 영속 불변식 위반(M2-repair-6)"
    )
    # run당 공고 1행 불변식(QA-M2-002) — feed dedup/cursor 전제
    uniq_rec = db.fetch_all(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'recommendations' "
        "AND indexdef LIKE '%UNIQUE%' AND indexdef LIKE '%job_posting_id%'"
    )
    assert uniq_rec, "recommendations (run_id, job_posting_id) unique 누락 (QA-M2-002)"

    # crawl_runs (run별 컬럼)
    cr = _columns("crawl_runs")
    for col in ("channel", "run_at", "status", "new_count", "closed_count"):
        assert col in cr, f"crawl_runs.{col} 누락 (coverage 파생)"

    # resumes (M3 업로드 메타 — masked·source·upload_format 추가, T-035)
    rs = _columns("resumes")
    for col in ("content", "masked", "source", "upload_format"):
        assert col in rs, f"resumes.{col} 누락 (M3 업로드 메타)"
    assert rs.get("masked") == "boolean", (
        f"resumes.masked != boolean: {rs.get('masked')}"
    )


def test_AC_4_users_table_and_user_id_fk_exist() -> None:
    """T-042 AC-4 — users 테이블 + resumes.user_id FK 존재 검증(폴리글랏 drift 가드)."""
    # users 테이블 존재 + 최소 5필드 검증 (ADR-105 Amend1 계정 PII)
    us = _columns("users")
    for col in ("provider", "provider_account_id", "email", "display_name"):
        assert col in us, f"users.{col} 누락 (T-042 계정 필드)"

    # (provider, provider_account_id) 복합 unique — 동일 provider 계정 중복 차단
    uniq_users = db.fetch_all(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'users' "
        "AND indexdef LIKE '%UNIQUE%' AND indexdef LIKE '%provider_account_id%'"
    )
    assert uniq_users, "users (provider, provider_account_id) unique 누락 (T-042)"

    # resumes.user_id FK — users 테이블 참조
    rs = _columns("resumes")
    assert "user_id" in rs, "resumes.user_id 누락 (T-042 FK)"

    fk = db.fetch_all(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name = 'resumes' AND constraint_type = 'FOREIGN KEY'"
    )
    fk_names = [str(r[0]) for r in fk]
    # FK 이름에 'user' 포함 여부로 검증 (Prisma 생성 FK명 패턴)
    assert any("user" in n for n in fk_names), (
        f"resumes.user_id FK to users 누락 (T-042). found: {fk_names}"
    )
