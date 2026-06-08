"""T-088 AC-1 — PostgresCacheAdapter 단위 테스트.

DB 없이 psycopg.connect를 mock으로 대체해 어댑터 get/put 로직·graceful fallback·
어댑터 선택 분기를 검증한다(항상 실행). 실 Postgres 라운드트립은 test_cache_gss1.py가
DATABASE_URL 게이트로 검증.

mock은 psycopg3 동작을 모사한다: put은 `Json(value)`(객체 .obj=원 dict)로 들어오고,
get은 JSONB를 파싱된 dict로 돌려받는다.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_conn(stored: dict[str, Any]) -> MagicMock:
    """psycopg.connect()가 반환하는 context-manager mock. stored로 INSERT↔SELECT 상태 공유."""
    mock_cur = MagicMock()

    def _execute(sql: str, params: tuple[Any, ...] | None = None) -> None:
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            key = params[0] if params else None
            mock_cur.fetchone.return_value = (stored[key],) if key in stored else None
        elif sql_upper.startswith("INSERT"):
            if params:
                val = params[1]
                # psycopg Json(value).obj = 원 dict (실 JSONB read는 파싱된 dict 반환)
                stored[params[0]] = getattr(val, "obj", val)
        elif sql_upper.startswith("DELETE"):
            if params:
                stored.pop(params[0], None)

    mock_cur.execute.side_effect = _execute
    mock_cur.__enter__ = lambda s: s
    mock_cur.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_conn.commit = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn


def test_AC_1_cache_hit_after_put() -> None:
    """AC-1: 동일 key로 put 후 get → 저장 값 반환(캐시 히트)."""
    from worker.cache_postgres import PostgresCacheAdapter

    stored: dict[str, Any] = {}
    with patch(
        "worker.cache_postgres.psycopg.connect", return_value=_make_mock_conn(stored)
    ):
        adapter = PostgresCacheAdapter("postgresql://test/test")
        adapter.put("key-abc", {"score": 90})
        result = adapter.get("key-abc")

    assert result == {"score": 90}, f"캐시 히트 실패: {result}"


def test_AC_1_cache_miss_returns_none() -> None:
    """AC-1: 미존재 key → None(캐시 미스)."""
    from worker.cache_postgres import PostgresCacheAdapter

    with patch(
        "worker.cache_postgres.psycopg.connect", return_value=_make_mock_conn({})
    ):
        adapter = PostgresCacheAdapter("postgresql://test/test")
        assert adapter.get("key-nonexistent") is None


def test_AC_1_db_connection_failure_returns_none_graceful() -> None:
    """AC-1: DB 연결 실패 시 get→None(graceful fallback — 재계산으로 정확도 유지)."""
    from worker.cache_postgres import PostgresCacheAdapter

    with patch(
        "worker.cache_postgres.psycopg.connect",
        side_effect=Exception("connection refused"),
    ):
        adapter = PostgresCacheAdapter("postgresql://bad/url")
        assert adapter.get("any-key") is None


def test_AC_1_db_put_failure_is_silent() -> None:
    """AC-1: DB 쓰기 실패는 예외 미전파(캐시 실패는 치명적 아님)."""
    from worker.cache_postgres import PostgresCacheAdapter

    with patch(
        "worker.cache_postgres.psycopg.connect",
        side_effect=Exception("connection refused"),
    ):
        adapter = PostgresCacheAdapter("postgresql://bad/url")
        adapter.put("any-key", {"value": 1})  # raise 없이 통과


def test_AC_1_different_keys_different_results() -> None:
    """AC-1: 다른 키는 다른 값."""
    from worker.cache_postgres import PostgresCacheAdapter

    stored: dict[str, Any] = {}
    with patch(
        "worker.cache_postgres.psycopg.connect", return_value=_make_mock_conn(stored)
    ):
        adapter = PostgresCacheAdapter("postgresql://test/test")
        adapter.put("key-A", {"score": 10})
        adapter.put("key-B", {"score": 20})
        assert adapter.get("key-A") == {"score": 10}
        assert adapter.get("key-B") == {"score": 20}


def test_AC_1_use_postgres_cache_env_selects_postgres_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-1: USE_POSTGRES_CACHE=1 → PostgresCacheAdapter 선택."""
    monkeypatch.setenv("USE_POSTGRES_CACHE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")

    from worker.cache import get_cache_adapter
    from worker.cache_postgres import PostgresCacheAdapter

    adapter = get_cache_adapter()
    assert isinstance(adapter, PostgresCacheAdapter)


def test_AC_1_no_env_selects_default_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-1: USE_POSTGRES_CACHE 미설정 → 기본 인메모리 CacheAdapter."""
    monkeypatch.delenv("USE_POSTGRES_CACHE", raising=False)

    from worker.cache import CacheAdapter, get_cache_adapter
    from worker.cache_postgres import PostgresCacheAdapter

    adapter = get_cache_adapter()
    assert isinstance(adapter, CacheAdapter)
    assert not isinstance(adapter, PostgresCacheAdapter)
