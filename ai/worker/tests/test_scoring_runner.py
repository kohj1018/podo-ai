"""T-065 scoring_runner 단위 테스트 — AC-2 (TDD Red → Green).

AC-2: run_full_scoring() 실행 시 run_scoring 내부 LLM 호출이 K(후보)에 비례,
      recommendations에 K개 이내 deep 결과만 저장.

LLM·DB 호출 없음 — 모두 mock으로 대체.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from worker.scoring_runner import run_full_scoring

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_jobs(n: int) -> list[dict[str, Any]]:
    return [
        {
            "job_id": str(i + 1),
            "raw_text": f"Python Django backend {i + 1}",
            "role_family": "backend",
            "source": "toss",
            "company": f"Co{i + 1}",
            "title": f"BE {i + 1}",
            "url": f"https://example.com/{i + 1}",
        }
        for i in range(n)
    ]


def _make_resume() -> Any:
    from core.models import Resume

    return Resume(raw_text="Python 5년 backend", primary_domains=["backend"])


def _mock_candidate_set(k: int, all_jobs: list[dict[str, Any]]) -> Any:
    """처음 k개만 후보로 하는 CandidateSet mock."""
    from worker.prefilter import CandidateSet

    candidates = [j["job_id"] for j in all_jobs[:k]]
    non_candidates = [j["job_id"] for j in all_jobs[k:]]
    sim_map = {jid: 0.9 - i * 0.01 for i, jid in enumerate(candidates)}
    return CandidateSet(
        candidates=candidates,
        similarity_map=sim_map,
        non_candidates=non_candidates,
    )


def _dummy_run_scoring_result(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """run_scoring 반환 형식 최소 fixture."""
    return {
        "final_ranking": {
            "note": "fit은 보수적 레벨",
            "user_profile": {},
            "guard_moves": [],
            "ranking": [
                {"job_id": j["job_id"], "fit_level": 3, "domain_alignment": "strong"}
                for j in candidates
            ],
        },
        "matching_tables": {},
        "pairwise_comparisons": {
            "bradley_terry_scores": {},
            "candidate_set": [],
            "comparisons": [],
        },
        "pending_job_ids": set(),
    }


# ---------------------------------------------------------------------------
# AC-2: LLM 호출이 K에 비례 (N이 아님)
# ---------------------------------------------------------------------------


class TestAC2LlmCallsProportionalToK:
    """AC-2: N개 JD 중 K개 후보 선별 → run_scoring은 K개에만 호출."""

    def test_AC_2_llm_calls_proportional_to_K(self) -> None:
        """run_full_scoring() 실행 시 run_scoring에 전달되는 jobs 수 = K (N이 아님)."""
        N = 10
        K = 3
        all_jobs = _make_jobs(N)
        resume = _make_resume()
        mock_conn = MagicMock()

        candidate_set = _mock_candidate_set(K, all_jobs)
        scoring_result = _dummy_run_scoring_result(all_jobs[:K])

        with (
            patch(
                "worker.scoring_runner.select_candidates", return_value=candidate_set
            ),
            patch(
                "worker.scoring_runner.run_scoring", return_value=scoring_result
            ) as mock_run,
            patch("worker.scoring_runner.materialize_coarse"),
            patch(
                "worker.scoring_runner._load_resume_embedding",
                return_value=[0.1] * 1536,
            ),
            patch(
                "worker.scoring_runner._load_resume_domains", return_value=["backend"]
            ),
        ):
            run_full_scoring(
                conn=mock_conn,
                resume=resume,
                resume_id=1,
                all_jobs=all_jobs,
            )

        # run_scoring에 전달된 jobs 수 = K (N이 아님)
        assert mock_run.call_count == 1
        called_jobs = (
            mock_run.call_args[1]["jobs"]
            if mock_run.call_args[1]
            else mock_run.call_args[0][1]
        )
        assert len(called_jobs) == K, (
            f"run_scoring에 K={K}개가 아닌 {len(called_jobs)}개 전달됨"
        )

    def test_AC_2_coarse_materialize_called_with_non_candidates(self) -> None:
        """run_full_scoring()이 후보 밖 N-K개를 coarse_materialize에 전달한다."""
        N = 8
        K = 3
        all_jobs = _make_jobs(N)
        resume = _make_resume()
        mock_conn = MagicMock()

        candidate_set = _mock_candidate_set(K, all_jobs)
        scoring_result = _dummy_run_scoring_result(all_jobs[:K])

        with (
            patch(
                "worker.scoring_runner.select_candidates", return_value=candidate_set
            ),
            patch("worker.scoring_runner.run_scoring", return_value=scoring_result),
            patch("worker.scoring_runner.materialize_coarse") as mock_coarse,
            patch(
                "worker.scoring_runner._load_resume_embedding",
                return_value=[0.1] * 1536,
            ),
            patch(
                "worker.scoring_runner._load_resume_domains", return_value=["backend"]
            ),
        ):
            run_full_scoring(
                conn=mock_conn,
                resume=resume,
                resume_id=1,
                all_jobs=all_jobs,
            )

        # coarse materialize가 1회 호출되고 non_candidates = N-K개
        mock_coarse.assert_called_once()
        call_kwargs = mock_coarse.call_args
        non_cands = call_kwargs[1].get("non_candidates") or call_kwargs[0][0]
        assert len(non_cands) == N - K, (
            f"non_candidates 수 불일치: expected={N - K}, got={len(non_cands)}"
        )

    def test_AC_2_recommendations_deep_only(self) -> None:
        """run_full_scoring 반환값에 deep 결과(K개 이내)만 포함."""
        N = 6
        K = 2
        all_jobs = _make_jobs(N)
        resume = _make_resume()
        mock_conn = MagicMock()

        candidate_set = _mock_candidate_set(K, all_jobs)
        scoring_result = _dummy_run_scoring_result(all_jobs[:K])

        with (
            patch(
                "worker.scoring_runner.select_candidates", return_value=candidate_set
            ),
            patch("worker.scoring_runner.run_scoring", return_value=scoring_result),
            patch("worker.scoring_runner.materialize_coarse"),
            patch(
                "worker.scoring_runner._load_resume_embedding",
                return_value=[0.1] * 1536,
            ),
            patch(
                "worker.scoring_runner._load_resume_domains", return_value=["backend"]
            ),
        ):
            result = run_full_scoring(
                conn=mock_conn,
                resume=resume,
                resume_id=1,
                all_jobs=all_jobs,
            )

        ranking = result["final_ranking"]["ranking"]
        assert len(ranking) <= K, f"recommendations에 K={K}개 초과: {len(ranking)}개"
        # 후보 밖 공고 id가 ranking에 없어야 함
        non_cand_ids = set(candidate_set.non_candidates)
        for item in ranking:
            assert item["job_id"] not in non_cand_ids, (
                f"후보 밖 공고 {item['job_id']}가 deep ranking에 포함됨"
            )
