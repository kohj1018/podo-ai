"""T-016 골든 페어 정확도 (SPEC §10-3).

사람이 라벨링한 A/B 공고 쌍과 시스템 순위 일치율을 측정한다.
LLM 호출 없음 — outputs/eval/<persona>/의 저장 산출물만 읽음.

- propose_pairs: 저장 산출물에서 하드 케이스 자동 추출 (라벨 X)
- load_pairs: 라벨 검증, 빈 라벨 분리 (graceful skip)
- evaluate_pairs: 페어별 시스템 정답 여부 판정
- aggregate_metrics: strict/tie-aware 정확도 + 페르소나/난이도/카테고리별
- rescore_persona: 저장 산출물만으로 fit 재계산 + aggregate() 재사용 (ablation)

A/B 규약: A = 기본 모드(domain_fit_bt)가 더 높게 랭크한 공고.
LABELS: A_better / B_better / tie / unsure
CATEGORIES: SPEC §10-3 8종
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.models import MatchingTable, PairwiseResult
from worker.rank_aggregate import aggregate, compute_fit

# ---------------------------------------------------------------------------
# 상수 (SPEC §10-3)
# ---------------------------------------------------------------------------

LABELS: tuple[str, ...] = ("A_better", "B_better", "tie", "unsure")

CATEGORIES: tuple[str, ...] = (
    "same_domain_close",
    "adjacent_vs_primary",
    "seniority_gap",
    "domain_transfer",
    "tool_stack_gap",
    "product_duty_vs_prerequisite",
    "weak_vs_adjacent",
    "mismatch_guard",
)

_HARDNESS_SIGNALS_THRESHOLD_HARD = 3
_HARDNESS_SIGNALS_THRESHOLD_MEDIUM = 2


# ---------------------------------------------------------------------------
# 데이터 구조
# ---------------------------------------------------------------------------


@dataclass
class GoldenPair:
    """사람 라벨이 달린 A/B 공고 쌍."""

    pair_id: str
    job_a: str  # 기본 모드(domain_fit_bt)가 더 높게 랭크한 공고
    job_b: str
    label: str  # LABELS 중 하나 (빈 문자열이면 미라벨)
    category: str = "same_domain_close"
    hardness: int = 1  # 합산 신호 수 (≥3 hard, ≥2 medium, else easy)
    job_a_rank: int = 0
    job_b_rank: int = 0
    job_a_fit: int = 0
    job_b_fit: int = 0
    notes: str = ""


@dataclass
class EvaluatedPair:
    """페어별 시스템 정답 여부 판정 결과."""

    pair: GoldenPair
    system_winner: str  # "A" | "B" | "tie"
    correct_strict: bool | None  # unsure/unavailable이면 None
    correct_tie_aware: bool | None
    unavailable: bool = False  # ranking에 없는 공고 포함 시 True


@dataclass
class PairMetrics:
    """aggregate_metrics 반환값."""

    # strict pairwise (분모: A_better + B_better)
    strict_correct: int = 0
    strict_total: int = 0
    strict_accuracy: float = 0.0

    # tie-aware (분모: A_better + B_better + tie, unsure 제외)
    tie_aware_correct: int = 0
    tie_aware_total: int = 0
    tie_aware_accuracy: float = 0.0

    unsure_count: int = 0
    unavailable_count: int = 0

    # 모드별 (현재 domain_fit_bt 단일 — ranking 이미 해당 모드 기준)
    by_mode: dict[str, dict[str, int]] = field(default_factory=dict)

    # 난이도별
    by_hardness: dict[str, dict[str, int]] = field(default_factory=dict)

    # 카테고리별
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)

    # 모드 불일치 목록 (시스템 ≠ 사람)
    disagreements: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# propose_pairs: 하드 케이스 자동 추출 (라벨 X)
# ---------------------------------------------------------------------------


def propose_pairs(
    ranking: list[dict[str, Any]],
    tables: dict[str, Any] | None = None,
    pairwise: list[dict[str, Any]] | None = None,
) -> list[GoldenPair]:
    """저장 산출물에서 하드 케이스를 자동 추출한다 (라벨 없음, expected_winner 공백).

    신호: 같은 직군·근접 fit, 모드 불일치, fit↔BT 불일치,
          주력 vs 인접 fit 역전, 연차 갭, 동일 회사 유사 직군.
    난이도: 합 ≥3 hard / ≥2 medium / else easy.
    """
    if not ranking or len(ranking) < 2:
        return []

    by_rank = sorted(ranking, key=lambda r: r["rank"])
    pairs: list[GoldenPair] = []
    pair_counter = 0

    for i in range(len(by_rank)):
        for j in range(i + 1, len(by_rank)):
            a = by_rank[i]
            b = by_rank[j]
            signals = 0

            # 신호 1: 같은 직군·근접 fit
            if a.get("role_family") == b.get("role_family"):
                if abs(a.get("fit_level", 0) - b.get("fit_level", 0)) <= 1:
                    signals += 1

            # 신호 2: fit↔rank 역전 (fit 높은데 rank 낮음)
            if a.get("fit_level", 0) < b.get("fit_level", 0):
                signals += 1

            # 신호 3: 도메인 tier 역전 (adjacent가 strong 위)
            dom_map = {"strong": 3, "adjacent": 2, "weak": 1, "mismatch": 0}
            da = dom_map.get(a.get("domain_alignment", "weak"), 1)
            db = dom_map.get(b.get("domain_alignment", "weak"), 1)
            if da < db:
                signals += 1

            if signals == 0:
                continue

            pair_counter += 1

            # 카테고리 추론 (단순 휴리스틱)
            if a.get("domain_alignment") != b.get("domain_alignment"):
                category = "adjacent_vs_primary"
            elif a.get("role_family") == b.get("role_family"):
                category = "same_domain_close"
            else:
                category = "same_domain_close"

            pairs.append(
                GoldenPair(
                    pair_id=f"proposed-{pair_counter}",
                    job_a=a["job_id"],
                    job_b=b["job_id"],
                    label="",  # 미라벨
                    category=category,
                    hardness=signals,
                    job_a_rank=a["rank"],
                    job_b_rank=b["rank"],
                    job_a_fit=a.get("fit_level", 0),
                    job_b_fit=b.get("fit_level", 0),
                )
            )

    return pairs


# ---------------------------------------------------------------------------
# load_pairs: JSON/dict에서 GoldenPair 로드 + 라벨 검증
# ---------------------------------------------------------------------------


def load_pairs(
    data: list[dict[str, Any]],
) -> tuple[list[GoldenPair], list[GoldenPair]]:
    """라벨 검증 후 (라벨된 페어, 미라벨 페어)를 반환한다.

    빈 라벨("") 또는 유효하지 않은 라벨은 미라벨로 분리 (graceful skip).
    유효 LABELS = LABELS 상수 참조.
    """
    labeled: list[GoldenPair] = []
    unlabeled: list[GoldenPair] = []

    for row in data:
        pair = GoldenPair(
            pair_id=row.get("pair_id", ""),
            job_a=row.get("job_a", ""),
            job_b=row.get("job_b", ""),
            label=row.get("label", ""),
            category=row.get("category", "same_domain_close"),
            hardness=row.get("hardness", 1),
            job_a_rank=row.get("job_a_rank", 0),
            job_b_rank=row.get("job_b_rank", 0),
            job_a_fit=row.get("job_a_fit", 0),
            job_b_fit=row.get("job_b_fit", 0),
            notes=row.get("notes", ""),
        )
        if pair.label in LABELS:
            labeled.append(pair)
        else:
            unlabeled.append(pair)

    return labeled, unlabeled


def load_pairs_from_file(path: Path) -> tuple[list[GoldenPair], list[GoldenPair]]:
    """JSON 파일에서 골든 페어를 로드한다."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("pairs", [])
    return load_pairs(data)


# ---------------------------------------------------------------------------
# evaluate_pairs: 페어별 시스템 정답 여부 판정
# ---------------------------------------------------------------------------


def evaluate_pairs(
    pairs: list[GoldenPair],
    ranking: dict[str, int],
    fit_by_id: dict[str, int],
    available_ids: set[str],
) -> list[EvaluatedPair]:
    """페어별 시스템 정답 여부를 판정한다.

    Args:
        pairs: 라벨된 골든 페어 목록
        ranking: job_id → rank (기본 모드 domain_fit_bt 기준)
        fit_by_id: job_id → fit_level
        available_ids: ranking에 실재하는 job_id 집합 (없으면 unavailable)

    Returns:
        EvaluatedPair 목록
    """
    results: list[EvaluatedPair] = []

    for pair in pairs:
        # unavailable 체크
        unavailable = pair.job_a not in available_ids or pair.job_b not in available_ids

        if unavailable:
            results.append(
                EvaluatedPair(
                    pair=pair,
                    system_winner="unavailable",
                    correct_strict=None,
                    correct_tie_aware=None,
                    unavailable=True,
                )
            )
            continue

        # 시스템 winner 판정
        rank_a = ranking.get(pair.job_a, 9999)
        rank_b = ranking.get(pair.job_b, 9999)
        fit_a = fit_by_id.get(pair.job_a, 0)
        fit_b = fit_by_id.get(pair.job_b, 0)

        if rank_a < rank_b:
            system_winner = "A"
        elif rank_b < rank_a:
            system_winner = "B"
        else:
            system_winner = "tie"

        # tie-aware: 같은 fit_level이면 시스템도 tie로 간주
        system_tie_aware = system_winner == "tie" or fit_a == fit_b

        # strict 정답 (분모: A_better + B_better만)
        label = pair.label
        if label == "unsure":
            correct_strict = None
            correct_tie_aware = None
        elif label == "A_better":
            correct_strict = system_winner == "A"
            correct_tie_aware = system_winner == "A" or system_tie_aware
        elif label == "B_better":
            correct_strict = system_winner == "B"
            correct_tie_aware = system_winner == "B" or system_tie_aware
        elif label == "tie":
            correct_strict = None  # tie는 strict 분모 제외
            correct_tie_aware = system_tie_aware
        else:
            correct_strict = None
            correct_tie_aware = None

        results.append(
            EvaluatedPair(
                pair=pair,
                system_winner=system_winner,
                correct_strict=correct_strict,
                correct_tie_aware=correct_tie_aware,
                unavailable=False,
            )
        )

    return results


# ---------------------------------------------------------------------------
# aggregate_metrics: strict/tie-aware + 세분화
# ---------------------------------------------------------------------------


def aggregate_metrics(
    pairs: list[GoldenPair],
    ranking: dict[str, int],
    fit_by_id: dict[str, int],
    available_ids: set[str],
    ranking_mode: str = "domain_fit_bt",
) -> PairMetrics:
    """strict pairwise + tie-aware 정확도를 모드/난이도/카테고리별로 산출한다.

    unavailable 공고 포함 페어는 집계에서 제외 (재수집 X).
    """
    evaluated = evaluate_pairs(pairs, ranking, fit_by_id, available_ids)

    metrics = PairMetrics()
    metrics.by_mode = {ranking_mode: {"strict_correct": 0, "strict_total": 0}}

    for ev in evaluated:
        if ev.unavailable:
            metrics.unavailable_count += 1
            continue

        label = ev.pair.label
        if label == "unsure":
            metrics.unsure_count += 1
            continue

        hardness_key = _hardness_label(ev.pair.hardness)
        cat_key = ev.pair.category

        # strict 집계 (A_better / B_better만)
        if label in ("A_better", "B_better"):
            metrics.strict_total += 1
            if ev.correct_strict:
                metrics.strict_correct += 1
                metrics.by_mode[ranking_mode]["strict_correct"] += 1
            metrics.by_mode[ranking_mode]["strict_total"] = metrics.strict_total

            # 난이도별
            if hardness_key not in metrics.by_hardness:
                metrics.by_hardness[hardness_key] = {
                    "strict_correct": 0,
                    "strict_total": 0,
                }
            metrics.by_hardness[hardness_key]["strict_total"] += 1
            if ev.correct_strict:
                metrics.by_hardness[hardness_key]["strict_correct"] += 1

            # 카테고리별
            if cat_key not in metrics.by_category:
                metrics.by_category[cat_key] = {"strict_correct": 0, "strict_total": 0}
            metrics.by_category[cat_key]["strict_total"] += 1
            if ev.correct_strict:
                metrics.by_category[cat_key]["strict_correct"] += 1

            # 불일치 기록
            if not ev.correct_strict:
                metrics.disagreements.append(
                    f"{ev.pair.pair_id}: label={label} system={ev.system_winner}"
                    f" A={ev.pair.job_a}(rank={ev.pair.job_a_rank})"
                    f" B={ev.pair.job_b}(rank={ev.pair.job_b_rank})"
                )

        # tie-aware 집계 (A_better + B_better + tie)
        if label in ("A_better", "B_better", "tie"):
            metrics.tie_aware_total += 1
            if ev.correct_tie_aware:
                metrics.tie_aware_correct += 1

    # 정확도 산출
    if metrics.strict_total > 0:
        metrics.strict_accuracy = metrics.strict_correct / metrics.strict_total
    if metrics.tie_aware_total > 0:
        metrics.tie_aware_accuracy = metrics.tie_aware_correct / metrics.tie_aware_total

    return metrics


def _hardness_label(signals: int) -> str:
    if signals >= _HARDNESS_SIGNALS_THRESHOLD_HARD:
        return "hard"
    if signals >= _HARDNESS_SIGNALS_THRESHOLD_MEDIUM:
        return "medium"
    return "easy"


# ---------------------------------------------------------------------------
# rescore_persona: 저장 산출물만으로 ablation (LLM 미호출)
# ---------------------------------------------------------------------------


def rescore_persona(
    eval_root: Path,
    persona: str,
    scoring_mode: str = "baseline",
    ranking_mode: str = "domain_fit_bt",
) -> tuple[list[Any], dict[str, float], list[dict[str, Any]]]:
    """저장 산출물만으로 fit 재계산 + 실제 aggregate() 재사용 → LLM 없이 ablation.

    scoring_mode: "baseline" | "dedup_required_preferred"
    반환: (FitResult 목록, bt_scores, guard_moves)

    SPEC §10-3: rescore는 aggregate() 100% 재사용 — 랭킹 로직 동일.
    """
    persona_dir = eval_root / persona
    tables_path = persona_dir / "matching_tables.json"
    pairwise_path = persona_dir / "pairwise_comparisons.json"
    ranking_path = persona_dir / "final_ranking.json"

    # 산출물 없으면 unavailable (재수집 X)
    if not tables_path.exists() or not ranking_path.exists():
        return [], {}, []

    tables_raw: dict[str, Any] = json.loads(tables_path.read_text(encoding="utf-8"))
    ranking_raw: list[dict[str, Any]] = json.loads(
        ranking_path.read_text(encoding="utf-8")
    )

    pairwise_raw: list[dict[str, Any]] = []
    if pairwise_path.exists():
        pw_data = json.loads(pairwise_path.read_text(encoding="utf-8"))
        if isinstance(pw_data, dict):
            pairwise_raw = pw_data.get("comparisons", [])
        else:
            pairwise_raw = pw_data

    dedup_flag = scoring_mode == "dedup_required_preferred"

    # MatchingTable 복원
    tables_by_id: dict[str, MatchingTable] = {
        jid: MatchingTable.model_validate(t) for jid, t in tables_raw.items()
    }

    # 저장 domain_ctx 복원
    domain_ctx: dict[str, dict[str, str]] = {
        r["job_id"]: {
            "domain_alignment": r.get("domain_alignment", "weak"),
            "role_family": r.get("role_family", "other"),
        }
        for r in ranking_raw
    }

    # fit 재계산 (단계 6 — LLM 없이)
    fits: dict[str, dict[str, Any]] = {}
    for jid, table in tables_by_id.items():
        alignment = domain_ctx.get(jid, {}).get("domain_alignment", "weak")
        fits[jid] = compute_fit(
            table, alignment=alignment, dedup_required_preferred=dedup_flag
        )

    # listwise 순서 복원 (저장 산출물 rank 기준)
    listwise = [r["job_id"] for r in sorted(ranking_raw, key=lambda r: r["rank"])]

    # pairwise 복원
    pairwise: list[PairwiseResult] = [
        PairwiseResult.model_validate(p) for p in pairwise_raw
    ]

    candidate_ids: set[str] = {p.job_a for p in pairwise} | {p.job_b for p in pairwise}

    # 실제 aggregate() 재사용 (랭킹 로직 100% 동일 — SPEC §10-3)
    return aggregate(
        jobs_by_id=tables_by_id,
        tables_by_id=tables_by_id,
        listwise=listwise,
        pairwise=pairwise,
        candidate_ids=candidate_ids,
        fits=fits,
        domain_ctx=domain_ctx,
        ranking_mode=ranking_mode,
    )
