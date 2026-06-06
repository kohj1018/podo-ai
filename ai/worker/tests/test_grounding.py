"""T-031 grounding 공개 모듈 TDD 테스트.

AC-1: build_haystack·is_extractive가 worker.grounding 공개 심볼로 이전됐고,
      verify_matches 관련 기존 동작이 동일하게 유지된다.
AC-2: eval이 worker.grounding 공개 import만 사용하고 private import가 0건이다.
"""

from __future__ import annotations

from core.models import EvidenceItem


def _make_evidence(eid: str, quote: str, summary: str = "") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        title=f"title_{eid}",
        source_section="Experience",
        exact_quote=quote,
        normalized_summary=summary or f"summary of {quote[:20]}",
    )


# ---------------------------------------------------------------------------
# AC-1: 공개 모듈 심볼 존재 + 행동 동일
# ---------------------------------------------------------------------------


class TestAC1PublicGroundingBehaviorPreserved:
    """AC-1 [Given] 기존 grounding 동작 [When] worker.grounding 공개 모듈로 이전 후
    [Then] build_haystack·is_extractive가 공개 심볼로 존재하고 동작 동일하다.
    """

    def test_AC_1_public_grounding_behavior_preserved(self) -> None:
        """build_haystack·is_extractive가 worker.grounding에서 import 가능하다."""
        from worker.grounding import build_haystack, is_extractive  # noqa: F401

    def test_AC_1_build_haystack_includes_resume_text(self) -> None:
        """build_haystack은 이력서 텍스트를 정규화해 haystack에 포함한다."""
        from worker.grounding import build_haystack

        haystack = build_haystack("React 18 경력", [])
        assert "react 18 경력" in haystack

    def test_AC_1_build_haystack_includes_evidence_quote(self) -> None:
        """build_haystack은 evidence의 exact_quote를 정규화해 포함한다."""
        from worker.grounding import build_haystack

        evidence = [_make_evidence("E1", "TypeScript strict 모드")]
        haystack = build_haystack("이력서 텍스트", evidence)
        assert "typescript strict 모드" in haystack

    def test_AC_1_build_haystack_includes_evidence_summary(self) -> None:
        """build_haystack은 evidence의 normalized_summary를 포함한다."""
        from worker.grounding import build_haystack

        evidence = [_make_evidence("E1", "quote", summary="리액트 경험 요약")]
        haystack = build_haystack("이력서", evidence)
        assert "리액트 경험 요약" in haystack

    def test_AC_1_is_extractive_true_for_verbatim(self) -> None:
        """is_extractive는 verbatim 인용이 haystack에 있으면 True를 반환한다."""
        from worker.grounding import build_haystack, is_extractive

        evidence = [_make_evidence("E1", "React 18 프로젝트")]
        haystack = build_haystack("전체 이력서 React 18 프로젝트 내용", evidence)
        assert is_extractive("React 18 프로젝트", haystack) is True

    def test_AC_1_is_extractive_false_for_nonexistent(self) -> None:
        """is_extractive는 haystack에 없는 텍스트면 False를 반환한다."""
        from worker.grounding import is_extractive

        assert is_extractive("없는 텍스트", "이력서 내용") is False

    def test_AC_1_is_extractive_normalizes_whitespace(self) -> None:
        """is_extractive는 공백 정규화 후 검색한다 (대소문자, 공백 차이 허용)."""
        from worker.grounding import build_haystack, is_extractive

        haystack = build_haystack("React  18  경력", [])
        assert is_extractive("React 18 경력", haystack) is True

    def test_AC_1_private_build_haystack_removed_from_verify_matches(self) -> None:
        """_build_haystack private 정의가 verify_matches에서 제거됐다."""
        import inspect

        import worker.verify_matches as vm

        src = inspect.getsource(vm)
        assert "def _build_haystack" not in src, (
            "_build_haystack private 정의가 verify_matches.py에 남아 있음"
        )

    def test_AC_1_private_is_extractive_removed_from_verify_matches(self) -> None:
        """_is_extractive private 정의가 verify_matches에서 제거됐다."""
        import inspect

        import worker.verify_matches as vm

        src = inspect.getsource(vm)
        assert "def _is_extractive" not in src, (
            "_is_extractive private 정의가 verify_matches.py에 남아 있음"
        )
