"""T-006: matching.py TDD 테스트.

AC-1: 모든 요구당 정확히 1행 + evidence_quotes verbatim 복사.
AC-2: over-claim(존재하지 않는 id) + rematch 실패 → invalid_match=True, match_level=missing.
AC-3: missing인 critical same-category 그룹 행 → _needs_rematch가 True.
"""

from unittest.mock import patch

from core.models import (
    EvidenceItem,
    JobPosting,
    MatchingTable,
    Requirement,
)
from worker.matching import _needs_rematch, build_matching_table

# ---------------------------------------------------------------------------
# 공통 픽스처
# ---------------------------------------------------------------------------


def _make_evidence(eid: str, quote: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        title=f"title_{eid}",
        source_section="Experience",
        exact_quote=quote,
        normalized_summary=f"summary_{eid}",
    )


def _make_req(
    rid: str,
    req_type: str = "required",
    req_nature: str = "technical",
    req_category: str = "other",
    alternatives: list[str] | None = None,
) -> Requirement:
    return Requirement(
        requirement_id=rid,
        requirement_text=f"requirement text {rid}",
        requirement_type=req_type,
        requirement_nature=req_nature,
        requirement_category=req_category,
        alternatives=alternatives or [],
    )


def _make_job(requirements: list[Requirement]) -> JobPosting:
    return JobPosting(
        job_id="job-001",
        company="TestCo",
        title="Software Engineer",
        url="https://example.com",
        requirements=requirements,
    )


# ---------------------------------------------------------------------------
# AC-1: 모든 요구당 정확히 1행, evidence_quotes는 evidence.exact_quote와 글자 단위 일치
# ---------------------------------------------------------------------------


class TestAC1OneRowPerReqExtractivQuotes:
    """AC-1 [Given] LLM이 일부 요구를 누락하고 일부에 evidence_id를 준 응답
    [When] build_matching_table
    [Then] 모든 요구당 정확히 1행이 존재하고, 각 행의 evidence_quotes는 선택된 evidence의
           exact_quote와 글자 단위로 일치한다(LLM 작성 텍스트 아님).
    """

    def test_AC_1_one_row_per_req_extractive_quotes(self):
        evidences = [
            _make_evidence("E1", "React 18 프로젝트에서 3년 경력"),
            _make_evidence("E2", "TypeScript strict 모드 사용"),
        ]
        reqs = [
            _make_req("R1", req_type="critical"),
            _make_req("R2", req_type="required"),
            _make_req("R3", req_type="preferred"),  # LLM이 누락할 요구
        ]
        job = _make_job(reqs)

        # LLM이 R1만 응답하고 R2·R3은 누락 + R1에 E1 선택
        llm_response = {
            "matches": [
                {
                    "requirement_id": "R1",
                    "requirement_type": "critical",
                    "matched_evidence_ids": ["E1"],
                    "match_level": "direct",
                    "confidence": "high",
                    "explanation": "React 경험 직접 매칭",
                    "risk_note": "",
                },
                # R2는 존재하는 id E2 제공
                {
                    "requirement_id": "R2",
                    "requirement_type": "required",
                    "matched_evidence_ids": ["E2"],
                    "match_level": "direct",
                    "confidence": "medium",
                    "explanation": "TypeScript 경험",
                    "risk_note": "",
                },
                # R3 누락 — backfill 대상
            ]
        }

        def fake_llm(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kwargs,
        ):
            return validate(llm_response)

        with patch("worker.matching.call_structured", side_effect=fake_llm):
            table = build_matching_table(job, evidences)

        assert isinstance(table, MatchingTable)

        # 모든 요구당 정확히 1행
        assert len(table.rows) == 3, f"expected 3 rows, got {len(table.rows)}"

        req_ids = {row.requirement_id for row in table.rows}
        assert req_ids == {"R1", "R2", "R3"}, f"missing requirement rows: {req_ids}"

        # R1 행: evidence_quotes가 E1.exact_quote와 글자 단위 일치
        r1_row = next(r for r in table.rows if r.requirement_id == "R1")
        assert r1_row.evidence_quotes == [evidences[0].exact_quote], (
            f"R1 quote mismatch: {r1_row.evidence_quotes!r}"
        )
        assert r1_row.matched_evidence_ids == ["E1"]

        # R2 행: E2 quote
        r2_row = next(r for r in table.rows if r.requirement_id == "R2")
        assert r2_row.evidence_quotes == [evidences[1].exact_quote]

        # R3 행: backfill → missing/low, quotes empty
        r3_row = next(r for r in table.rows if r.requirement_id == "R3")
        assert r3_row.match_level == "missing"
        assert r3_row.confidence == "low"
        assert r3_row.evidence_quotes == []


# ---------------------------------------------------------------------------
# AC-2: over-claim (존재하지 않는 id) → resolve 후 rematch 실패 → invalid_match=True
# ---------------------------------------------------------------------------


class TestAC2OverclaimBecomesInvalid:
    """AC-2 [Given] match_level=direct인데 존재하지 않는 evidence_id만 준 행
    [When] resolve + rematch도 실패
    [Then] 해당 행은 match_level=missing·invalid_match=True로 표기되고 risk_note가 남는다.
    """

    def test_AC_2_overclaim_becomes_invalid(self):
        evidences = [
            _make_evidence("E1", "React 경험 텍스트"),
        ]
        reqs = [_make_req("R1", req_type="required")]
        job = _make_job(reqs)

        # LLM이 존재하지 않는 id "GHOST" 반환
        llm_response = {
            "matches": [
                {
                    "requirement_id": "R1",
                    "requirement_type": "required",
                    "matched_evidence_ids": ["GHOST"],
                    "match_level": "direct",
                    "confidence": "high",
                    "explanation": "매칭 주장",
                    "risk_note": "",
                },
            ]
        }

        # rematch도 "missing" 반환
        rematch_response = {
            "matched_evidence_ids": [],
            "match_level": "missing",
            "confidence": "low",
            "explanation": "no evidence found",
        }

        call_count = {"n": 0}

        def fake_llm(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kwargs,
        ):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return validate(llm_response)
            return validate(rematch_response)

        with patch("worker.matching.call_structured", side_effect=fake_llm):
            table = build_matching_table(job, evidences)

        r1_row = next(r for r in table.rows if r.requirement_id == "R1")
        assert r1_row.invalid_match is True, "over-claim 행은 invalid_match=True여야 함"
        assert r1_row.match_level == "missing", (
            f"match_level should be missing, got {r1_row.match_level!r}"
        )
        assert r1_row.risk_note, "risk_note가 비어 있음 — 사유가 기록되어야 함"


# ---------------------------------------------------------------------------
# AC-3: missing critical same-category 그룹 → _needs_rematch가 True
# ---------------------------------------------------------------------------


class TestAC3NeedsRematchGroup:
    """AC-3 [Given] missing으로 온 critical same-category 그룹 행
    [When] _needs_rematch
    [Then] rematch 대상으로 판정된다(false-negative 재확인).
    """

    def test_AC_3_needs_rematch_group(self):
        from core.models import MatchRow

        # critical + GROUP_CATEGORIES category + missing → 재시도 대상
        row = MatchRow(
            requirement_id="R1",
            requirement_text="React 또는 Vue",
            requirement_type="critical",
            requirement_nature="technical",
            requirement_category="framework",
            prerequisite_status="prerequisite",
            matched_evidence_ids=[],
            evidence_quotes=[],
            evidence_source_sections=[],
            match_level="missing",
            confidence="low",
        )
        assert _needs_rematch(row) is True

    def test_AC_3_needs_rematch_required_language_group(self):
        """required + language 카테고리 + missing도 재시도 대상."""
        from core.models import MatchRow

        row = MatchRow(
            requirement_id="R2",
            requirement_text="TypeScript 또는 JavaScript",
            requirement_type="required",
            requirement_nature="technical",
            requirement_category="language",
            prerequisite_status="prerequisite",
            matched_evidence_ids=[],
            evidence_quotes=[],
            evidence_source_sections=[],
            match_level="missing",
            confidence="low",
        )
        assert _needs_rematch(row) is True

    def test_AC_3_preferred_missing_not_rematched(self):
        """preferred + missing은 재시도 대상이 아님."""
        from core.models import MatchRow

        row = MatchRow(
            requirement_id="R3",
            requirement_text="GraphQL",
            requirement_type="preferred",
            requirement_nature="technical",
            requirement_category="framework",
            prerequisite_status="prerequisite",
            matched_evidence_ids=[],
            match_level="missing",
            confidence="low",
        )
        assert _needs_rematch(row) is False

    def test_AC_3_direct_match_not_rematched(self):
        """direct match인 행은 재시도 대상이 아님."""
        from core.models import MatchRow

        row = MatchRow(
            requirement_id="R4",
            requirement_text="React",
            requirement_type="critical",
            requirement_nature="technical",
            requirement_category="framework",
            prerequisite_status="prerequisite",
            matched_evidence_ids=["E1"],
            match_level="direct",
            confidence="high",
        )
        assert _needs_rematch(row) is False
