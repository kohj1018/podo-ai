"""core.db — Python↔Postgres raw SQL 접근(worker/crawler/eval 공유, ARCH §3-2 규칙2).

시스템 경계(외부 DB)에서만 검증한다 — 내부 호출엔 방어를 두지 않는다(ARCH §2).
ORM 없이 raw SQL만(§3-2: DDL은 Prisma 소유, DML은 각 런타임).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

import psycopg


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 미설정 — .env 또는 환경변수 필요")
    return url


def connect() -> psycopg.Connection[tuple[Any, ...]]:
    """DATABASE_URL로 Postgres 연결을 연다(트랜잭션은 호출자가 with/close로 관리)."""
    return psycopg.connect(_database_url())


def fetch_all(sql: str, params: Sequence[Any] | None = None) -> list[tuple[Any, ...]]:
    """raw SELECT — 전체 행을 튜플 리스트로 반환(자체 연결 open→commit→close)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(sql: str, params: Sequence[Any] | None = None) -> None:
    """raw INSERT/UPDATE/DDL — 자체 연결에서 실행하고 커밋한다(결과 미반환)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
