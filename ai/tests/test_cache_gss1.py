"""T-088 AC-2 — GS-1 멀티인스턴스 회귀 (PostgresCacheAdapter).

동일 입력(동일 cache_key) → worker 인스턴스 2개가 동일 결과를 반환한다(공유 Postgres 캐시).
디스크 캐시(.cache/llm)는 단일프로세스라 인스턴스 간 공유가 불가능했던 재현성을, Postgres
JSONB 어댑터가 보존한다(F-027 FAC-1). 캐시 키 포맷은 디스크 어댑터와 동일(make_key).

DATABASE_URL 게이트(실 Postgres + llm_cache 마이그레이션 적용 전제) — 로컬 무DB는 skip,
CI(schema-contract DB)가 실행.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from worker.cache import make_key
from worker.cache_postgres import PostgresCacheAdapter
from worker.config import SCHEMA_VERSION

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (llm_cache 테이블)",
)


@pytest.fixture
def cache_key() -> Iterator[str]:
    """결정론 키 1개를 발급하고, 테스트 후 caches에서 제거(실행 간 격리)."""
    key = make_key("gpt-5.4-mini", "GS1-system", "GS1-user", SCHEMA_VERSION)
    yield key
    PostgresCacheAdapter(os.environ["DATABASE_URL"]).refresh(key)


def test_AC_2_same_key_same_result_multiinstance(cache_key: str) -> None:
    """인스턴스 A가 put → 별도 인스턴스 B(별 연결)가 동일 키로 get → 동일 결과(GS-1)."""
    db_url = os.environ["DATABASE_URL"]
    value = {"fit": 4, "label": "적합", "evidence": ["React", "TypeScript"]}

    instance_a = PostgresCacheAdapter(db_url)
    instance_b = PostgresCacheAdapter(db_url)

    instance_a.put(cache_key, value)
    assert instance_b.get(cache_key) == value, (
        "멀티인스턴스 공유 캐시 결과 불일치(GS-1 위반)"
    )


def test_AC_2_refresh_invalidates(cache_key: str) -> None:
    """refresh 후 get은 miss(None) — 재계산 강제(SPEC §8-2 REFRESH)."""
    adapter = PostgresCacheAdapter(os.environ["DATABASE_URL"])
    adapter.put(cache_key, {"x": 1})
    assert adapter.get(cache_key) == {"x": 1}
    adapter.refresh(cache_key)
    assert adapter.get(cache_key) is None
