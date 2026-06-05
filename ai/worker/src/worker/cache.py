"""worker/cache.py — 결정론 캐시 키 + 인메모리 어댑터.

키 구성: sha256(model + system + user + schema_version) (SPEC §8-2).
시간·랜덤·환경 값 혼입 금지 (ARCH §3-1 결정론 경계 규칙).

저장소: 현재 인메모리(MVP/테스트용). DB 인터페이스는 동일하게 유지해
Postgres JSONB 어댑터로 교체 가능(ARCH §7-3 — 인터페이스 고정, 저장만 교체).
"""

import hashlib
from typing import Any


def make_key(model: str, system: str, user: str, schema_version: str) -> str:
    """결정론 캐시 키 — sha256(model + system + user + schema_version).

    렌더링된 프롬프트(system + user)와 모델 ID, 스키마 버전으로 구성한다.
    SPEC §8-2: 키에 시간·랜덤·환경 값 혼입 금지.
    """
    raw = model + system + user + schema_version
    return hashlib.sha256(raw.encode()).hexdigest()


class CacheAdapter:
    """캐시 저장 어댑터 — 인터페이스 고정, 구현은 인메모리(MVP).

    get(key) → dict | None
    put(key, value) → None
    refresh(key) → None  # 해당 키를 캐시에서 제거해 재계산 강제 (SPEC §8-2 REFRESH)

    Postgres JSONB 어댑터 교체 시 이 인터페이스를 구현하면 된다.
    """

    def __init__(self, namespace: str = "default") -> None:
        # namespace 격리 — eval/fixture 캐시가 일반 실행 캐시와 섞이지 않게 (SPEC §8-2)
        self._store: dict[str, Any] = {}
        self.namespace = namespace

    def _ns_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> Any | None:
        return self._store.get(self._ns_key(key))

    def put(self, key: str, value: Any) -> None:
        self._store[self._ns_key(key)] = value

    def refresh(self, key: str) -> None:
        """SPEC §8-2 --refresh-cache 동등: 해당 키 제거 → 다음 get은 miss."""
        self._store.pop(self._ns_key(key), None)
