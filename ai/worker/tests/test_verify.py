"""T-007: verify_matches.py TDD 테스트.

AC-1: 비추출 인용이 제거되고 근거 없는 행이 invalid_match=True·레벨 강등·confidence=low로 된다.
AC-2: verifier가 match_level을 올리려는 응답도 _apply_verifier는 레벨을 절대 올리지 않는다.
AC-3: 추출 가능한 verbatim 인용을 가진 정상 행은 extractive_ok=True·invalid 처리 안 됨.
"""

from core.models import (
    EvidenceItem,
    MatchingTable,
    MatchRow,
    Resume,
)

# ---------------------------------------------------------------------------
# 공통 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _make_evidence(eid: str, quote: str, summary: str = "") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        title=f"title_{eid}",
        source_section="Experience",
        exact_quote=quote,
        normalized_summary=summary or f"summary of {quote[:20]}",
    )


def _make_row(
    rid: str,
    match_level: str = "direct",
    confidence: str = "high",
    evidence_ids: list[str] | None = None,
    quotes: list[str] | None = None,
    invalid: bool = False,
) -> MatchRow:
    return MatchRow(
        requirement_id=rid,
        requirement_text=f"requirement {rid}",
        matched_evidence_ids=evidence_ids or [],
        evidence_quotes=quotes or [],
        match_level=match_level,
        confidence=confidence,
        invalid_match=invalid,
    )


def _make_table(rows: list[MatchRow]) -> MatchingTable:
    return MatchingTable(job_id="job-001", company="TestCo", title="SWE", rows=rows)


def _make_resume(raw_text: str, evidence: list[EvidenceItem] | None = None) -> Resume:
    return Resume(raw_text=raw_text, evidence=evidence or [])


# ---------------------------------------------------------------------------
# AC-1: 비추출 인용 제거 + 근거 없는 행 invalid 강등
# ---------------------------------------------------------------------------


class TestAC1NonExtractiveInvalidated:
    """AC-1 [Given] 이력서에 존재하지 않는 인용을 가진 (지지 주장) 행
    [When] verify_table
    [Then] 비추출 인용이 제거되고 행은 invalid_match=True·match_level 강등
           (direct/adjacent→weak, weak→missing)·confidence=low가 된다.
    """

    def test_AC_1_non_extractive_invalidated_direct_to_weak(self):
        """direct 행에 비추출 인용 → invalid_match=True, match_level=weak, confidence=low."""
        from worker.verify_matches import verify_table

        resume_text = "React 18 프로젝트에서 3년 경력"
        evidence = [_make_evidence("E1", resume_text)]
        resume = _make_resume(raw_text=resume_text, evidence=evidence)

        # 인용이 이력서에 없는 텍스트 (비추출)
        row = _make_row(
            "R1",
            match_level="direct",
            confidence="high",
            evidence_ids=["E1"],
            quotes=["이 텍스트는 이력서에 없음 — invented quote"],
        )
        table = _make_table([row])

        # verifier LLM을 fake로 주입 (강등 없이 통과)
        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "direct",
                        "confidence": "high",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)

        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.invalid_match is True, "비추출 인용 행은 invalid_match=True여야 함"
        assert r1.match_level == "weak", (
            f"direct → weak 강등 기대, got {r1.match_level!r}"
        )
        assert r1.confidence == "low", f"confidence=low 기대, got {r1.confidence!r}"
        # 비추출 인용은 제거됨
        assert r1.evidence_quotes == [], (
            f"비추출 인용은 제거되어야 함, got {r1.evidence_quotes!r}"
        )

    def test_AC_1_non_extractive_invalidated_weak_to_missing(self):
        """weak 행에 비추출 인용 → match_level=missing."""
        from worker.verify_matches import verify_table

        resume_text = "TypeScript strict 모드 사용"
        evidence = [_make_evidence("E1", resume_text)]
        resume = _make_resume(raw_text=resume_text, evidence=evidence)

        row = _make_row(
            "R1",
            match_level="weak",
            confidence="medium",
            evidence_ids=["E1"],
            quotes=["없는 텍스트"],
        )
        table = _make_table([row])

        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "weak",
                        "confidence": "medium",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)

        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.match_level == "missing", (
            f"weak → missing 강등 기대, got {r1.match_level!r}"
        )
        assert r1.invalid_match is True

    def test_AC_1_adjacent_to_weak(self):
        """adjacent 행에 비추출 인용 → match_level=weak."""
        from worker.verify_matches import verify_table

        resume = _make_resume(raw_text="실제 이력서 내용", evidence=[])
        row = _make_row(
            "R1",
            match_level="adjacent",
            confidence="medium",
            evidence_ids=["E1"],
            quotes=["비추출 인용"],
        )
        table = _make_table([row])

        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "adjacent",
                        "confidence": "medium",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)
        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.match_level == "weak"
        assert r1.invalid_match is True


# ---------------------------------------------------------------------------
# AC-2: verifier가 레벨을 올리려 해도 _apply_verifier는 올리지 않음
# ---------------------------------------------------------------------------


class TestAC2VerifierOnlyLowers:
    """AC-2 [Given] verifier가 match_level을 올리려는(direct로) 응답
    [When] _apply_verifier
    [Then] 레벨은 절대 올라가지 않고(min severity) 유지/강등만 된다.
    """

    def test_AC_2_verifier_cannot_upgrade_level(self):
        """verifier가 weak→direct 올리려 해도 weak 유지."""
        from worker.verify_matches import _apply_verifier

        row = _make_row("R1", match_level="weak", confidence="medium")
        # verifier 응답: direct로 올리려는 시도
        v_entry = {
            "requirement_id": "R1",
            "match_level": "direct",
            "confidence": "high",
            "exaggerated": False,
            "downgrade": False,
            "verifier_note": "looks good actually",
        }
        result = _apply_verifier(row, v_entry)
        assert result.match_level == "weak", f"레벨 올리기 금지: {result.match_level!r}"

    def test_AC_2_verifier_downgrade_exaggerated(self):
        """verifier exaggerated=True, downgrade=True → -1 강등."""
        from worker.verify_matches import _apply_verifier

        row = _make_row("R1", match_level="direct", confidence="high")
        v_entry = {
            "requirement_id": "R1",
            "match_level": "direct",
            "confidence": "medium",
            "exaggerated": True,
            "downgrade": True,
            "verifier_note": "exaggerated claim",
        }
        result = _apply_verifier(row, v_entry)
        # direct(3) -1 = adjacent(2)
        assert result.match_level == "adjacent", (
            f"exaggerated → adjacent 기대, got {result.match_level!r}"
        )

    def test_AC_2_verifier_missing_caps_confidence_low(self):
        """verifier가 missing 판정 시 confidence=low 강제."""
        from worker.verify_matches import _apply_verifier

        row = _make_row("R1", match_level="adjacent", confidence="medium")
        v_entry = {
            "requirement_id": "R1",
            "match_level": "missing",
            "confidence": "medium",
            "exaggerated": False,
            "downgrade": True,
            "verifier_note": "no real evidence",
        }
        result = _apply_verifier(row, v_entry)
        assert result.match_level == "missing"
        assert result.confidence == "low", (
            f"missing → confidence=low 기대, got {result.confidence!r}"
        )

    def test_AC_2_verify_table_verifier_cannot_upgrade(self):
        """verify_table 통합: verifier가 올리려 해도 원래 레벨 유지."""
        from worker.verify_matches import verify_table

        resume_text = "React 프로젝트 React 경험"
        evidence = [_make_evidence("E1", resume_text)]
        resume = _make_resume(raw_text=resume_text, evidence=evidence)

        # 추출형 OK 행 (weak 레벨)
        row = _make_row(
            "R1",
            match_level="weak",
            confidence="medium",
            evidence_ids=["E1"],
            quotes=[resume_text],  # verbatim — extractive OK
        )
        table = _make_table([row])

        # verifier가 direct로 올리려 함
        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "direct",
                        "confidence": "high",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "upgrade attempt",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)
        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.match_level == "weak", f"레벨 올리기 금지: {r1.match_level!r}"
        assert r1.invalid_match is False


# ---------------------------------------------------------------------------
# AC-3: 추출 가능한 verbatim 인용 → extractive_ok=True, invalid 처리 안 됨
# ---------------------------------------------------------------------------


class TestAC3ExtractiveKept:
    """AC-3 [Given] 추출 가능한 verbatim 인용을 가진 정상 행
    [When] verify_table
    [Then] extractive_ok=True로 유지되고 invalid 처리되지 않는다.
    """

    def test_AC_3_extractive_kept(self):
        """verbatim 인용 → extractive_ok=True, match_level/confidence 유지."""
        from worker.verify_matches import verify_table

        resume_text = "React 18 프로젝트에서 3년 경력"
        evidence = [_make_evidence("E1", resume_text)]
        resume = _make_resume(raw_text=resume_text, evidence=evidence)

        # evidence_quotes에 resume_text verbatim이 있음 → 추출형
        row = _make_row(
            "R1",
            match_level="direct",
            confidence="high",
            evidence_ids=["E1"],
            quotes=[resume_text],
        )
        table = _make_table([row])

        # verifier LLM fake — 강등 없이 통과
        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "direct",
                        "confidence": "high",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)

        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.extractive_ok is True, (
            f"extractive_ok=True 기대, got {r1.extractive_ok!r}"
        )
        assert r1.invalid_match is False, "정상 행은 invalid_match=False여야 함"
        assert r1.match_level == "direct", f"레벨 유지: {r1.match_level!r}"

    def test_AC_3_extractive_from_evidence_normalized_summary(self):
        """normalized_summary에 인용이 있어도 추출형으로 인정."""
        from worker.verify_matches import verify_table

        exact_q = "React 18 프로젝트"
        evidence = [
            _make_evidence("E1", exact_q, summary="리액트 18 관련 프로젝트 경험")
        ]
        resume = _make_resume(raw_text="other text", evidence=evidence)

        # quote가 evidence.exact_quote와 동일 → extractive
        row = _make_row(
            "R1",
            match_level="direct",
            confidence="high",
            evidence_ids=["E1"],
            quotes=[exact_q],
        )
        table = _make_table([row])

        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "direct",
                        "confidence": "high",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)
        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.extractive_ok is True
        assert r1.invalid_match is False

    def test_AC_3_no_evidence_ids_is_not_extractive(self):
        """evidence_ids 없이 매칭을 주장한 행 (증거 없는 주장) → invalid."""
        from worker.verify_matches import verify_table

        resume_text = "React 경험"
        resume = _make_resume(raw_text=resume_text, evidence=[])

        # 지지를 주장(match_level=direct)했으나 evidence_ids 없음
        row = _make_row(
            "R1",
            match_level="direct",
            confidence="high",
            evidence_ids=[],
            quotes=[],
        )
        table = _make_table([row])

        def fake_verifier(
            system,
            user,
            validate,
            max_tokens=1024,
            temperature=0.0,
            cache_label=None,
            **kw,
        ):
            payload = {
                "verified": [
                    {
                        "requirement_id": "R1",
                        "match_level": "direct",
                        "confidence": "high",
                        "exaggerated": False,
                        "downgrade": False,
                        "verifier_note": "",
                    }
                ]
            }
            return validate(payload)

        result = verify_table(table, resume, _call_fn=fake_verifier)
        r1 = next(r for r in result.rows if r.requirement_id == "R1")
        assert r1.invalid_match is True
        assert r1.confidence == "low"


# ---------------------------------------------------------------------------
# 헬퍼 단위 테스트 (_norm, _build_haystack, _is_extractive)
# ---------------------------------------------------------------------------


class TestHelpers:
    """_norm, _build_haystack, _is_extractive 불변식 회귀 (T-014 재사용 대비 공개 심볼)."""

    def test_norm_collapses_whitespace_and_lowercases(self):
        from worker.verify_matches import _norm

        assert _norm("  React  18 ") == "react 18"
        assert _norm("TypeScript\n strict") == "typescript strict"

    def test_is_extractive_substring_match(self):
        from worker.grounding import build_haystack, is_extractive  # per ADR-103

        evidence = [_make_evidence("E1", "React 18 프로젝트")]
        haystack = build_haystack("전체 이력서 React 18 프로젝트 내용", evidence)
        assert is_extractive("React 18 프로젝트", haystack) is True

    def test_is_extractive_non_existent(self):
        from worker.grounding import build_haystack, is_extractive  # per ADR-103

        evidence = []
        haystack = build_haystack("이력서 내용", evidence)
        assert is_extractive("없는 텍스트", haystack) is False
