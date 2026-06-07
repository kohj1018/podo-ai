"""T-066 AC-1~AC-4: domain_classifier 단위 테스트.

TDD Red phase — domain_classifier.py 신설 전 실패 테스트.
"""

from __future__ import annotations

import pytest

from core.models import EvidenceItem
from worker.domain_classifier import classify_domains


def _make_evidence(domain: list[str], skills: list[str]) -> EvidenceItem:
    return EvidenceItem(
        evidence_id="e1",
        title="test",
        source_section="skills",
        exact_quote="...",
        normalized_summary="...",
        domain=domain,
        skills=skills,
    )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def frontend_evidence() -> list[EvidenceItem]:
    return [
        _make_evidence(["frontend"], ["react", "next.js", "tailwind"]),
        _make_evidence(["frontend"], ["redux", "webpack"]),
        _make_evidence(["frontend"], ["react"]),
    ]


@pytest.fixture
def backend_evidence() -> list[EvidenceItem]:
    return [
        _make_evidence(["backend"], ["spring", "django"]),
        _make_evidence(["backend"], ["fastapi", "grpc"]),
        _make_evidence(["backend"], ["nestjs"]),
    ]


@pytest.fixture
def data_evidence() -> list[EvidenceItem]:
    return [
        _make_evidence(["data"], ["pandas", "spark"]),
        _make_evidence(["data"], ["airflow", "dbt"]),
        _make_evidence(["data"], ["bigquery", "etl"]),
    ]


@pytest.fixture
def fullstack_evidence() -> list[EvidenceItem]:
    return [
        _make_evidence(["frontend"], ["react"]),
        _make_evidence(["backend"], ["django"]),
        _make_evidence(["frontend"], ["next.js"]),
        _make_evidence(["backend"], ["fastapi"]),
    ]


@pytest.fixture
def empty_evidence() -> list[EvidenceItem]:
    return []


# ---------------------------------------------------------------------------
# AC-1: 각 도메인 이력서 → 올바른 primary_domains 반환
# ---------------------------------------------------------------------------


def test_AC_1_domain_classification_per_type(
    frontend_evidence: list[EvidenceItem],
    backend_evidence: list[EvidenceItem],
    data_evidence: list[EvidenceItem],
) -> None:
    """AC-1: 프론트엔드·백엔드·데이터 각 fixture → 올바른 primary_domains."""
    fe = classify_domains(frontend_evidence)
    assert "frontend" in fe.primary_domains, f"frontend not in {fe.primary_domains}"

    be = classify_domains(backend_evidence)
    assert "backend" in be.primary_domains, f"backend not in {be.primary_domains}"

    da = classify_domains(data_evidence)
    assert "data" in da.primary_domains, f"data not in {da.primary_domains}"


# ---------------------------------------------------------------------------
# AC-2: 신호 빈약 이력서 → confidence="low", primary_domains=["unknown"]
# ---------------------------------------------------------------------------


def test_AC_2_low_confidence_sparse_resume(empty_evidence: list[EvidenceItem]) -> None:
    """AC-2: evidence 없음 → confidence=low, primary_domains=["unknown"]."""
    result = classify_domains(empty_evidence)
    assert result.confidence == "low", f"expected low, got {result.confidence}"
    assert result.primary_domains == ["unknown"], (
        f"expected ['unknown'], got {result.primary_domains}"
    )


def test_AC_2_low_confidence_no_rule_match() -> None:
    """AC-2: 규칙 미매칭 skills → confidence=low."""
    evidence = [
        _make_evidence([], ["some_obscure_lang_x", "unknown_framework_y"]),
    ]
    result = classify_domains(evidence)
    assert result.confidence == "low"
    assert result.primary_domains == ["unknown"]


# ---------------------------------------------------------------------------
# AC-3: 풀스택 이력서 → primary_domains 복수 or confidence에 혼재 신호
# ---------------------------------------------------------------------------


def test_AC_3_fullstack_multi_domain(fullstack_evidence: list[EvidenceItem]) -> None:
    """AC-3: frontend+backend 동수 → primary_domains 복수 or confidence!=high."""
    result = classify_domains(fullstack_evidence)
    multi_primary = len(result.primary_domains) >= 2
    mixed_confidence = result.confidence in ("medium", "low")
    assert multi_primary or mixed_confidence, (
        f"fullstack 혼재 신호가 반영되지 않음: primary={result.primary_domains}, "
        f"confidence={result.confidence}"
    )


# ---------------------------------------------------------------------------
# AC-4: 결정성 — 동일 fixture 2회 호출 → 동일 결과
# ---------------------------------------------------------------------------


def test_AC_4_deterministic_output(frontend_evidence: list[EvidenceItem]) -> None:
    """AC-4: 동일 입력 2회 호출 → DomainResult 동일(GS-1 정합, CLASSIFIER_VERSION 핀)."""
    result1 = classify_domains(frontend_evidence)
    result2 = classify_domains(frontend_evidence)
    assert result1 == result2, f"비결정적 출력: {result1} vs {result2}"
