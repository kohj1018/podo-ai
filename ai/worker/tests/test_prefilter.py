"""T-065 prefilter 단위 테스트 — AC-1·AC-4 (TDD Red → Green).

AC-1: 벡터+도메인+스킬 합집합 → K_max cap → 결정적 tie-break(유사도 desc/job_id asc).
AC-4: 동일 입력 2회 호출 → 동일 후보 집합(GS-1 결정성).

DB 의존 없음 — 벡터 유사도·합집합 로직만 mock으로 검증.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from worker.prefilter import CandidateSet, select_candidates

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_jobs(n: int) -> list[dict[str, Any]]:
    """n개 공고 dict(job_id, raw_text, role_family) 생성."""
    return [
        {
            "job_id": str(i + 1),
            "raw_text": f"Python Django backend 공고 {i + 1}",
            "role_family": "backend",
            "source": "toss",
            "company": f"Co{i + 1}",
            "title": f"BE {i + 1}",
            "url": f"https://example.com/{i + 1}",
        }
        for i in range(n)
    ]


def _mock_similarity_rows(jobs: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """job_id → similarity 내림차순(인덱스가 높을수록 유사도 낮게)."""
    return [(j["job_id"], round(1.0 - i * 0.01, 4)) for i, j in enumerate(jobs)]


# ---------------------------------------------------------------------------
# AC-1: 합집합·K_max cap·tie-break 결정성
# ---------------------------------------------------------------------------


class TestAC1HybridUnionAndDeterministicTiebreak:
    """AC-1: N개 JD + 이력서 임베딩 → select_candidates() →
    합집합이 K_max 이하로 cap, 동일 입력 동일 후보, tie-break 결정적."""

    def test_AC_1_hybrid_union_and_deterministic_tiebreak(self) -> None:
        """벡터 top-K_v ∪ 도메인 ∪ 스킬 합집합 → K_max cap → tie-break 검증."""
        jobs = _make_jobs(20)
        resume_embedding = [0.1] * 1536
        resume_domains = ["backend"]

        # DB conn mock: SELECT 결과로 similarity row 반환
        mock_conn = MagicMock()
        sim_rows = _mock_similarity_rows(jobs)  # 20행

        # select_candidates 내 _fetch_vector_top_k는 mock_conn 사용
        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows[:10]):
            result: CandidateSet = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=10,
                K_max=15,
            )

        # K_max=15 cap 확인
        assert len(result.candidates) <= 15, f"K_max cap 위반: {len(result.candidates)}"
        # 결과는 리스트(순서 있음)
        assert isinstance(result.candidates, list)
        # 후보 job_id는 jobs에 속해야 함
        job_id_set = {j["job_id"] for j in jobs}
        for jid in result.candidates:
            assert jid in job_id_set, f"알 수 없는 job_id: {jid}"

    def test_AC_1_tiebreak_similarity_desc_jobid_asc(self) -> None:
        """동일 유사도 값이 여럿일 때 tie-break: 유사도 desc → job_id asc(결정적)."""
        # 모든 공고 유사도 동일(0.5)
        jobs = _make_jobs(5)
        resume_embedding = [0.1] * 1536
        resume_domains: list[str] = []

        # 유사도 모두 0.5
        sim_rows_tied = [(j["job_id"], 0.5) for j in jobs]

        mock_conn = MagicMock()
        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows_tied):
            result = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=5,
                K_max=5,
            )

        # job_id asc 순서 검증(모두 동일 유사도 → job_id "1","2","3","4","5")
        assert result.candidates == sorted(result.candidates, key=lambda x: int(x)), (
            f"tie-break job_id asc 위반: {result.candidates}"
        )

    def test_AC_1_kmax_cap_is_enforced(self) -> None:
        """합집합이 K_max보다 커도 K_max 이하로 cap된다."""
        jobs = _make_jobs(30)
        resume_embedding = [0.1] * 1536
        resume_domains = ["backend", "data"]

        sim_rows = _mock_similarity_rows(jobs)
        mock_conn = MagicMock()

        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows[:20]):
            result = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=20,
                K_max=8,
            )

        assert len(result.candidates) <= 8, (
            f"K_max=8 cap 위반: {len(result.candidates)}"
        )

    def test_AC_1_similarity_map_populated(self) -> None:
        """CandidateSet.similarity_map에 후보 job_id → 유사도 값이 채워진다."""
        jobs = _make_jobs(5)
        resume_embedding = [0.1] * 1536
        resume_domains: list[str] = []
        sim_rows = _mock_similarity_rows(jobs)

        mock_conn = MagicMock()
        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows):
            result = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=5,
                K_max=5,
            )

        for jid in result.candidates:
            assert jid in result.similarity_map, f"similarity_map에 {jid} 없음"
            assert isinstance(result.similarity_map[jid], float)


# ---------------------------------------------------------------------------
# AC-4: 결정성(GS-1) — 동일 입력 2회 호출 동일 결과
# ---------------------------------------------------------------------------


class TestAC4DeterministicCandidatesGs1:
    """AC-4: 동일 (이력서, 공고집합) 2회 연속 select_candidates() → 동일 후보 집합."""

    def test_AC_4_deterministic_candidates_gs1(self) -> None:
        """GS-1: 동일 입력 2회 → 후보 집합·순서 완전 동일."""
        jobs = _make_jobs(15)
        resume_embedding = [0.1] * 1536
        resume_domains = ["backend"]
        sim_rows = _mock_similarity_rows(jobs)

        mock_conn = MagicMock()
        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows[:10]):
            result1 = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=10,
                K_max=12,
            )

        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows[:10]):
            result2 = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=10,
                K_max=12,
            )

        assert result1.candidates == result2.candidates, (
            f"GS-1 위반: 1차={result1.candidates}, 2차={result2.candidates}"
        )
        assert result1.similarity_map == result2.similarity_map, (
            "GS-1 위반: similarity_map 불일치"
        )

    def test_AC_4_different_kmax_gives_subset(self) -> None:
        """K_max가 다르면 후보 수가 달라도 K_max 이하 불변식은 유지된다."""
        jobs = _make_jobs(10)
        resume_embedding = [0.1] * 1536
        resume_domains: list[str] = []
        sim_rows = _mock_similarity_rows(jobs)

        mock_conn = MagicMock()
        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows):
            result_small = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=10,
                K_max=5,
            )
        with patch("worker.prefilter._fetch_vector_top_k", return_value=sim_rows):
            result_large = select_candidates(
                conn=mock_conn,
                resume_embedding=resume_embedding,
                jobs=jobs,
                resume_domains=resume_domains,
                K_v=10,
                K_max=10,
            )

        assert len(result_small.candidates) <= 5
        assert len(result_large.candidates) <= 10
