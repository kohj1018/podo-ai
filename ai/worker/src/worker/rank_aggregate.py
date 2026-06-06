"""T-003/T-008: compute_fit + BT + aggregate (SPEC §4·§5).

상수·알고리즘은 SCORING_PIPELINE_SPEC.md §4·§5 그대로 이식.
검증된 캘리브레이션이므로 임의 변경 금지.

- compute_fit: MatchingTable + alignment → fit level 1~5 + coverage dict
- detect_required_preferred_dups: 실험 dedup (기본 OFF, SPEC §10-4 승격 4조건 미충족)
- bradley_terry: 순수 파이썬 MM 반복 (SPEC §5-1)
- elo: fallback (디버그용)
- aggregate: 3 랭킹 모드 + 도메인 우선순위 가드 (SPEC §5-2·§5-3)
"""

import re
from typing import Any

from core.models import (
    CORE_NATURES,
    FIT_LABELS,
    FitResult,
    MatchingTable,
    MatchRow,
    PairwiseResult,
)

# §4-1: 상호 교체 가능 툴링 카테고리 — 갭이 role-defining 아님 (SPEC §4-1)
# core.models에는 없으므로 worker 로컬 상수로 둔다 (compute_fit 전용)
MINOR_CATEGORIES: set[str] = {
    "state_management",
    "styling",
    "data_fetching",
    "build_tooling",
    "testing",
}

# ---------------------------------------------------------------------------
# §4-1. 가중치 상수 (SPEC §4-1 그대로 — 임의 변경 금지)
# ---------------------------------------------------------------------------

TYPE_WEIGHT: dict[str, float] = {
    "critical": 3.0,
    "required": 2.0,
    "preferred": 1.0,
    "optional": 0.5,
}
LEVEL_CREDIT: dict[str, float] = {
    "direct": 1.0,
    "adjacent": 0.6,
    "weak": 0.3,
    "missing": 0.0,
}
# prerequisite만 full weight. product_duty/context는 거의 안 셈, behavioral는 약간.
STATUS_WEIGHT: dict[str, float] = {
    "prerequisite": 1.0,
    "behavioral_preference": 0.4,
    "product_duty": 0.15,
    "context": 0.1,
}
# 가시적 도메인 거리 상한 (숨은 패널티 아님 — 리포트에 노출).
# mismatch는 compute_fit에서 role_evidence 유무에 따라 동적 처리.
DOMAIN_CAP: dict[str, int] = {"strong": 5, "adjacent": 4, "weak": 3, "mismatch": 2}


# ---------------------------------------------------------------------------
# §4-4. dedup 헬퍼 (실험 모드 — 기본 OFF)
# ---------------------------------------------------------------------------

# 명백한 필수 표현: 이 단어가 있으면 required → preferred 강등 금지
_MANDATORY_PATTERNS = re.compile(r"필수|반드시|must|필수적|필수로", re.IGNORECASE)

# 짧은/일반 텍스트 스킵 기준 (자 수)
_MIN_TEXT_LEN = 6


def _token_jaccard(a: str, b: str) -> float:
    """두 문자열의 토큰 Jaccard 유사도."""
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _normalize_text(text: str) -> str:
    """소문자 + 연속 공백 제거."""
    return re.sub(r"\s+", " ", text.lower().strip())


def detect_required_preferred_dups(
    rows: list[MatchRow],
) -> dict[int, dict[str, object]]:
    """required/critical ↔ preferred/optional 중복 행을 탐지해 cap에서만 제외.

    반환: {row_index: {duplicate_group_id, duplicate_resolution,
                       excluded_from_fit_cap, dedup_reason}}

    SPEC §4-4: 보수적 기준 — 교차 타입만, containment or Jaccard≥0.6,
               또는 (같은 category & Jaccard≥0.4). 짧은 텍스트 스킵.
               필수 표현 보유 시 유지(강등 X).
    """
    high_types = {"critical", "required"}
    low_types = {"preferred", "optional"}

    # 고우선 행, 저우선 행 인덱스 분리
    high_rows = [(i, r) for i, r in enumerate(rows) if r.requirement_type in high_types]
    low_rows = [(i, r) for i, r in enumerate(rows) if r.requirement_type in low_types]

    result: dict[int, dict[str, object]] = {}
    group_id = 0

    for h_idx, h_row in high_rows:
        h_text = _normalize_text(h_row.requirement_text)
        if len(h_text) < _MIN_TEXT_LEN:
            continue
        # 필수 표현이 있으면 강등 금지
        if _MANDATORY_PATTERNS.search(h_row.requirement_text):
            continue

        for l_idx, l_row in low_rows:
            l_text = _normalize_text(l_row.requirement_text)
            if len(l_text) < _MIN_TEXT_LEN:
                continue

            # containment 판정
            is_contained = h_text in l_text or l_text in h_text
            jaccard = _token_jaccard(h_text, l_text)
            same_cat = (
                h_row.requirement_category == l_row.requirement_category
                and h_row.requirement_category != "other"
            )
            is_dup = is_contained or jaccard >= 0.6 or (same_cat and jaccard >= 0.4)

            if not is_dup:
                continue

            group_id += 1
            gid = f"dup-{group_id}"
            reason = (
                "containment"
                if is_contained
                else f"jaccard={jaccard:.2f}"
                + (f" + same_category={h_row.requirement_category}" if same_cat else "")
            )
            # required/critical 행을 cap에서만 제외 (행 자체는 리포트에 유지).
            # compute_fit의 role-defining cap 카운터는 critical/required 행 인덱스만
            # excluded_cap으로 검사하므로 키는 반드시 h_idx여야 한다 — l_idx로 키잉하면
            # 카운터에 절대 안 걸려 dedup이 no-op이 된다.
            result[h_idx] = {
                "duplicate_group_id": gid,
                "duplicate_resolution": "excluded_from_cap",
                "excluded_from_fit_cap": True,
                "dedup_reason": reason,
                "paired_preferred_idx": l_idx,
            }
            break  # 하나의 high 행당 첫 preferred 트윈만 (프로토타입 동작)

    return result


# ---------------------------------------------------------------------------
# §4-2. compute_fit 본체 (SPEC §4-2 그대로 이식 — 임의 변경 금지)
# ---------------------------------------------------------------------------


def compute_fit(
    table: MatchingTable,
    alignment: str = "weak",
    dedup_required_preferred: bool = False,
) -> dict[str, object]:
    """MatchingTable + alignment → fit {level, label, coverage, strong, weak, ...}.

    alignment: 도메인 정렬 문자열 (domain_alignment 결과 — ai/core 소유)
    dedup_required_preferred: 실험 플래그 (기본 OFF=baseline 동일, SPEC §10-4)

    반환 dict 키:
        level, label, coverage{...}, strong[], weak[], preferred_gaps[],
        product_duties[], invalid[], risks[], dedup_audit[]
    """
    dedup_info = (
        detect_required_preferred_dups(table.rows) if dedup_required_preferred else {}
    )
    excluded_cap = {i for i, d in dedup_info.items() if d["excluded_from_fit_cap"]}

    earned = total = 0.0
    prereq_crit_unmet = prereq_req_unmet = 0
    prereq_crit_total = prereq_req_total = 0
    role_defining_crit_unmet = role_defining_req_unmet = 0
    role_evidence = 0
    crit_total = crit_met = req_total = req_met = 0
    strong, weak, pref_gaps, product_duties, invalid, risks = [], [], [], [], [], []

    for idx, row in enumerate(table.rows):
        w = TYPE_WEIGHT.get(row.requirement_type, 1.0) * STATUS_WEIGHT.get(
            row.prerequisite_status, 0.7
        )
        credit = LEVEL_CREDIT.get(row.match_level, 0.0)
        if row.confidence == "low":
            credit *= 0.7
        total += w
        earned += w * credit

        is_core = row.requirement_nature in CORE_NATURES
        is_prereq = row.prerequisite_status == "prerequisite"
        unmet = row.match_level in ("missing", "weak")

        # role_evidence: CORE prereq crit/req에 direct/adjacent 매칭 + 유효
        if (
            row.requirement_type in ("critical", "required")
            and is_prereq
            and is_core
            and row.match_level in ("direct", "adjacent")
            and not row.invalid_match
        ):
            role_evidence += 1

        is_minor = row.requirement_category in MINOR_CATEGORIES

        if row.requirement_type == "critical":
            crit_total += 1
            if not unmet:
                crit_met += 1
            if is_prereq:
                prereq_crit_total += 1
                if unmet:
                    prereq_crit_unmet += 1
                    if not is_minor and idx not in excluded_cap:
                        role_defining_crit_unmet += 1

        if row.requirement_type == "required":
            req_total += 1
            if not unmet:
                req_met += 1
            if is_prereq:
                prereq_req_total += 1
                if unmet:
                    prereq_req_unmet += 1
                    if not is_minor and idx not in excluded_cap:
                        role_defining_req_unmet += 1

        if (
            row.match_level == "direct"
            and row.confidence in ("high", "medium")
            and not row.invalid_match
        ):
            strong.append(row.requirement_text)

        if row.requirement_type in ("critical", "required") and unmet:
            tag = (
                f"[{row.requirement_type}/{row.requirement_nature}/{row.match_level}]"
                f" {row.requirement_text}"
            )
            if is_prereq:
                weak.append(tag)
            elif row.prerequisite_status in ("product_duty", "context"):
                product_duties.append(tag)

        if (
            row.requirement_type in ("preferred", "optional")
            and is_core
            and is_prereq
            and unmet
        ):
            pref_gaps.append(
                f"[{row.requirement_type}/{row.requirement_nature}/{row.match_level}]"
                f" {row.requirement_text}"
            )

        if row.invalid_match:
            invalid.append(row.requirement_text)

        note = (row.risk_note or row.verifier_note or "").strip()
        if note:
            risks.append(note)

    # §4-2 step 2: 비율 → 레벨
    ratio = earned / total if total > 0 else 0.0
    if ratio >= 0.80:
        level = 5
    elif ratio >= 0.62:
        level = 4
    elif ratio >= 0.42:
        level = 3
    elif ratio >= 0.22:
        level = 2
    else:
        level = 1

    # §4-2 step 3: cap 사다리
    crit_ratio = (
        (prereq_crit_total - prereq_crit_unmet) / prereq_crit_total
        if prereq_crit_total
        else 1.0
    )
    cap_reasons: list[str] = []
    role_defining_gap = (role_defining_crit_unmet > 0) or (role_defining_req_unmet > 0)

    if role_defining_crit_unmet >= 2:
        level = min(level, 2)
        cap_reasons.append(f"role-defining critical gaps x{role_defining_crit_unmet}")
    elif role_defining_crit_unmet == 1:
        level = min(level, 3)
        cap_reasons.append("role-defining critical gap")
    elif prereq_crit_unmet > 0:
        if crit_ratio >= 0.8:
            level = min(level, 4)
            cap_reasons.append(
                "minor critical (tooling) gap, criticals ≥80% met → max 4"
            )
        else:
            level = min(level, 3)
            cap_reasons.append("critical gaps <80% met → max 3")

    if role_defining_req_unmet >= 2:
        level = min(level, 2)
        cap_reasons.append(f"role-defining required gaps x{role_defining_req_unmet}")
    elif role_defining_req_unmet == 1:
        level = min(level, 3)
        cap_reasons.append("role-defining required gap")

    # §4-2 step 4: 도메인 거리 cap
    if alignment == "mismatch":
        # role_evidence>0 → cap 2, 없으면 cap 1
        domain_cap = 2 if role_evidence > 0 else 1
    else:
        domain_cap = DOMAIN_CAP.get(alignment, 5)

    if domain_cap < level:
        cap_reasons.append(f"domain {alignment} → max {domain_cap}")
    level = min(level, domain_cap)

    return {
        "level": level,
        "label": FIT_LABELS[level],
        "coverage": {
            "critical_met": crit_met,
            "critical_total": crit_total,
            "critical_met_count": prereq_crit_total - prereq_crit_unmet,
            "critical_total_count": prereq_crit_total,
            "required_met": req_met,
            "required_total": req_total,
            "role_defining_gap": role_defining_gap,
            "cap_reason": "; ".join(cap_reasons) or "no cap",
            "prereq_critical_unmet": prereq_crit_unmet,
            "prereq_required_unmet": prereq_req_unmet,
            "role_evidence_matches": role_evidence,
            "domain_alignment": alignment,
            "domain_cap": domain_cap,
            "weighted_earned": round(earned, 2),
            "weighted_total": round(total, 2),
        },
        "strong": strong[:8],
        "weak": weak[:10],
        "preferred_gaps": pref_gaps[:10],
        "product_duties": product_duties[:10],
        "invalid": invalid[:10],
        "risks": risks[:8],
        "dedup_audit": list(dedup_info.values()),
    }


# ---------------------------------------------------------------------------
# §5-1. Bradley-Terry (순수 파이썬 MM 반복, SPEC §5-1 그대로 이식)
# ---------------------------------------------------------------------------

# §5-2: 정렬 모드 상수
RANKING_MODES: tuple[str, ...] = ("bt_primary", "fit_primary", "domain_fit_bt")

# §5-2: 도메인 tier → 정렬 키 숫자.
# SSOT per ADR-104 — rerank_listwise·pipeline·eval이 import. 복제 금지(REV-M1-002).
DOM_RANK: dict[str, int] = {"strong": 3, "adjacent": 2, "weak": 1, "mismatch": 0}


def bradley_terry(
    ids: list[str],
    results: list[PairwiseResult],
    iters: int = 300,
    prior: float = 0.5,
) -> dict[str, float]:
    """pairwise 결과로 상대 적합도 강도(BT 점수)를 추정한다.

    평균 강도를 1로 정규화. n==0→{}, n==1→{id:1.0}.
    prior(0.5)로 비교 그래프를 연결 유지해 수렴 보장 (SPEC §5-1).
    """
    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: 1.0}

    idx = {jid: i for i, jid in enumerate(ids)}
    wins = [[0.0] * n for _ in range(n)]

    for r in results:
        if r.job_a not in idx or r.job_b not in idx:
            continue
        i, j = idx[r.job_a], idx[r.job_b]
        if r.outcome == r.job_a:
            wins[i][j] += 1.0
        elif r.outcome == r.job_b:
            wins[j][i] += 1.0
        else:
            wins[i][j] += 0.5
            wins[j][i] += 0.5

    for i in range(n):
        for j in range(n):
            if i != j:
                wins[i][j] += prior

    total_wins = [sum(wins[i]) for i in range(n)]
    p = [1.0] * n

    for _ in range(iters):
        new_p = [0.0] * n
        for i in range(n):
            denom = sum(
                (wins[i][j] + wins[j][i]) / (p[i] + p[j]) for j in range(n) if i != j
            )
            new_p[i] = (total_wins[i] / denom) if denom > 0 else p[i]
        s = sum(new_p)
        if s > 0:
            new_p = [x * n / s for x in new_p]
        if max(abs(new_p[i] - p[i]) for i in range(n)) < 1e-9:
            p = new_p
            break
        p = new_p

    return {ids[i]: p[i] for i in range(n)}


def elo(
    ids: list[str],
    results: list[PairwiseResult],
    k: float = 32.0,
) -> dict[str, float]:
    """BT fallback — Elo 방식 강도 추정 (디버그용). SPEC §5-1."""
    ratings = {jid: 1500.0 for jid in ids}
    for r in results:
        if r.job_a not in ratings or r.job_b not in ratings:
            continue
        ra, rb = ratings[r.job_a], ratings[r.job_b]
        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        eb = 1.0 - ea
        if r.outcome == r.job_a:
            sa, sb = 1.0, 0.0
        elif r.outcome == r.job_b:
            sa, sb = 0.0, 1.0
        else:
            sa = sb = 0.5
        ratings[r.job_a] = ra + k * (sa - ea)
        ratings[r.job_b] = rb + k * (sb - eb)
    return ratings


# ---------------------------------------------------------------------------
# §5-2·§5-3. aggregate (3 랭킹 모드 + 도메인 우선순위 가드)
# ---------------------------------------------------------------------------


def aggregate(
    jobs_by_id: dict[str, MatchingTable],
    tables_by_id: dict[str, MatchingTable],
    listwise: list[str],
    pairwise: list[PairwiseResult],
    candidate_ids: set[str],
    fits: dict[str, dict[str, Any]],
    domain_ctx: dict[str, dict[str, str]],
    ranking_mode: str = "domain_fit_bt",
) -> tuple[list[FitResult], dict[str, float], list[dict[str, Any]]]:
    """3 랭킹 모드 정렬 + 도메인 우선순위 가드 적용.

    Args:
        jobs_by_id: job_id → MatchingTable (메타 소스)
        tables_by_id: job_id → MatchingTable (현재 jobs_by_id와 동일 계약)
        listwise: listwise 순위 정렬된 job_id 목록
        pairwise: pairwise 비교 결과 목록
        candidate_ids: BT 계산 대상 job_id 집합
        fits: job_id → compute_fit 결과 dict (단계 6 사전 계산)
        domain_ctx: job_id → {domain_alignment, role_family}
        ranking_mode: "domain_fit_bt" | "fit_primary" | "bt_primary"

    Returns:
        (List[FitResult], bt_scores dict, guard_moves list)
    """
    all_ids = list(listwise)
    # listwise에 없는 job_id 보완 (fits에 있는 것 기준)
    for jid in fits:
        if jid not in all_ids:
            all_ids.append(jid)

    # §5-1: BT 계산 — candidate_ids ≥ 2 + pairwise 있을 때만
    top_ids = [jid for jid in all_ids if jid in candidate_ids]
    bt_scores: dict[str, float]
    if len(top_ids) >= 2 and pairwise:
        bt_scores = bradley_terry(top_ids, pairwise)
    else:
        bt_scores = {}

    lw_index = {jid: i for i, jid in enumerate(all_ids)}

    def _dom(jid: str) -> str:
        return domain_ctx.get(jid, {}).get("domain_alignment", "weak")

    def _fit(jid: str) -> int:
        return int(fits.get(jid, {}).get("level", 1))

    def _bt(jid: str) -> float:
        return round(bt_scores.get(jid, 0.0), 6)

    def _lw(jid: str) -> int:
        return lw_index.get(jid, len(all_ids))

    # §5-2: 정렬 키별 순서 산출
    if ranking_mode == "domain_fit_bt":
        sorted_ids = sorted(
            all_ids,
            key=lambda j: (-DOM_RANK.get(_dom(j), 1), -_fit(j), -_bt(j), _lw(j), j),
        )
    elif ranking_mode == "fit_primary":
        sorted_ids = sorted(
            all_ids,
            key=lambda j: (-_fit(j), -DOM_RANK.get(_dom(j), 1), -_bt(j), _lw(j), j),
        )
    else:
        # bt_primary: BT 비교 집합은 BT 키, 나머지는 fit/dom/lw 키
        in_bt = set(top_ids)
        sorted_ids = sorted(
            all_ids,
            key=lambda j: (
                0 if j in in_bt else 1,
                -_bt(j) if j in in_bt else -_fit(j),
                -_fit(j) if j in in_bt else -DOM_RANK.get(_dom(j), 1),
                -DOM_RANK.get(_dom(j), 1) if j in in_bt else _lw(j),
                _lw(j),
                j,
            ),
        )

    # §5-3: 도메인 우선순위 가드 — 안정 분할
    non_mismatch = [j for j in sorted_ids if _dom(j) != "mismatch"]
    mismatch_list = [j for j in sorted_ids if _dom(j) == "mismatch"]
    final_ids = non_mismatch + mismatch_list

    # guard_moves 기록
    guard_moves: list[dict[str, Any]] = []
    old_rank = {jid: i for i, jid in enumerate(sorted_ids)}
    new_rank = {jid: i for i, jid in enumerate(final_ids)}
    for jid in mismatch_list:
        old_r = old_rank[jid]
        new_r = new_rank[jid]
        if new_r != old_r:
            guard_moves.append(
                {
                    "job_id": jid,
                    "old_rank": old_r + 1,
                    "new_rank": new_r + 1,
                    "reason": "domain_priority_guard",
                }
            )

    # FitResult 조립
    fit_results: list[FitResult] = []
    for rank_idx, jid in enumerate(final_ids):
        table = tables_by_id.get(jid) or jobs_by_id.get(jid)
        fit_data = fits.get(jid, {})
        ctx = domain_ctx.get(jid, {})
        # model_validate(dict): role_family/domain_alignment 등 str→Literal을 clamp가
        # coerce (strict 정합 — ADR-102 D3, T-006 MatchRow와 동일 idiom).
        fit_results.append(
            FitResult.model_validate(
                {
                    "job_id": jid,
                    "company": table.company if table else "",
                    "title": table.title if table else "",
                    "role_family": ctx.get("role_family", "other"),
                    "domain_alignment": ctx.get("domain_alignment", "weak"),
                    "rank": rank_idx + 1,
                    "fit_level": fit_data.get("level", 1),
                    "fit_label": fit_data.get("label", FIT_LABELS[1]),
                    "bt_score": bt_scores.get(jid, 0.0),
                    "coverage": fit_data.get("coverage", {}),
                    "strong_matches": fit_data.get("strong", []),
                    "weak_or_missing": fit_data.get("weak", []),
                    "preferred_gaps": fit_data.get("preferred_gaps", []),
                    "product_duties": fit_data.get("product_duties", []),
                    "invalid_matches": fit_data.get("invalid", []),
                    "risk_notes": fit_data.get("risks", []),
                }
            )
        )

    return fit_results, bt_scores, guard_moves
