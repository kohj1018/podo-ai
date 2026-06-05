"""T-008 Acceptance Criteria tests — bradley_terry + aggregate (rank_aggregate.py).

SPEC §5 알고리즘을 검증한다.
"""

from core.models import MatchingTable, MatchRow, PairwiseResult
from worker.rank_aggregate import aggregate, bradley_terry

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _row(
    rid: str,
    req_type: str = "required",
    req_nature: str = "technical",
    prereq_status: str = "prerequisite",
    req_category: str = "other",
    match_level: str = "direct",
    confidence: str = "high",
    invalid_match: bool = False,
    req_text: str = "some requirement",
) -> MatchRow:
    return MatchRow(
        requirement_id=rid,
        requirement_text=req_text,
        requirement_type=req_type,
        requirement_nature=req_nature,
        prerequisite_status=prereq_status,
        requirement_category=req_category,
        match_level=match_level,
        confidence=confidence,
        invalid_match=invalid_match,
    )


def _table(rows: list[MatchRow], job_id: str = "job-1") -> MatchingTable:
    return MatchingTable(job_id=job_id, company="Corp", title="Dev", rows=rows)


def _pair(a: str, b: str, winner: str) -> PairwiseResult:
    """A/B 양방향이 일치하는 pairwise 결과 헬퍼."""
    return PairwiseResult(
        job_a=a,
        job_b=b,
        ab_winner=winner,
        ba_winner=winner,
        agreed=(winner != "tie"),
        outcome=winner,
        confidence="high",
    )


# ---------------------------------------------------------------------------
# AC-1: 명확한 pairwise 승패 → bradley_terry 결정적·수렴·승자 강도 > 패자
# ---------------------------------------------------------------------------


def test_AC_1_bt_converges_deterministic() -> None:
    """Given 명확한 pairwise 승패 집합
    When bradley_terry 두 번 호출
    Then 동일 점수로 수렴하고(결정적) 승자 강도 > 패자 강도다.
    """
    # job-A 가 job-B 를 3:0 으로 이기는 집합
    results = [
        _pair("job-A", "job-B", "job-A"),
        _pair("job-A", "job-B", "job-A"),
        _pair("job-A", "job-B", "job-A"),
    ]
    ids = ["job-A", "job-B"]

    scores1 = bradley_terry(ids, results)
    scores2 = bradley_terry(ids, results)

    # 결정적: 두 번 호출 결과가 동일
    assert scores1 == scores2, "bradley_terry must be deterministic"

    # 승자(job-A)가 패자(job-B)보다 강해야 함
    assert scores1["job-A"] > scores1["job-B"], "winner BT score must exceed loser"

    # 평균 정규화: 두 점수 평균 ≈ 1.0
    mean = sum(scores1.values()) / len(scores1)
    assert abs(mean - 1.0) < 1e-6, f"mean BT score should be 1.0, got {mean}"


def test_AC_1_bt_edge_empty() -> None:
    """n==0 → {} 반환."""
    assert bradley_terry([], []) == {}


def test_AC_1_bt_edge_single() -> None:
    """n==1 → {id: 1.0} 반환."""
    assert bradley_terry(["only"], []) == {"only": 1.0}


# ---------------------------------------------------------------------------
# AC-2: domain_fit_bt 정렬 키 — tier desc → fit desc → BT desc → lw → jid
# ---------------------------------------------------------------------------


def test_AC_2_domain_fit_bt_sort_key() -> None:
    """Given 같은 fits·domain_ctx
    When aggregate(ranking_mode='domain_fit_bt')
    Then 순서가 (도메인 tier desc → fit desc → BT desc → listwise → jid) 키를
         따르고 같은 tier 내 fit이 단조 비증가다.
    """
    # 3개 JD: strong/fit=4, strong/fit=3, adjacent/fit=5
    # domain_fit_bt → tier 우선이므로 strong 두 개가 adjacent(fit=5)보다 먼저
    jobs_by_id = {
        "j-strong-4": _table([_row("r1")], job_id="j-strong-4"),
        "j-strong-3": _table([_row("r2")], job_id="j-strong-3"),
        "j-adj-5": _table([_row("r3")], job_id="j-adj-5"),
    }
    tables_by_id = dict(jobs_by_id)
    listwise = ["j-strong-4", "j-adj-5", "j-strong-3"]
    pairwise: list[PairwiseResult] = []  # BT 비교 없음 — pairwise 비교집합 외
    candidate_ids: set[str] = set()  # BT 대상 없음

    fits = {
        "j-strong-4": {
            "level": 4,
            "label": "높음: 추천",
            "coverage": {},
            "strong": [],
            "weak": [],
            "preferred_gaps": [],
            "product_duties": [],
            "invalid": [],
            "risks": [],
            "dedup_audit": [],
        },
        "j-strong-3": {
            "level": 3,
            "label": "보통: 검토 가능",
            "coverage": {},
            "strong": [],
            "weak": [],
            "preferred_gaps": [],
            "product_duties": [],
            "invalid": [],
            "risks": [],
            "dedup_audit": [],
        },
        "j-adj-5": {
            "level": 5,
            "label": "매우 높음: 강력 추천",
            "coverage": {},
            "strong": [],
            "weak": [],
            "preferred_gaps": [],
            "product_duties": [],
            "invalid": [],
            "risks": [],
            "dedup_audit": [],
        },
    }
    domain_ctx = {
        "j-strong-4": {"domain_alignment": "strong", "role_family": "frontend"},
        "j-strong-3": {"domain_alignment": "strong", "role_family": "backend"},
        "j-adj-5": {"domain_alignment": "adjacent", "role_family": "fullstack"},
    }

    results, bt_scores, guard_moves = aggregate(
        jobs_by_id=jobs_by_id,
        tables_by_id=tables_by_id,
        listwise=listwise,
        pairwise=pairwise,
        candidate_ids=candidate_ids,
        fits=fits,
        domain_ctx=domain_ctx,
        ranking_mode="domain_fit_bt",
    )

    ranked_ids = [r.job_id for r in results]

    # strong tier 두 개가 adjacent보다 먼저
    adj_rank = ranked_ids.index("j-adj-5")
    strong4_rank = ranked_ids.index("j-strong-4")
    strong3_rank = ranked_ids.index("j-strong-3")

    assert strong4_rank < adj_rank, "strong/fit=4 must rank above adjacent/fit=5"
    assert strong3_rank < adj_rank, "strong/fit=3 must rank above adjacent/fit=5"

    # 같은 strong tier 내에서 fit 단조 비증가
    assert strong4_rank < strong3_rank, "within same tier, higher fit must come first"

    # rank 필드가 1-based 연속
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(results) + 1)), (
        f"ranks must be 1-based sequential: {ranks}"
    )


# ---------------------------------------------------------------------------
# AC-3: mismatch 가드 — 모든 모드에서 mismatch는 non-mismatch 아래
# ---------------------------------------------------------------------------


def test_AC_3_mismatch_guard_all_modes() -> None:
    """Given mismatch(marketing) 1건이 fit/BT상 상위로 정렬될 입력
    When 어떤 ranking_mode로든 aggregate
    Then mismatch는 모든 non-mismatch 아래로 배치되고 guard_moves에 기록된다.
    """
    # marketing(mismatch)/fit=5 vs backend(strong)/fit=2
    # 가드 없으면 marketing이 상위지만, 가드 후 backend가 위에 와야 함
    jobs_by_id = {
        "j-mismatch": _table([_row("r1")], job_id="j-mismatch"),
        "j-nonmis": _table([_row("r2")], job_id="j-nonmis"),
    }
    tables_by_id = dict(jobs_by_id)
    # listwise가 mismatch를 1위로 올린 상황
    listwise = ["j-mismatch", "j-nonmis"]
    pairwise: list[PairwiseResult] = []
    candidate_ids: set[str] = set()

    fits = {
        "j-mismatch": {
            "level": 5,
            "label": "매우 높음: 강력 추천",
            "coverage": {},
            "strong": [],
            "weak": [],
            "preferred_gaps": [],
            "product_duties": [],
            "invalid": [],
            "risks": [],
            "dedup_audit": [],
        },
        "j-nonmis": {
            "level": 2,
            "label": "낮음: 아쉬움",
            "coverage": {},
            "strong": [],
            "weak": [],
            "preferred_gaps": [],
            "product_duties": [],
            "invalid": [],
            "risks": [],
            "dedup_audit": [],
        },
    }
    domain_ctx = {
        "j-mismatch": {"domain_alignment": "mismatch", "role_family": "marketing"},
        "j-nonmis": {"domain_alignment": "strong", "role_family": "backend"},
    }

    # fit_primary 모드에서는 fit=5인 mismatch가 정렬 전에는 1위가 돼
    # 가드 후 non-mismatch 아래로 이동 → guard_moves에 기록돼야 함
    all_guard_moves: list[dict] = []
    for mode in ("domain_fit_bt", "fit_primary", "bt_primary"):
        results, _, guard_moves = aggregate(
            jobs_by_id=jobs_by_id,
            tables_by_id=tables_by_id,
            listwise=listwise,
            pairwise=pairwise,
            candidate_ids=candidate_ids,
            fits=fits,
            domain_ctx=domain_ctx,
            ranking_mode=mode,
        )

        ranked_ids = [r.job_id for r in results]
        mismatch_rank = ranked_ids.index("j-mismatch")
        nonmis_rank = ranked_ids.index("j-nonmis")

        assert mismatch_rank > nonmis_rank, (
            f"mode={mode}: mismatch must rank below non-mismatch, "
            f"got mismatch={mismatch_rank} nonmis={nonmis_rank}"
        )

        all_guard_moves.extend(guard_moves)

    # fit_primary (또는 bt_primary)에서 mismatch가 실제 이동되므로 guard_moves에 기록돼야 함
    # (domain_fit_bt는 정렬 키 자체가 tier 우선이라 이동 없을 수 있음 — 정상)
    moved_ids = [m["job_id"] for m in all_guard_moves]
    assert "j-mismatch" in moved_ids, (
        f"j-mismatch must appear in guard_moves for at least one mode, got {all_guard_moves}"
    )
