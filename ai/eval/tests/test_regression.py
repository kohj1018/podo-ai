"""T-014 불변식 회귀 테스트 — AC-1·AC-2·AC-3 (SPEC §10-1)."""

from __future__ import annotations

import ast
from pathlib import Path

from eval.regression import (
    FIXTURE_NAMESPACE,
    all_pass,
    check_invariants,
    failed,
    load_fixture,
    make_fixture_cache,
)
from worker.cache import CacheAdapter

# ---------------------------------------------------------------------------
# AC-1: 고정 합성 픽스처에서 불변식 10종 모두 통과
# ---------------------------------------------------------------------------


def test_AC_1_ten_invariants_pass() -> None:
    """AC-1: 고정 픽스처 산출물 → check_invariants → 불변식 10종 모두 통과."""
    fx = load_fixture()
    results = check_invariants(fx.ranking, fx.tables, fx.pairwise, fx.resume)

    # SPEC §10-1: 정확히 10종
    assert len(results) == 10, f"불변식 10종이어야 함: {len(results)}"
    assert all_pass(results), f"실패 불변식: {[r.name for r in failed(results)]}"


# ---------------------------------------------------------------------------
# AC-2: fixture 네임스페이스 캐시 격리
# ---------------------------------------------------------------------------


def test_AC_2_fixture_cache_isolation() -> None:
    """AC-2: fixture 네임스페이스 캐시는 일반 --refresh-cache에 영향받지 않는다."""
    golden = make_fixture_cache()
    assert golden.namespace == FIXTURE_NAMESPACE

    key = "golden_invariant_key"
    golden.put(key, {"frontend_rank": 1})

    # 일반 실행이 default 네임스페이스를 --refresh-cache로 비워도
    general = CacheAdapter(namespace="default")
    general.put(key, {"stale": True})
    general.refresh(key)
    assert general.get(key) is None, "일반 캐시는 refresh로 비워져야 함"

    # 회귀 골든은 격리 네임스페이스라 그대로 보존돼야 함
    assert golden.get(key) == {"frontend_rank": 1}, "fixture 골든이 흔들림"
    assert golden.namespace != general.namespace


# ---------------------------------------------------------------------------
# AC-3: mismatch 가드 위반 검출 (false negative 방지)
# ---------------------------------------------------------------------------


def test_AC_3_guard_violation_detected() -> None:
    """AC-3: mismatch 역할이 non-mismatch 위로 온 오염 산출물 → 가드 불변식 실패 검출."""
    fx = load_fixture()

    # 오염: marketing(mismatch)을 #1로 올려 non-mismatch(frontend/android) 위에 둔다.
    polluted = []
    for item in fx.ranking:
        clone = dict(item)
        if clone["role_family"] == "marketing":
            clone["rank"] = 1
        elif clone["role_family"] == "frontend":
            clone["rank"] = 2
        elif clone["role_family"] == "android":
            clone["rank"] = 3
        polluted.append(clone)

    results = check_invariants(polluted, fx.tables, fx.pairwise, fx.resume)

    guard = next(r for r in results if r.name == "mismatch_priority_guard")
    assert guard.passed is False, (
        "가드 불변식이 오염을 검출해야 함(false negative 방지)"
    )
    assert not all_pass(results)


# ---------------------------------------------------------------------------
# AC-2 (T-031): eval 경계 — worker public-only 의존 (ADR-103)
# ---------------------------------------------------------------------------


def test_AC_2_eval_uses_public_grounding() -> None:
    """T-031 AC-2: eval이 worker private(_) 심볼을 import하지 않고 worker.grounding 공개 API만 의존한다 (per ADR-103)."""
    import eval.regression as _reg
    from worker.grounding import build_haystack, is_extractive

    # 공개 grounding API가 존재·호출 가능해야 함
    assert callable(build_haystack) and callable(is_extractive)

    # eval 소스 패키지 전체를 AST 스캔 — worker private(_) import 0건 (AC-2 grep 계약)
    reg_file = _reg.__file__
    assert reg_file is not None
    eval_src = Path(reg_file).parent
    offenders: list[str] = []
    for py in eval_src.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "worker"
            ):
                for alias in node.names:
                    if alias.name.startswith("_"):
                        offenders.append(f"{py.name}: {node.module}.{alias.name}")
    assert not offenders, f"eval이 worker private 심볼 import: {offenders}"
