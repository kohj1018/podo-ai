# 스코어링 파이프라인 스펙 (Scorer · Collector · Eval 알고리즘 SSOT)

## 0. Status
draft

> 모드: Reference (알고리즘·파이프라인·프롬프트 SSOT). Living — 스코어링 의미 변경 시 갱신.
> 상위: [ARCHITECTURE_OVERVIEW](ARCHITECTURE_OVERVIEW.md) (§3 Scorer/Collector/Feed, §3-1 결정론·grounding 경계, §3-2 폴리글랏 계약), [PROJECT_CHARTER](../10-charter/PROJECT_CHARTER.md) (§6 GS-1·GS-2·GS-3), [ADR-100](../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선, D3 결정론 캐시).
> 본 문서는 **Scorer 모듈의 알고리즘 본체**를 명세한다. `/implement-workitem`(builder)이 이 스펙을 *기계적으로 재현*하는 SSOT다 — 빌더는 본 문서의 상수·정렬키·프롬프트를 거의 그대로 옮긴다(검증된 캘리브레이션이므로 임의 변경 금지).

---

## 1. 목적·범위 + 논리 모듈 → 실행 단위 매핑

이 시스템의 본질: 한 후보(이력서)에 대해 N개의 JD를 받아 **적합도(fit) 순으로 정렬**하고, 각 공고마다 *왜 그 순위인지*(충족/미충족 요건, 추출형 인용, cap 사유, fit 1~5)를 설명하는 **결정적·감사 가능한 랭커**다. **합격확률/퍼센트를 출력하지 않는다**(Charter §5 비목표). fit은 확률이 아니라 *검증된 요구 커버리지 기반의 보수적 레벨*이다.

ARCH §3의 논리 모듈(Collector/Scorer/Feed)을 §3-2 실행 단위에 매핑하면, 본 스펙이 다루는 알고리즘은 다음 위치로 이식된다:

| 알고리즘 영역 | 실행 단위 (ARCH §3-2) | 비고 |
|--------------|----------------------|------|
| 공유 데이터 계약 (Pydantic 모델·enum·가중치 상수) + `domain_alignment`(role_family→tier) | `ai/core` | worker·eval·crawler 공통 의존 (순환 import 방지). **`domain_alignment`·`ROLE_FAMILY_TO_DOMAINS`는 crawler(선택)와 worker(스코어링)가 함께 쓰므로 core에 둔다** — crawler→worker import는 의존 방향 위반(ARCH §3-1) |
| 추출·매칭·검증·compute_fit·BT·aggregate·도메인 가드·프롬프트·LLM 게이트웨이·캐시 | `ai/worker` (Scorer) | **결정론·grounding 경계 소유** (§3-1). 알고리즘 본체. (`domain_alignment` 함수 자체는 core에서 import) |
| 공고 수집(토스·당근) + 도메인 인지 선택 | `crawler` (Collector) | `job_postings` upsert. httpx 정적 fetch |
| 불변식 회귀 · 멀티-페르소나 진단 · 골든 페어 정확도 · 스코어링 재채점(ablation) | `ai/eval` | GS-1 결정성·GS-2 사실성·GS-3 τ 프록시 측정 경로 |

> **스코어링 결정론 경계(§3-1) 직결:** compute_fit·aggregate·BT는 *순수 결정적 파이썬*이다(LLM 호출 없음, scipy/playwright 불필요). LLM이 개입하는 단계(추출·매칭·검증·listwise·pairwise)는 모두 캐시·재시도·구조화 출력 검증으로 감싼다 — 동일 입력 + 동일 캐시 = 동일 출력(GS-1).

---

## 2. 파이프라인 12단계 (stage-by-stage)

```
1. 이력서 evidence 추출  (LLM + 결정적 Skills 항목 보강)
2. JD 요구사항 구조화      (LLM — prerequisite vs product_duty 분류)
3. 도메인 정렬 컨텍스트     (결정적 — role_family vs 사용자 도메인 → strong/adjacent/weak/mismatch)
4. 요구↔근거 매칭          (LLM — evidence_id 선택만; 인용은 코드가 verbatim 채움)
5. 매칭 검증               (결정적 추출형 체크 + 보수적 LLM verifier — 강등만)
6. compute_fit (1~5 + caps)(결정적 — 단계 4·5 산출만으로 계산, 모든 다운스트림이 공유)
7. listwise 재랭킹          (LLM — 압축 매칭표만; 누락/중복 보정)
8. pairwise 후보 집합 구성  (결정적 — listwise top-K + fit≥4 + strong 도메인 구제)
9. pairwise 비교            (LLM — A/B·B/A 순서 교차)
10. Bradley-Terry 집계      (결정적 순수 파이썬 MM 반복)
11. aggregate(랭킹 모드) + 도메인 우선순위 가드 (결정적 정렬)
12. 리포트(JSON + Markdown) (결정적 직렬화)
```

**오케스트레이션 핵심 규율 (이식 시 반드시 보존):**
- **compute_fit은 단계 6에서 *한 번* 계산하고 단계 7·8·11에서 *공유*한다.** 재계산 금지 — 다운스트림 결정의 일관성 보장.
- 단계 4의 매칭은 **evidence_id만 선택**하고, 인용 텍스트는 *코드*가 evidence 항목의 `exact_quote`에서 verbatim 복사한다(구성상 추출형 — 단계 5에서 떨궈낼 LLM 패러프레이즈 인용이 애초에 없음). GS-2 grounding 경계의 1차 보증.
- 단계 5 verifier는 **강등(낮추기)만** 한다 — 절대 올리지 않는다(보수성).
- 단계 11 도메인 우선순위 가드는 **모든 랭킹 모드에서 적용**되는 하드 규칙: mismatch(marketing/design/product) 역할은 어떤 non-mismatch(엔지니어링) 역할보다 위로 올 수 없다.

**런타임 분담 (§3-2):** 단계 1·2·4·5·7·9는 LLM 호출(Worker가 OpenAI SDK로, temperature=0/seed/버전 핀). 단계 3·6·8·10·11·12는 순수 결정적(Worker). 수집은 별도 Collector(crawler).

---

## 3. 데이터 계약 (`ai/core` — Pydantic 모델·enum·가중치)

> **가장 먼저 이식할 것.** 모든 단계가 이 계약 위에서 돈다. 아래 enum 분류가 알고리즘 정확도를 만든다(특히 `prerequisite_status`·`requirement_nature`·`requirement_category`).

### 3-1. enum / 분류 상수 (그대로 이식)

```python
EVIDENCE_TYPES = {"work_experience", "project", "education", "award", "activity", "skills", "other"}
STRENGTHS = {"strong", "medium", "weak"}
REQ_TYPES = {"critical", "required", "preferred", "optional"}
MATCH_LEVELS = {"direct", "adjacent", "weak", "missing"}
CONFIDENCES = {"high", "medium", "low"}

ROLE_FAMILIES = {
    "frontend", "backend", "fullstack", "android", "ios", "data", "ml_ai",
    "devops_infra", "security", "product", "marketing", "design", "other",
}
REQ_NATURES = {
    "technical", "domain", "experience_level", "behavioral",
    "language", "location", "employment", "other",
}
REQ_ORIGINS = {"explicit_requirement", "responsibility_inferred", "product_context", "company_value"}
# prerequisite        = 입사 전 이미 보유해야 함 (fit을 강하게 cap)
# product_duty        = 입사 후 수행할 업무 (fit을 cap하면 안 됨)
# context             = 도메인/제품 배경 (정보용)
# behavioral_preference = soft trait (강하게 cap 금지)
PREREQ_STATUSES = {"prerequisite", "product_duty", "context", "behavioral_preference"}
REQ_CATEGORIES = {
    "state_management", "styling", "data_fetching", "build_tooling", "testing",
    "framework", "language", "other",
}
ALT_MATCH_POLICIES = {"exact_or_same_category", "exact_only"}
# fit을 의미있게 gate하는 nature (cap을 구동)
CORE_NATURES = {"technical", "domain", "experience_level", "language"}
DOMAIN_ALIGNMENTS = {"strong", "adjacent", "weak", "mismatch"}

# JD role_family → 그것이 "속하는" 도메인 토큰 (사용자 프로파일 대비 정렬 산출 근거)
ROLE_FAMILY_TO_DOMAINS = {
    "frontend": {"frontend", "web"},
    "backend": {"backend"},
    "fullstack": {"fullstack", "frontend", "backend", "web"},
    "android": {"mobile", "android"},
    "ios": {"mobile", "ios"},
    "data": {"data"},
    "ml_ai": {"ml_ai", "ai"},
    "devops_infra": {"devops", "cloud", "infra"},
    "security": {"security"},
    "product": {"product"},
    "marketing": {"marketing"},
    "design": {"design"},
    "other": {"other"},
}

MATCH_SEVERITY = {"missing": 0, "weak": 1, "adjacent": 2, "direct": 3}
SEVERITY_TO_LEVEL = {v: k for k, v in MATCH_SEVERITY.items()}
CONF_RANK = {"low": 0, "medium": 1, "high": 2}

FIT_LABELS = {
    5: "매우 높음: 강력 추천",
    4: "높음: 추천",
    3: "보통: 검토 가능",
    2: "낮음: 아쉬움",
    1: "매우 낮음: 비추천",
}
```

보조 헬퍼: `clamp(value, allowed, default)`(소문자 strip 후 allowed 집합에 없으면 default), `as_list(v)`(콤마 분리 문자열/리스트/None → `List[str]`). 모든 Pydantic 모델은 enum 필드에 `field_validator(mode="before")`로 `clamp`을 적용해 *허용값 외 입력을 안전하게 default로 클램프*한다(LLM 오출력 방어).

### 3-2. 모델 (필드 요지 — 전체는 코드로 이식)

- **`EvidenceItem`**: `evidence_id, title, source_section, exact_quote, normalized_summary, skills[], domain[], evidence_type, strength, recency`. `exact_quote`는 이력서 verbatim span(추출형의 근원).
- **`Resume`**: `raw_text, evidence[], primary_domains[], secondary_domains[]`.
- **`Requirement`**: `requirement_id, requirement_text, requirement_type(default required), requirement_nature(other), requirement_origin(explicit_requirement), prerequisite_status(prerequisite), alternatives[](OR 그룹), requirement_category(other), alternative_match_policy(exact_or_same_category)`.
- **`JobPosting`**: `job_id, company, title, url, role_family(other), employment_type, location, team, responsibilities[], requirements[], preferred_requirements[], hard_constraints[], seniority, tech_stack[], raw_text`. 메서드 `all_requirements() = requirements + preferred_requirements`.
- **`MatchRow`**: Requirement 필드 일체 + `matched_evidence_ids[], evidence_quotes[], evidence_source_sections[], match_level(missing), confidence(low), explanation, risk_note` + verifier/파이프라인 필드 `extractive_ok(Optional[bool]), downgraded(False), invalid_match(False), rematched(False), verifier_note`.
- **`MatchingTable`**: `job_id, company, title, rows[MatchRow]`.
- **`PairwiseResult`**: `job_a, job_b, ab_winner(tie), ba_winner(tie), agreed(False), outcome(tie), confidence(low), reason_ab, reason_ba`.
- **`FitResult`** (최종 출력 계약): `job_id, company, title, url, role_family, domain_alignment(weak), domain_alignment_reason, rank, fit_level(1), fit_label, bt_score(0.0), listwise_reason, coverage{}, strong_matches[], weak_or_missing[], preferred_gaps[], product_duties[], invalid_matches[], risk_notes[]`.

---

## 4. `compute_fit` — 1~5 산출 + cap 사다리 (Scorer 코어, 결정적)

> **알고리즘의 심장.** 입력: `MatchingTable` + `alignment`(도메인 정렬 문자열) + `dedup_required_preferred`(실험 플래그, 기본 OFF=baseline과 바이트 동일). 출력: `{level, label, coverage{...}, strong[], weak[], preferred_gaps[], product_duties[], invalid[], risks[], dedup_audit[]}`. **여기 수치는 fit 지표이며 절대 합격확률/% 아님.**

### 4-1. 가중치 상수 (그대로 이식)

```python
TYPE_WEIGHT  = {"critical": 3.0, "required": 2.0, "preferred": 1.0, "optional": 0.5}
LEVEL_CREDIT = {"direct": 1.0, "adjacent": 0.6, "weak": 0.3, "missing": 0.0}
# prerequisite만 full weight. product duty/context는 거의 안 셈, behavioral는 약간.
STATUS_WEIGHT = {"prerequisite": 1.0, "behavioral_preference": 0.4, "product_duty": 0.15, "context": 0.1}
# 가시적 도메인 거리 상한 (숨은 패널티 아님 — 리포트에 노출). mismatch는 compute_fit에서 동적 처리.
DOMAIN_CAP = {"strong": 5, "adjacent": 4, "weak": 3, "mismatch": 2}
# 상호 교체 가능 툴링 카테고리 — 여기 갭은 "마이너/툴링"이지 role-defining 갭이 아님.
MINOR_CATEGORIES = {"state_management", "styling", "data_fetching", "build_tooling", "testing"}
```

### 4-2. 산출 절차 (그대로 이식)

1. **행별 가중치** `w = TYPE_WEIGHT[type] × STATUS_WEIGHT[prerequisite_status]`. **credit** `= LEVEL_CREDIT[match_level]`, 단 `confidence == "low"`면 `credit *= 0.7`. `total += w`, `earned += w * credit`.
2. **비율 → 레벨:** `ratio = earned/total` → `≥0.80→5, ≥0.62→4, ≥0.42→3, ≥0.22→2, else 1`.
3. **cap 사다리** (prerequisite 미충족만 cap; product_duty/context/behavioral은 절대 cap 안 함). `unmet = match_level in (missing, weak)`. `is_minor = requirement_category in MINOR_CATEGORIES`. role-defining = `not is_minor`:
   - role-defining critical 미충족 `≥2 → cap 2`; `==1 → cap 3`.
   - 그 외(마이너 critical만 남음): `crit_ratio≥0.8 → cap 4`, else `cap 3`.
   - role-defining required 미충족 `≥2 → cap 2`; `==1 → cap 3`. (마이너 required 갭은 하드 cap 없음 — 이미 비율을 낮춤.)
   - *주의: critical과 required를 사실상 동급으로 cap하는 이 대칭이 골든 페어가 드러낸 캘리브레이션 약점이다(§10-4 / dedup 실험).*
4. **도메인 거리 cap:** `mismatch`면 `role_evidence>0 ? cap 2 : cap 1` (role_evidence = CORE-nature prerequisite critical/required에 direct/adjacent 매칭이 있고 invalid 아님인 행 수). 그 외 `DOMAIN_CAP[alignment]`. `level = min(level, domain_cap)`.

코어 함수 전문(거의 그대로 이식):

```python
def compute_fit(table, alignment="weak", dedup_required_preferred=False) -> dict:
    dedup_info = detect_required_preferred_dups(table.rows) if dedup_required_preferred else {}
    excluded_cap = {i for i, d in dedup_info.items() if d["excluded_from_fit_cap"]}
    earned = total = 0.0
    prereq_crit_unmet = prereq_req_unmet = 0
    prereq_crit_total = prereq_req_total = 0
    role_defining_crit_unmet = role_defining_req_unmet = 0
    role_evidence = 0
    crit_total = crit_met = req_total = req_met = 0
    strong, weak, pref_gaps, product_duties, invalid, risks = [], [], [], [], [], []
    for idx, row in enumerate(table.rows):
        w = TYPE_WEIGHT.get(row.requirement_type, 1.0) * STATUS_WEIGHT.get(row.prerequisite_status, 0.7)
        credit = LEVEL_CREDIT.get(row.match_level, 0.0)
        if row.confidence == "low":
            credit *= 0.7
        total += w; earned += w * credit
        is_core = row.requirement_nature in CORE_NATURES
        is_prereq = row.prerequisite_status == "prerequisite"
        unmet = row.match_level in ("missing", "weak")
        if (row.requirement_type in ("critical", "required") and is_prereq and is_core
                and row.match_level in ("direct", "adjacent") and not row.invalid_match):
            role_evidence += 1
        is_minor = row.requirement_category in MINOR_CATEGORIES
        if row.requirement_type == "critical":
            crit_total += 1
            if not unmet: crit_met += 1
            if is_prereq:
                prereq_crit_total += 1
                if unmet:
                    prereq_crit_unmet += 1
                    if not is_minor and idx not in excluded_cap: role_defining_crit_unmet += 1
        if row.requirement_type == "required":
            req_total += 1
            if not unmet: req_met += 1
            if is_prereq:
                prereq_req_total += 1
                if unmet:
                    prereq_req_unmet += 1
                    if not is_minor and idx not in excluded_cap: role_defining_req_unmet += 1
        if row.match_level == "direct" and row.confidence in ("high", "medium") and not row.invalid_match:
            strong.append(row.requirement_text)
        if row.requirement_type in ("critical", "required") and unmet:
            tag = f"[{row.requirement_type}/{row.requirement_nature}/{row.match_level}] {row.requirement_text}"
            if is_prereq: weak.append(tag)
            elif row.prerequisite_status in ("product_duty", "context"): product_duties.append(tag)
        if row.requirement_type in ("preferred", "optional") and is_core and is_prereq and unmet:
            pref_gaps.append(f"[{row.requirement_type}/{row.requirement_nature}/{row.match_level}] {row.requirement_text}")
        if row.invalid_match: invalid.append(row.requirement_text)
        note = (row.risk_note or row.verifier_note or "").strip()
        if note: risks.append(note)

    ratio = earned / total if total > 0 else 0.0
    if   ratio >= 0.80: level = 5
    elif ratio >= 0.62: level = 4
    elif ratio >= 0.42: level = 3
    elif ratio >= 0.22: level = 2
    else: level = 1

    crit_ratio = (prereq_crit_total - prereq_crit_unmet) / prereq_crit_total if prereq_crit_total else 1.0
    cap_reasons = []
    role_defining_gap = (role_defining_crit_unmet > 0) or (role_defining_req_unmet > 0)
    if role_defining_crit_unmet >= 2:
        level = min(level, 2); cap_reasons.append(f"role-defining critical gaps x{role_defining_crit_unmet}")
    elif role_defining_crit_unmet == 1:
        level = min(level, 3); cap_reasons.append("role-defining critical gap")
    elif prereq_crit_unmet > 0:
        if crit_ratio >= 0.8: level = min(level, 4); cap_reasons.append("minor critical (tooling) gap, criticals ≥80% met → max 4")
        else: level = min(level, 3); cap_reasons.append("critical gaps <80% met → max 3")
    if role_defining_req_unmet >= 2:
        level = min(level, 2); cap_reasons.append(f"role-defining required gaps x{role_defining_req_unmet}")
    elif role_defining_req_unmet == 1:
        level = min(level, 3); cap_reasons.append("role-defining required gap")

    if alignment == "mismatch":
        domain_cap = 2 if role_evidence > 0 else 1
    else:
        domain_cap = DOMAIN_CAP.get(alignment, 5)
    if domain_cap < level: cap_reasons.append(f"domain {alignment} → max {domain_cap}")
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
```

### 4-3. `domain_alignment` (결정적)

> **위치: `ai/core`** (NOT `ai/worker`). `ROLE_FAMILY_TO_DOMAINS`(§3-1)와 함께 core에 둔다 — worker(스코어링)와 crawler(도메인 인지 선택, §9-4)가 *둘 다* 호출하므로. crawler가 worker를 import하면 의존 방향 위반(ARCH §3-1). compute_fit은 이 함수의 *결과 문자열*(alignment)만 인자로 받는다.

```python
def domain_alignment(role_family, primary, secondary):
    primary = {d.lower() for d in primary}; secondary = {d.lower() for d in secondary}
    tokens = ROLE_FAMILY_TO_DOMAINS.get(role_family, {role_family})
    if tokens & primary:   return "strong",   f"role_family '{role_family}'가 사용자 주력 도메인과 직접 일치"
    if tokens & secondary: return "adjacent", f"role_family '{role_family}'가 사용자 보조 도메인과 인접"
    if role_family in {"marketing", "design", "product"}:
                           return "mismatch", f"role_family '{role_family}'는 사용자 엔지니어링 도메인과 불일치"
    return "weak", f"role_family '{role_family}'가 사용자 도메인과 약하게만 관련됨"
```

### 4-4. dedup (실험 스코어링 모드 — 기본 OFF)

`detect_required_preferred_dups(rows)`: required/critical 행이 *같은 역량*을 서술하는 preferred/optional 행과 **중복**될 때 매핑. **보수적**: 교차 타입만(required/critical ↔ preferred/optional), 텍스트 정규화 후 **containment** 또는 **token Jaccard ≥0.6**, 또는 (같은 requirement_category & Jaccard ≥0.4)일 때만 중복 판정. 짧은/일반 텍스트(<6자) 스킵. 명백한 필수 표현(`필수/반드시/must/필수적/필수로`)이 있으면 유지(강등 X). 강등 대상은 **cap 계산에서만 제외**(가중 비율·리포트 행은 그대로 — 증거 삭제 없음). 처리 내역은 `dedup_audit`(duplicate_group_id / duplicate_resolution / excluded_from_fit_cap / dedup_reason)로 감사. — 이식은 하되 **기본값 승격 금지**(§10-4 승격 4조건 미충족, 실험 플래그 유지).

---

## 5. Bradley-Terry + aggregate(3 모드) + 도메인 우선순위 가드 (결정적)

### 5-1. Bradley-Terry (순수 파이썬 MM 반복, scipy 불필요)

pairwise A/B·B/A 결과로 **상대 적합도 강도**를 추정(합격확률 아님). 작은 대칭 prior(`0.5`)로 비교 그래프를 연결 유지해 수렴 보장. `iters=300, prior=0.5`. 평균 강도를 1로 정규화. `n==0→{}`, `n==1→{id:1.0}`. (대안 `elo(ids, results, k=32.0)` fallback 구현도 함께 이식 — 디버그용.)

```python
def bradley_terry(ids, results, iters=300, prior=0.5) -> dict:
    n = len(ids)
    if n == 0: return {}
    if n == 1: return {ids[0]: 1.0}
    idx = {jid: i for i, jid in enumerate(ids)}
    wins = [[0.0]*n for _ in range(n)]
    for r in results:
        if r.job_a not in idx or r.job_b not in idx: continue
        i, j = idx[r.job_a], idx[r.job_b]
        if   r.outcome == r.job_a: wins[i][j] += 1.0
        elif r.outcome == r.job_b: wins[j][i] += 1.0
        else: wins[i][j] += 0.5; wins[j][i] += 0.5
    for i in range(n):
        for j in range(n):
            if i != j: wins[i][j] += prior
    total_wins = [sum(wins[i]) for i in range(n)]
    p = [1.0]*n
    for _ in range(iters):
        new_p = [0.0]*n
        for i in range(n):
            denom = sum((wins[i][j]+wins[j][i])/(p[i]+p[j]) for j in range(n) if i != j)
            new_p[i] = (total_wins[i]/denom) if denom > 0 else p[i]
        s = sum(new_p)
        if s > 0: new_p = [x*n/s for x in new_p]
        if max(abs(new_p[i]-p[i]) for i in range(n)) < 1e-9: p = new_p; break
        p = new_p
    return {ids[i]: p[i] for i in range(n)}
```

### 5-2. 랭킹 모드 정렬 키 (그대로 이식 — 업스트림 신호는 모드 무관 동일, 최종 순서만 다름)

`RANKING_MODES = ("bt_primary", "fit_primary", "domain_fit_bt")`. `DOM_RANK = {strong:3, adjacent:2, weak:1, mismatch:0}`. `lw_index` = listwise 순위 인덱스. BT는 `round(bt, 6)`로 동점 안정화.

- **`domain_fit_bt`** (기본·권장 제품 정렬): `key = (-domrank, -fit, -bt, lw_index, jid)`. 도메인 tier 먼저, 같은 tier 안에서 fit 내림차순(순위↔fit 일치), BT/pairwise는 같은 tier·같은 fit의 타이브레이커.
- **`fit_primary`** (fit 정렬 UI 옵션): `key = (-fit, -domrank, -bt, lw_index, jid)`. fit 1차 — adjacent가 strong 위로 올 수 있어 기본 비권장.
- **`bt_primary`** (BT 우선·디버그/연구): 비교집합 `(-bt, -fit, -domrank, lw, jid)` + 나머지 `(-fit, -domrank, lw, jid)`. v0 원래 기본값.

### 5-3. 도메인 우선순위 가드 (모든 모드 적용 — 하드 규칙, 반드시 이식)

정렬 후 안정 분할: `final = non_mismatch + mismatch`. mismatch 역할은 어떤 non-mismatch 위로도 못 온다. 이동된 항목은 `guard_moves`(job_id, old_rank, new_rank, reason="domain_priority_guard")로 기록해 리포트·JSON에 노출.

`aggregate(jobs_by_id, tables_by_id, listwise, pairwise, candidate_ids, fits, domain_ctx, ranking_mode="domain_fit_bt")` → `(List[FitResult], bt_scores, guard_moves)`. `candidate_ids` = pairwise 비교를 받은 집합(BT 대상). `fits` = 사전 계산된 compute_fit 결과(단계 6 공유). BT는 `len(top_ids)>=2 and pairwise`일 때만 계산, 아니면 0.

---

## 6. 매칭(단계 4) + 검증(단계 5) — 신뢰 레이어 (절대 생략 금지)

### 6-1. 매칭 + rematch (`matching.py` 개념)

- LLM은 **evidence_id만** 선택(프롬프트 `requirement_evidence_match`). 코드가 `_resolve_evidence`로 존재하는 id만 남기고 `evidence_quotes`를 evidence의 `exact_quote`에서 verbatim 채움(**구성상 추출형**). 존재하지 않는 id는 risk_note에 기록.
- 모든 요구사항당 정확히 1행 보장: 모델이 누락한 행은 `missing/low`로 backfill하고 *권위 메타데이터*(type/nature/origin/prerequisite_status/alternatives/category/policy)는 Requirement에서 덮어쓴다.
- **rematch 1회 재시도**(`rematch_evidence` 프롬프트): 행이 (a) 매칭을 주장했으나 유효 근거 0이거나, (b) critical/required인데 same-category 그룹(`alternatives` 또는 `requirement_category in GROUP_CATEGORIES`)이 missing/weak으로 돌아온 false-negative 의심일 때. 재시도 후에도 유효 근거 없으면: over-claim이면 `invalid_match=True`, 아니면 genuine miss로 표기.
  - `GROUP_CATEGORIES = {state_management, styling, data_fetching, build_tooling, testing, framework, language}`.

### 6-2. 검증 (`verify_matches.py` — 2 레이어, 그대로 이식)

1. **결정적 추출형 체크** (`_extractive_pass`): 모든 `evidence_quote`가 이력서 텍스트 또는 파싱된 evidence(`exact_quote`/`normalized_summary`)의 정규화본(`_norm` = whitespace 접고 lower)에 **substring으로 실재**해야 함. 비추출 인용은 제거 + risk_note. *지지를 주장했으나 추출 인용 0*인 행은 `invalid_match=True` + `matched_evidence_ids=[]` + match_level 강등(direct/adjacent→weak, weak→missing) + confidence=low.
2. **보수적 LLM verifier** (`match_verifier` 프롬프트): 행별 재판정. **severity를 낮추기만**(`new_sev = min(cur, v_sev)`, downgrade/exaggerated면 추가 -1). confidence는 현재와 verifier 중 낮은 쪽, 강등 시 medium 이하로 cap, missing이면 low. 절대 올리지 않음.

`MAX_RESUME_CHARS = 9000` (verifier 프롬프트에 넣는 이력서 컷오프).

---

## 7. 추출(단계 1·2) + listwise(단계 7) + pairwise(단계 9)

### 7-1. 이력서 evidence 추출 (`parse_resume.py`)

LLM(`resume_extract`)로 evidence 항목 추출 + **결정적 Skills evidence 항상 보강**(`extract_skills_evidence`): 이력서의 Skills/기술스택 헤딩 아래 불릿을 코드로 파싱해 `exact_quote`=verbatim 불릿, `skills`=토큰 분해. 명시된 툴(Tailwind/styled-components/Socket.io/WebTransport 등)이 LLM 누락으로 사라지지 않게 보장. id 충돌 시 `_x` suffix. (`_KEY_FRONTEND_SKILLS` 존재 점검은 `skills_debug`로 디버그 출력.)

### 7-2. JD 구조화 (`parse_job.py`)

LLM(`jd_extract`)로 `role_family` + requirements/preferred_requirements 분류. 모델이 `prerequisite_status` 누락 시 default: nature가 behavioral이면 `behavioral_preference`, 아니면 `prerequisite`(보수적 — duty는 명시적으로만). 리스트 내 id 유일성 보장. `MAX_RAW_CHARS = 12000`.

### 7-3. listwise 재랭킹 (`rerank_listwise.py`)

압축 매칭표(`compress_table` — JD/이력서 원문 없이 type별 매칭 카운트 + strong + core_prerequisite_gaps + preferred_technical_gaps + behavioral_gaps + product_duty_gaps_not_blocking + invalid + risks)만 LLM(`listwise_rerank`)에 전달. **누락/중복 보정**: 1차 응답에서 빠진 job_id 있으면 재질의 1회, 그래도 빠지면 **fit/domain 기준 안전 배치**(맨 끝 blind append 아님 — `key(jid) = (fit_level, DOM_RANK)`로 적절 위치 삽입). 중복 id는 첫 등장만 유지.

### 7-4. pairwise 후보 집합(단계 8) + 비교(단계 9)

**후보 집합 구성(결정적, `_build_pairwise_candidates` 그대로 이식).** 상수: `TOP_K_PAIRWISE=5`, `MAX_PAIRWISE_CANDIDATES=8`(env override 가능 — config default). `top_k = min(TOP_K_PAIRWISE, len(ordered_ids))`. 4단 포함 규칙(누적, 첫 사유만 기록) → 상한 bound:

```python
_DOM_RANK = {"strong": 3, "adjacent": 2, "weak": 1, "mismatch": 0}

def _build_pairwise_candidates(ordered_ids, fits, domain_ctx, top_k):
    def fit(j): return fits[j]["level"]
    def dom(j): return domain_ctx.get(j, {}).get("domain_alignment", "weak")
    def rf(j): return domain_ctx.get(j, {}).get("role_family", "other")
    def is_strong_fe(j): return dom(j) == "strong" and rf(j) in ("frontend", "fullstack")
    lw_rank = {j: i for i, j in enumerate(ordered_ids)}
    candidates, reasons = [], {}
    def add(j, why):
        if j not in reasons:
            candidates.append(j); reasons[j] = why
    # 1) listwise top-5 (any domain)
    for j in ordered_ids[:top_k]:
        add(j, "listwise top-5")
    # 2) any fit>=4 (caps로 weak/mismatch는 fit>=4 불가 → 엔지니어링 한정)
    for j in ordered_ids:
        if fit(j) >= 4: add(j, "fit>=4")
    # 3) strong frontend/fullstack with fit > 현재 집합의 최약 fit
    for j in ordered_ids:
        if j in reasons or not is_strong_fe(j): continue
        weakest = min((fit(c) for c in candidates), default=0)
        if fit(j) > weakest:
            add(j, f"strong frontend rescue (fit {fit(j)} > weakest-in-set {weakest})")
    # 4) catch-all: 더 낮은-fit adjacent/weak가 비교되는데 strong이 빠진 경우 구제
    for j in ordered_ids:
        if j in reasons or dom(j) != "strong": continue
        if any(dom(c) in ("adjacent", "weak", "mismatch") and fit(c) < fit(j) for c in candidates):
            add(j, "strong-domain rescue (a lower-fit adjacent/weak role is compared)")
    # bound: fit → domain → listwise rank 우선 (weak/mismatch 경유 추가 금지 — 규칙 2~4)
    cap = MAX_PAIRWISE_CANDIDATES
    if len(candidates) > cap:
        kept = set(sorted(candidates,
                          key=lambda j: (-fit(j), -_DOM_RANK.get(dom(j), 1), lw_rank.get(j, 999)))[:cap])
        for j in candidates:
            if j not in kept: reasons[j] += " [bounded out]"
        candidates = [j for j in ordered_ids if j in kept]
    info = {
        "pairwise_candidate_set": [{"job_id": j, "reason": reasons[j], "fit": fit(j),
                                    "domain_alignment": dom(j), "role_family": rf(j)} for j in candidates],
        "rescued_strong_domain": [j for j in candidates if reasons[j].startswith("strong")],
        "strong_domain_excluded": [
            {"job_id": j, "fit": fit(j),
             "reason": ("bounded out (max candidates)" if "[bounded out]" in reasons.get(j, "")
                        else f"not rescued (fit {fit(j)} not above weakest-in-set)")}
            for j in ordered_ids if is_strong_fe(j) and j not in candidates],
    }
    return candidates, info
```

**비교(`compare_pairwise.py`, `pairwise_compare` 프롬프트):** 모든 후보 쌍을 **A/B와 B/A 두 방향** 비교. 양방향 winner가 일치(`agreed`)할 때만 outcome 확정(confidence = 두 방향 중 낮은 쪽), 불일치면 outcome=tie/confidence=low(순서 편향 차단).

---

## 8. LLM 게이트웨이 + 결정론 캐시 키 (GS-1 직결)

### 8-1. LLM 게이트웨이 (`llm.py` → `ai/worker` 프로덕션 게이트웨이로 이식)

- `JSON_SYSTEM` 시스템 프롬프트(아래 부록 B). `call_text(system, user, max_tokens, temperature=0.0)`. `call_structured(system, user, validate, max_tokens, temperature=0.0, cache_label=None)`: JSON 파싱(`_extract_json` — code fence 제거 + greedy shrink) + `validate` 실행, **실패 시 1회 재시도**(직전 에러를 프롬프트에 첨부). `cache_label` 주면 결과 캐시.
- temperature=0.0 기본. OpenAI 경로는 모델 계열 파라미터 차이(`max_tokens` ↔ `max_completion_tokens`, seed 미지원, 고정 temperature)를 **API 에러 기반으로 자동 적응**(모델명 하드코딩 없음). seed = `LLM_SEED`(기본 7, 재현성 힌트 — *캐시가 주 메커니즘*).
- **프로토타입의 멀티-provider(OpenAI/Anthropic) 추상화는 이식 시 OpenAI 핀으로 단순화**(ARCH §7 LLM 제공자=OpenAI). provider 자동 선택 로직은 버린다. 단 "구조화 출력 검증 + 1회 재시도 + 캐시" 3계층은 보존.

### 8-2. 결정론 캐시 키 (GS-1 게이트 — 반드시 보존)

- **키 = `sha256(model + rendered_prompt + SCHEMA_VERSION)`** (프로토타입 `cache.make_key(model, system, user, SCHEMA_VERSION)`). 시간·랜덤·환경 값 혼입 절대 금지(§3-1 결정론 경계). `SCHEMA_VERSION` 변경 시 캐시 자동 무효화(프롬프트/스키마/스코어링 의미 변경 시 bump).
- **저장소 적응(§3-2):** 프로토타입은 파일 캐시(`outputs/cache/<label>__<key12>.json` + `_meta`). 이식 시 **Postgres worker 소유 테이블 + 좁은 JSONB**(`ranking_runs.result`)로 교체(ARCH §7-3, 별도 Redis 미도입 — YAGNI). **캐시 키 *개념*(model+prompt+schema_version)은 그대로**, 물리 저장만 DB.
- **네임스페이스 격리:** 프로토타입은 회귀 픽스처가 `fixture/`, eval이 `eval/` 네임스페이스를 써 정상 실행 캐시와 섞이지 않음. 이식 시 동등한 격리(예: 테이블 컬럼/스키마 분리)로 *회귀 골든이 일반 재계산에 흔들리지 않게* 한다.
- `--refresh-cache` 동등: 강제 재계산 경로(캐시 무시하고 새로 쓰기). GS-1 miss 재계산 테스트(top-k 순서 변동 0)에 사용.

> **버전 변경 시 기존 캐시·점수 마이그레이션 정책은 미정**(F-001 §12 열린 질문). 이식 단계에서는 SCHEMA_VERSION/PROMPT_VERSION 핀만 보존하고 마이그레이션은 후속.

---

## 9. Collector — 수집(토스·당근) + 도메인 인지 선택 (`crawler`)

> ARCH §6: httpx 정적 fetch 우선, 동적렌더링/anti-bot 시 Playwright 승격(A-1 검증됨). 둘 다 **Greenhouse 기반 JSON API**라 정적 fetch로 충분(Playwright 불필요).

### 9-1. fetch 소스 (그대로 이식)

- **토스:** `https://api-public.toss.im/api/v3/ipd-eggnog/career` — 목록 `GET {base}/jobs`(JSON `success` 배열: `id, title, absolute_url`), 상세 `GET {base}/jobs/{id}`(`success.content` 또는 `payload.content`, `html.unescape`).
- **당근:** `https://boards-api.greenhouse.io/v1/boards/daangn/jobs?content=true`(JSON `jobs` 배열에 `content` 포함 — 2차 fetch 불필요).
- 헤더 `{"User-Agent": USER_AGENT, "Accept": "application/json, text/html"}`, timeout `REQUEST_TIMEOUT=15`. `USER_AGENT`는 이식 시 서비스 식별자로 갱신(ToS 준수 운영 원칙).
- 원본 저장: 프로토타입은 `data/raw/jobs/<job_id>.{json,html}` + `index.json`. **이식 시 `job_postings` 테이블 upsert**(Collector 소유, §3-2). `job_id = "{source}-{gid}"`. HTML→텍스트는 BeautifulSoup `get_text("\n")` + 빈 줄 접기.

### 9-2. 제목 키워드 필터 (그대로 이식)

`_norm(s) = re.sub(r"[\s\-_/]+", "", s.lower())`. `keyword_match(title) = any(_norm(kw) in _norm(title) for kw in TARGET_KEYWORDS)`. 기본 `TARGET_KEYWORDS`:
```
software, engineer, developer, frontend, backend, fullstack, android, ios, server, platform,
소프트웨어, 엔지니어, 개발자, 프론트엔드, 백엔드, 서버, 플랫폼
```
(엔지니어링 토큰 강제 — bare "intern/인턴/web/웹" 의도적 제외해 마케팅/운영 직군 차단. env `TARGET_KEYWORDS`로 override.)

### 9-3. 제목 기반 role_family 분류 (휴리스틱, 그대로 이식)

`ROLE_PATTERNS`(순서대로, 더 구체적 먼저 — 첫 매치 승):
```python
ROLE_PATTERNS = [
  ("fullstack", ["fullstack","full-stack","full stack","풀스택"]),
  ("frontend",  ["frontend","front-end","front end","프론트엔드","프론트","web frontend","웹 프론트","웹프론트","react","vue","웹 프론트엔드"]),
  ("android",   ["android","안드로이드"]),
  ("ios",       ["ios"]),
  ("ml_ai",     ["ai engineer"," ai ","machine learning","ml engineer","mlops","deep learning","data scientist","llm","인공지능","생성형"]),
  ("data",      ["data analytics","analytics engineer","data engineer","data platform","데이터 엔지니어","데이터 분석","데이터"]),
  ("security",  ["security","보안","모의해킹","detection","response","appsec","침해사고"]),
  ("devops_infra",["aiops","devops","sre","platform engineer","platform","infra","인프라","network","네트워크","cloud","클라우드","kubernetes","reliability","플랫폼"]),
  ("backend",   ["backend","back-end","back end","서버","백엔드","server"]),
  ("marketing", ["marketer","marketing","마케팅","마케터"]),
  ("design",    ["designer","design","디자인"]),
  ("product",   ["product manager","프로덕트 매니저","프로덕트매니저","기획자"]),
]
```
> 제목 휴리스틱 role_family는 *선택용 임시값*. **LLM 파싱 role_family(`jd_extract`)가 최종 권위.**

### 9-4. 도메인 인지 균형 선택 (그대로 이식)

tier = `domain_alignment(role_family, USER_PRIMARY_DOMAINS, USER_SECONDARY_DOMAINS)`를 `{strong→primary, adjacent→adjacent, weak→weak, mismatch→mismatch}`로 매핑. `--pool-size`(기본 50)로 큰 풀 수집(tier 순서 + 회사 round-robin) → `--limit`(기본 `MAX_JD_PAGES=10`)만큼 **`select_balanced`**: `q_primary=round(limit*0.5)`, `q_adjacent=round(limit*0.3)`, `q_contrast=limit-q_primary-q_adjacent`(weak+mismatch). 정원 미달 시 primary→adjacent→weak→mismatch 순 backfill. limit=10이면 **5 primary + 3 adjacent + 2 contrast**. 선택 내역 = `fetch_selection_report.{md,json}`(tier/role_family 분포, selected/skipped). 비싼 LLM 단계 전 값싼 휴리스틱 선별.

> **이식 적응:** 프로토타입 `USER_PRIMARY_DOMAINS`(기본 frontend/fullstack/web/robot_web)·`USER_SECONDARY_DOMAINS`(backend/cloud/mobile)는 **전역 하드코딩**. 프로덕션은 **후보(이력서)별 값**으로(다중 사용자 확장 대비 — Charter §2.1 직군 미확정 페르소나도 후보별 도메인). MVP는 단일 사용자라 env/설정값으로 시작 가능. `jobs_manual.md` 폴백(스크래핑 실패 시 수동 JD 붙여넣기 → 동일 파이프라인)도 동등 경로로 보존.

---

## 10. 평가 하니스 (`ai/eval`) — GS-1·GS-2·GS-3 측정 경로

> **이식 핵심 안전장치.** 스코어링을 바꿀 때마다 "정확도 보존/개선 + 회귀 0"을 자동 확인하는 게이트. 프로덕션은 도메인 골든셋을 **CI 게이트**로 건다(아니면 스코어링 변경 차단).

### 10-1. 불변식 회귀 (GS-1 — 결정성·제품 규칙)

고정 3-JD 픽스처(Frontend / Android device SWE / Content Marketer 인턴)에서 *정확한 fit 수치가 아닌 제품 수준 불변식* 검사. 픽스처 캐시는 격리 네임스페이스(§8-2). **불변식 10종(그대로 이식):**
1. Frontend가 #1 (`rank==1`).
2. Frontend fit ≥ 4.
3. Android가 Frontend보다 아래 (`rank > fe.rank`).
4. Android fit ≤ 3.
5. Android fit < Frontend fit.
6. Marketing이 최하위 (`rank == n`).
7. Marketing fit ≤ 2.
8. **mismatch 역할이 어떤 non-mismatch보다 위로 못 옴** (`min(mismatch_ranks) > max(nonmismatch_ranks)` 또는 한쪽 empty) — 도메인 우선순위 가드.
9. 살아남은 모든 evidence 인용이 추출형 (`_is_extractive` 재검).
10. pairwise A/B vs B/A 불일치는 보고되어야 하나 최상위 랭킹을 바꾸지 않음 (`not disagreement or fe.rank==1`).

> **회귀 철학:** 프롬프트/스키마 개선으로 절대 fit 수치는 정당히 변동될 수 있다(예: Skills recall 개선으로 Android fit 2→3 상승). 버그가 아니며 Frontend보다 낮은 한 허용 — 그래서 Android 불변식이 `≤2`가 아니라 `≤3 (+< Frontend fit)`이다. GS-1은 *캐시 hit 변동 0* + *miss 재계산 top-k 순서 변동 0*으로 측정(Charter §6).

### 10-2. 멀티-페르소나 진단 (방향성 일반화)

4개 **합성** 페르소나(`backend_platform`, `junior_frontend`, `ai_ml_application`, `devops_infra_security`)로 *방향성* 점검(정확도 아님). 페르소나별 `primary/secondary_domains`를 주입(전역 config override)해 도메인 tier가 페르소나별로 산출되게 한다. 6 불변식(severity): extractive(fail), fit_scale(1~5 정수·%금지, fail), mismatch_priority(fail), expected_top_in_top3(warning/n-a), domain_order(warning/n-a), primary_domain_available(warning/n-a). `--compare-ranking-modes`로 3 모드 ablation → `ranking_mode_comparison.md`(fit_rank_inversions/tier_inversions/mismatch_violation). 합성 데이터는 합성임을 명시하고 실제 이력서를 덮어쓰지 않는다.

페르소나 도메인 프로파일:

| 페르소나 | primary | secondary |
|---|---|---|
| backend_platform | backend | fullstack, devops, cloud, infra |
| junior_frontend | frontend, web | fullstack |
| ai_ml_application | ml_ai, ai | data, backend |
| devops_infra_security | devops, cloud, infra | security, backend |

### 10-3. 골든 페어 정확도 (GS-3 프록시 — 유일한 외부 정답 기반)

사람이 라벨링한 A/B 공고 쌍과 시스템 순위 일치율 = *내려갈 수 있는* 정확도 숫자. **LLM 호출 없음** — `outputs/eval/<persona>/`의 저장 산출물만 읽음(공고가 없으면 재수집 X, unavailable 처리).

- **`propose_pairs`**: 저장 산출물에서 하드 케이스를 자동 추출(라벨 안 함, `expected_winner` 공백). 신호: 같은 직군·근접 fit, 모드 불일치, fit↔BT 불일치, 주력 vs 인접 fit 역전, 연차 갭, 동일 회사 유사 직군. 난이도(hardness 합 ≥3 hard/2 medium/else easy). 출력 `proposed_pairs.{md,json}` + `manual_labeling_packet*`.
- **`load_pairs`**: 라벨 검증, 빈 라벨은 "미라벨"로 분리(graceful skip). **A/B 규약: A = 기본 모드 domain_fit_bt가 더 높게 랭크한 공고**. 라벨 4종 `LABELS = (A_better, B_better, tie, unsure)`. `CATEGORIES = (same_domain_close, adjacent_vs_primary, seniority_gap, domain_transfer, tool_stack_gap, product_duty_vs_prerequisite, weak_vs_adjacent, mismatch_guard)`.
- **지표(`aggregate_metrics`):** **strict pairwise** = 분모 A_better/B_better, 시스템이 사람 선택 쪽을 위에 두면 정답. **tie-aware** = tie 포함(시스템이 near-tie=같은 fit_level로 보면 정답), unsure 제외. 페르소나/난이도/카테고리별 정확도, 모드 불일치 목록, 시스템≠사람(개선 후보) 목록.
- **`rescore_persona(eval_root, persona, scoring_mode)`**: 저장 산출물만으로 fit 재계산(`compute_fit(..., dedup_required_preferred=(scoring_mode=="dedup_required_preferred"))`) + **실제 `aggregate()` 재사용**해 모드별 순위 재생성 → **LLM 없이 스코어링 변경을 ablation**. "저장물로 재채점"의 레퍼런스. 프로덕션 CI 게이트의 토대.

### 10-4. 이식 *전* 보완 권고 (골든 페어가 드러낸 약점)

baseline `domain_fit_bt` 16/20, 오류 4건 전부 `same_domain_close`. 근본 원인: (1) **cap 대칭 결함** — critical 갭과 required 갭을 동급 cap(§4-2 step3), (2) **후보 연차 미모델링** — "3년+/5년+" vs 주니어를 못 깎음(프로덕션은 *연차 추정*이 1급 피처여야), (3) **role-core vs 주변 도구 갭 미구분**, (4) **required/preferred 중복 이중 계산**(→ dedup §4-4). **dedup 실험으로 16→19, 회귀 0** 확인됐으나 개선 3건이 한 공고에서만 나와 **기본값 승격 보류, 실험 유지**. 승격 4조건: (a) 정확도 개선/보존, (b) 비-프론트엔드 회귀 0, (c) 진짜 필수 요구 약화 안 함, (d) 탐지가 계속 보수적.
> **권고:** 코어 알고리즘은 그대로 이식하되, *프로덕션 스코어링을 신뢰하기 전* (1)·(2)를 **이 프로젝트의 골든셋**으로 재검증·보완하라(GS-3 τ 프록시와 같은 정신, Charter §6). dedup은 실험 플래그로만, 기본화는 골든셋 확장 + 4조건 충족 시에만. — 본 보완은 M1 이후 후속(Charter §9 A-3 결과 의존).

---

## 11. 이식 적응 포인트 요약 (🟢 그대로 / 🟡 개념+재구현 / 🔴 버림)

| 영역 | 이식 | 메모 |
|---|:--:|---|
| 데이터 계약(모델·enum·가중치) | 🟢 | **가장 먼저.** `ai/core` |
| compute_fit + cap + dedup | 🟢 | 알고리즘 본체 — 상수 그대로 |
| Bradley-Terry + elo fallback | 🟢 | 순수 파이썬 |
| aggregate(3 모드) + 도메인 가드 | 🟢 | 정렬 키 그대로 |
| 추출형 검증 + 보수적 verifier | 🟢 | 신뢰 레이어 — 생략 금지 |
| 7개 프롬프트(부록 A) | 🟢 | `ai/worker/prompts/*.md`로 verbatim |
| 평가 하니스(회귀·페르소나·골든) | 🟢 | `ai/eval` — CI 게이트 |
| 추출(이력서/JD)·매칭·rematch·listwise·pairwise | 🟡 | 개념+프롬프트 그대로, 실 LLM 인프라로 |
| LLM 게이트웨이 | 🟡 | OpenAI 핀으로 단순화. 구조화검증+재시도+캐시 3계층 보존 |
| 캐시 | 🟡 | 키 개념(model+prompt+schema_version) 보존, 저장은 Postgres JSONB |
| config(USER_DOMAINS·SCHEMA_VERSION) | 🟡 | USER_DOMAINS 하드코딩 → 후보별/설정값 |
| 수집(토스·당근 + 도메인 선택) | 🟡 | 엔드포인트·휴리스틱 그대로, 저장은 `job_postings` upsert |
| 리포트(필드) | 🟡 | 필드(매칭/결손/인용/cap사유/fit) 보존, 출력은 JSONB→API |
| CLI 오케스트레이션(main) | 🟡 | 단계 시퀀스가 *명세*. worker 오케스트레이션 + cron |
| rich 콘솔 UI · cp949 우회 · 합성 페르소나(테스트 픽스처화) | 🔴 | 프로토타입 스캐폴딩 |

**출력 산출물 계약(이식 시 JSONB/API로):** `final_ranking.json`(note "fit≠합격확률" + user_profile + guard_moves + ranking[FitResult]), `matching_tables.json`(job_id→MatchingTable), `pairwise_comparisons.json`(bradley_terry_scores + candidate_set + comparisons). 리포트는 *합격확률/% 출력 금지* + BT="상대 강도, 확률 아님" 명시를 보존(Charter §5, GS 정합).

---

## 부록 A. 프롬프트 7종 (verbatim — `ai/worker/prompts/*.md`로 그대로 이식)

> LLM IP. 패러프레이즈 = 다른 동작 → **글자 그대로** 옮긴다. `{{VAR}}` 플레이스홀더는 코드의 `render(template, **kwargs)`가 치환(`{{KEY}}` → str(value)). 아래는 7개 프롬프트 **전문(verbatim)** — T-005 구현 시 `ai/worker/prompts/<name>.md`로 글자 그대로 작성한다(펜스 안 내용이 파일 본문).

### A-1. `resume_extract.md`
````text
You extract structured **evidence items** from a candidate's resume.

## Hard rules
- Use ONLY the resume text given below. NEVER invent, infer, or embellish facts.
- `exact_quote` MUST be copied **verbatim** (character-for-character) from the resume text. Do not paraphrase inside `exact_quote`.
- If you are unsure whether something is in the resume, leave it out.
- Output JSON only. No markdown, no commentary.

## Granularity
- Create one evidence item per distinct, meaningful unit: each work experience, each project, each notable achievement, each education entry, each award/certification, each activity.
- Prefer several focused items over one giant item. A single job or project may yield multiple evidence items if it contains distinct accomplishments (e.g., a latency optimization vs. a monorepo refactor).

## Output schema
Return a JSON object: `{"evidence": [ <EvidenceItem>, ... ]}`

Each EvidenceItem:
- `evidence_id`: short stable id you assign, e.g. "E1", "E2", ...
- `title`: short human label (e.g. "NAVER LABS 인턴 - 카메라 스트리밍 지연 최적화")
- `source_section`: the resume heading this came from (e.g. "Experience", "Projects")
- `exact_quote`: a verbatim span copied from the resume that backs this item (keep it focused; you may join a few consecutive bullet lines with "\n")
- `normalized_summary`: your own 1-2 sentence neutral summary
- `skills`: array of concrete skills/technologies mentioned for this item (verbatim tokens, e.g. ["React", "WebTransport"])
- `domain`: array of domains/areas (e.g. ["frontend", "infra", "robotics"]) — only if evident
- `evidence_type`: one of "work_experience" | "project" | "education" | "award" | "activity" | "other"
- `strength`: one of "strong" | "medium" | "weak"
  - "strong": professional/production work, real users at scale, measurable outcomes, internships at companies
  - "medium": substantial personal/team projects with real usage, coursework with depth
  - "weak": short activities, early/small projects, unquantified claims
- `recency`: a date or year string if the resume states one (e.g. "2025"); otherwise null

## Resume text
<<<RESUME
{{RESUME_TEXT}}
RESUME

Return ONLY the JSON object.
````

### A-2. `jd_extract.md`
````text
You convert a single job description (JD) into a structured object.

## Hard rules
- Use ONLY the JD text given. Do not invent requirements that are not stated.
- Classify each requirement with category labels, NEVER a numeric weight/importance (no 0.25).
- Output JSON only. No markdown, no commentary.
- The JD may be in Korean; keep requirement text in its original language.

## role_family (infer conservatively)
Set `role_family` to exactly one of:
`frontend | backend | fullstack | android | ios | data | ml_ai | devops_infra | security | product | marketing | design | other`
Infer from the title, responsibilities, requirements, and tech stack. Examples:
- React/SPA/web UI/browser POS web → `frontend`
- Server/Spring/DB/distributed/API → `backend`
- "Device Software Engineer (Android)", Android Framework/HAL/AOSP, Kotlin/Java native → `android`
- Content/marketing/SNS/영상 → `marketing`
If genuinely mixed front+back, use `fullstack`. When unsure, use `other`.

## requirement_nature (for every requirement)
Set `requirement_nature` to exactly one of:
`technical | domain | experience_level | behavioral | language | location | employment | other`
- `technical`: concrete skill/tool/tech (React, TypeScript, Android Framework, AOSP, C/C++, crash/ANR debugging, Spring, SQL, distributed systems, API design...).
- `domain`: a field/area of work (payments, ads, robotics, commerce...).
- `experience_level`: seniority/years ("5년 이상", "신입", "리드 경험").
- `behavioral`: personality / soft traits ("주도적으로 문제 해결", "근본 원인을 파고드는", "협업을 잘하는", "함께 성장", "커뮤니케이션").
- `language`: human language (English/Korean fluency).
- `location` / `employment`: workplace / 정규직·인턴·계약 등.

## PREREQUISITE vs PRODUCT DUTY — the most important distinction
A **requirement** is something the candidate is expected to **ALREADY HAVE before joining** (a prior skill, capability, or experience). A **responsibility** is something the candidate will **DO after joining**.

For every item, also set:
- `requirement_origin`: `explicit_requirement` (stated in 자격요건/우대/Requirements) | `responsibility_inferred` (you inferred it from 합류하면 함께할 업무/responsibilities) | `product_context` (the product/domain the team works on) | `company_value` (culture/values).
- `prerequisite_status`:
  - `prerequisite` — a prior skill/capability/experience the candidate must already have (e.g. React, TypeScript, SPA, frontend architecture; Android Framework/AOSP/Native-C++/crash·ANR/system-level debugging; Spring, databases, distributed systems; "5년 이상 경력").
  - `product_duty` — work the candidate will perform on the job, NOT a prior prerequisite (e.g. "build a POS product", "build payment SDK/plugins", "develop dashboards"). Mark these `product_duty` **unless the JD explicitly asks for prior experience** with them (e.g. "결제 SDK 개발 경험이 있는 분" → that IS a prerequisite).
  - `context` — product/domain background ("오프라인 결제 시장", "1,900만 MAU 광고 플랫폼"). Background, not a skill the candidate must have.
  - `behavioral_preference` — soft traits (proactive, root-cause, collaboration, grows-with-us, communication).

### Rules
- **Do NOT promote a responsibility into a `required` prerequisite unless it clearly implies a distinct prior skill/capability/experience.** Building a product (POS, SDK, dashboards, payment logic) is a `product_duty`, not a prerequisite — even though it appears in the responsibilities/role-defining text.
- Concrete prerequisite technical skills go in `requirements` as `critical`/`required` with `prerequisite_status: prerequisite` — even if the JD soft-pedals them under 우대 (e.g. for an Android device role, Framework/AOSP/Native-C++/crash·ANR are genuine prerequisites).
- Generic behavioral lines → `preferred`/`optional` with `prerequisite_status: behavioral_preference` (even if phrased "필요해요"). Only mark behavioral `required` if the JD explicitly says it is mandatory/필수.
- Product duties and context still belong in `responsibilities`; only add them as requirement objects if you must, and then mark them `product_duty`/`context` so they do not act like missing prerequisites.

### Worked examples
- Frontend JD "웹 기술로 POS 제품을 만들어요 / 결제 SDK·플러그인을 만들어요" → `product_duty` (NOT a required prerequisite). "오프라인 결제 시장" → `context`. "React/SPA 능숙", "TypeScript/Flow 정적 타입" → `prerequisite` (technical, required/critical).
- Android device JD "Framework/HAL/AOSP, crash/ANR/system debugging, C/C++" → `prerequisite` (technical). An old student Android app only supports basic Android app experience, not these.

## Split compound requirements — but handle AND vs OR (IMPORTANT)
- **AND (distinct conditions):** if one bullet lists several *different* requirements joined by "and / ,", split into separate requirements (one condition each). This stops a broad weak match from covering several role-defining gaps.
  - Example — "Native/C++ 이해, crash/ANR 디버깅 경험, 시스템 레벨 디버깅" → three separate technical requirements.
- **OR (interchangeable alternatives — "one of these is enough"):** if a bullet lists interchangeable options where having ANY one satisfies it, keep it as **ONE** requirement. Put the options in an `alternatives` array and preserve the original wording in `requirement_text`. Do NOT split an OR-group into separate requirements.
  - Recognize OR-groups from wording/slashes/commas implying alternatives: "TypeScript, Flow", "Kotlin/Java", "React/Vue", "AWS/GCP", "~ 또는 ~", "~ 중 하나".
  - Example — "TypeScript, Flow를 이용한 정적 타입 분석 경험" → ONE requirement, `requirement_text` = original phrase, `alternatives` = ["TypeScript", "Flow"]. Having either one satisfies it.
- **EXAMPLES / "such as / 등 / 예: / e.g." tool & library lists:** when a requirement lists tools/libraries/frameworks as EXAMPLES or a stack (e.g. "PyTorch, Hugging Face Transformers, LangChain 등을 활용한 경험", "Spark, Flink 같은 도구", "such as PyTorch/TensorFlow"), treat the WHOLE thing as **ONE** requirement whose underlying ask is "experience with such tools", satisfied by ANY one. Put the listed items in `alternatives` and keep the original phrase in `requirement_text`.
  - **Do NOT split example libraries into multiple separate `critical`/`required` requirements** — that wrongly inflates the unmet-prerequisite count. (e.g. "PyTorch, Hugging Face, LangChain" → ONE requirement with alternatives=["PyTorch","Hugging Face Transformers","LangChain"], NOT three.)
- If a bullet mixes AND + OR (e.g. "Android 앱 또는 Framework 개발 경험, 그리고 crash/ANR 디버깅"), split on AND first, then keep each OR-part as one requirement with `alternatives`.

## SAME-CATEGORY tool/library groups (IMPORTANT — set `requirement_category`)
When a JD lists multiple interchangeable tools/libraries from the **same category**, emit **ONE grouped requirement** (do NOT make each library its own required prerequisite). Set `requirement_category`, put the libraries in `alternatives`, preserve original text, and set `alternative_match_policy: "exact_or_same_category"` (a same-category equivalent counts). Use these categories:
- `state_management` — Recoil, Jotai, Zustand, Redux, MobX → "프론트엔드 상태관리 경험"
- `styling` — Emotion, Vanilla-extract, styled-components, Tailwind CSS, CSS Modules, Sass → "프론트엔드 스타일링 시스템 경험"
- `data_fetching` — React Query, TanStack Query, SWR, Apollo Client, Relay → "프론트엔드 데이터 패칭/서버 상태 관리 경험"
- `build_tooling` — Vite, Webpack, Rollup, esbuild, Babel → "프론트엔드 빌드 도구 경험"
- `testing` — Jest, Vitest, React Testing Library, Cypress, Playwright → "프론트엔드 테스트 경험"

Example — a JD listing "Recoil, Jotai" (state) and "Emotion, Vanilla-extract" (styling) → TWO grouped requirements, NOT four: one `state_management` (alternatives=["Recoil","Jotai","Zustand","Redux","MobX"]) and one `styling` (alternatives=["Emotion","Vanilla-extract","styled-components","Tailwind CSS","CSS Modules","Sass"]).

### Framework caution (do NOT over-group)
- Frameworks (React, Vue, Angular, Svelte) are NOT freely interchangeable. If the JD specifically requires **React** (role-defining), keep it as its OWN prerequisite with `requirement_category: "framework"` and `alternative_match_policy: "exact_only"` (a different framework must NOT count as a same-category substitute).
- Only group frameworks under one requirement when the JD itself says "React/Vue/등 SPA 프레임워크 중 하나" (genuinely interchangeable). Otherwise keep React standalone.
- For non-framework categories (state/styling/data_fetching/build/testing), `alternative_match_policy` is `exact_or_same_category`.
- A broad **platform-experience** requirement (e.g. "Android 기반 소프트웨어 개발 경험", "iOS 개발 경험") is a PLATFORM prerequisite, NOT a framework-substitution group. It is satisfied by ANY genuine experience on that exact platform (an app — even small/old). Don't expect a specific sub-framework; a DIFFERENT platform doesn't count, but the same platform (even shallow) does (the matcher scores it weak/adjacent by depth, never missing).

## Sections
- `requirements`: 자격요건/Requirements/필수 items + role-defining technical capabilities derived from responsibilities (each a Requirement; type usually `critical`/`required`).
- `preferred_requirements`: 우대/Preferred items and generic behavioral preferences (each a Requirement; type usually `preferred`/`optional`).
- Keep the two lists disjoint.

## Output schema
{
  "role_family": "<one value above>",
  "employment_type": "", "location": "", "team": "", "seniority": "",
  "tech_stack": ["..."],
  "responsibilities": ["..."],
  "hard_constraints": ["탈락 기준에 가까운 제약", "..."],
  "requirements": [ {"requirement_id": "R1", "requirement_text": "...", "requirement_type": "critical|required", "requirement_nature": "technical|domain|experience_level|behavioral|language|...", "requirement_origin": "explicit_requirement|responsibility_inferred|product_context|company_value", "prerequisite_status": "prerequisite|product_duty|context|behavioral_preference", "alternatives": ["OptionA", "OptionB"], "requirement_category": "state_management|styling|data_fetching|build_tooling|testing|framework|language|other", "alternative_match_policy": "exact_or_same_category|exact_only"} ],
  "preferred_requirements": [ {"requirement_id": "P1", "requirement_text": "...", "requirement_type": "preferred|optional", "requirement_nature": "...", "requirement_origin": "...", "prerequisite_status": "...", "alternatives": [], "requirement_category": "other", "alternative_match_policy": "exact_or_same_category"} ]
}
Assign ids yourself: "R1","R2",... for requirements and "P1","P2",... for preferred_requirements.

## Known fields (already verified, do not change)
- company: {{COMPANY}}
- title: {{TITLE}}
- url: {{URL}}

## JD text
<<<JD
{{RAW_TEXT}}
JD

Return ONLY the JSON object.
````

### A-3. `requirement_evidence_match.md`
````text
You build a **requirement → evidence matching table** for ONE job, using a fixed candidate.

## Hard rules
- Compare ONLY this candidate's evidence against this job's requirements. Do not consider company prestige, salary, or brand.
- **Select evidence by `evidence_id` only. DO NOT write, paraphrase, or copy any quote text.** The system fills the actual quotes verbatim from the evidence items you select. Writing your own quote text is forbidden and will be ignored.
- Only use `evidence_id` values that appear in the provided evidence list. Never invent an id.
- If no evidence supports a requirement, set `match_level` to "missing" with an empty `matched_evidence_ids`.
- Never output pass/acceptance probability or any percentage. You assess FIT only.
- Output JSON only. No markdown, no commentary.

## OR-groups & same-category groups (requirements with an `alternatives` list)
A requirement may carry `alternatives`, a `requirement_category`, and an `alternative_match_policy`.
- Count the group as **ONE** requirement. Do NOT treat each unmatched alternative as a separate gap.
- If the candidate's evidence shows **any one of the exact alternatives** → `direct`.
- **Same-category equivalent rule** (`alternative_match_policy: "exact_or_same_category"`, used for state_management / styling / data_fetching / build_tooling / testing): if the candidate has a DIFFERENT tool in the SAME category, mark `adjacent` (transferable), NOT `missing`. Examples:
  - state_management group [Recoil, Jotai] + resume has **Zustand** → `adjacent`.
  - styling group [Emotion, Vanilla-extract] + resume has **styled-components / Tailwind** → `adjacent`.
  - data_fetching group [React Query, SWR] + resume has **React Query** → `direct` (exact).
  - build_tooling [Vite, Webpack] + resume has **Vite** → `direct`; testing [Jest, Vitest] + resume has **Vitest** → `direct`.
- **Framework caution** (`alternative_match_policy: "exact_only"`, used for `framework`): a DIFFERENT framework does NOT count — requirement React + resume has only Vue → `weak`/`missing`, never adjacent. Do not over-generalize frameworks.
  - **BUT exact-platform-present overrides this:** if the candidate HAS the SAME framework/platform named in the requirement — even via an old / small / student project (e.g. an old Android Native app for an "Android 기반 개발 경험" requirement) — that is a VALID match: `weak` or `adjacent` by depth (per the old/student-project rule), **NEVER `missing`**. `exact_only` only blocks DIFFERENT tools; it never denies credit for shallow-but-exact experience. Select that evidence_id.
- Only `missing` if there is no same-category evidence at all (for exact_or_same_category) / no exact evidence (for exact_only).
- In `explanation`, note which alternative matched and whether it was exact or same-category.

## Old / student / personal-project evidence (be precise, not absent)
- If the resume shows **real but old/student/personal** experience with the platform or skill (e.g. an old Android Native app), then for the **basic version** of that requirement (e.g. "Android app development experience") use `weak` or `adjacent` — **NOT `missing`** and **NOT `direct`**. Add a risk_note about the limited scope.
- Reserve `missing` for skills with **no supporting evidence at all** — e.g. AOSP / Android Framework internals / C/C++ / crash·ANR / system-level debugging when the resume does not mention them.

## For EVERY requirement (including preferred ones), output one row:
- `requirement_id`: copy from input
- `requirement_type`: copy from input ("critical"|"required"|"preferred"|"optional")
- `matched_evidence_ids`: array of `evidence_id` values (from the evidence list) that support it (may be empty). **IDs only — no quote text.**
- `match_level`: one of
  - "direct": evidence clearly and specifically satisfies the requirement
  - "adjacent": related/transferable but not a direct hit (e.g. Next.js experience for a "React" requirement)
  - "weak": only loosely related or unproven
  - "missing": no supporting evidence
- `confidence`: "high" | "medium" | "low"
- `explanation`: 1-2 sentences, why this match_level (you may reference evidence by id)
- `risk_note`: any caveat (e.g. "개인 프로젝트라 대규모 운영 경험으로 보긴 어려움"); "" if none

## Output
Return a JSON object: `{"matches": [ {"requirement_id": "...", "requirement_type": "...", "matched_evidence_ids": ["E3","E7"], "match_level": "...", "confidence": "...", "explanation": "...", "risk_note": "..."} , ... ]}` with exactly one row per requirement below. (Do NOT include any quote text; the system adds quotes from the selected ids.)

## Job
- company: {{COMPANY}}
- title: {{TITLE}}

## Requirements (one row required per item)
{{REQUIREMENTS}}

## Candidate evidence items (select by evidence_id; the system copies the exact_quote)
{{EVIDENCE}}

Return ONLY the JSON object.
````

### A-4. `rematch_evidence.md`
````text
You are doing a focused second-pass match for ONE job requirement against a fixed candidate's resume evidence.

A previous pass selected no usable evidence for this requirement. Look again carefully.

## Rules
- **Choose `evidence_id`(s) ONLY from the evidence list below. DO NOT write, paraphrase, or copy any quote text.** The system fills quotes verbatim from the ids you select.
- Only use ids that appear in the list. Never invent an id.
- Select an id if its content genuinely supports this requirement, even partially (transferable/adjacent counts — set match_level accordingly).
- If, after looking carefully, no evidence supports it at all, return an empty list with match_level "missing".
- No percentages, no pass probability. Output JSON only.

## Requirement
- requirement_text: {{REQUIREMENT_TEXT}}
- requirement_type: {{REQUIREMENT_TYPE}}
- requirement_nature: {{REQUIREMENT_NATURE}}
- alternatives (any one is enough, if non-empty): {{ALTERNATIVES}}

## Candidate evidence items
{{EVIDENCE}}

## Output (JSON only)
{ "matched_evidence_ids": ["E#", ...], "match_level": "direct|adjacent|weak|missing", "confidence": "high|medium|low", "explanation": "1 sentence" }
````

### A-5. `match_verifier.md`
````text
You are a **conservative verifier** for a requirement→evidence matching table. Your job is to catch exaggeration and downgrade weak matches. You NEVER upgrade a match.

## Mindset
Be skeptical. When in doubt, downgrade. Weigh the **depth, type, and recency** of the cited evidence against what the requirement actually demands.

## Evidence-aware rules (use evidence_type, strength, recency, source_section)
- A **2020 student/personal mobile app** is **weak or adjacent** evidence for a **basic Android app-development** requirement — NOT `direct`, but also **NOT `missing`** (the candidate did build a real Android app). Keep it at `weak`/`adjacent` with a scope caveat.
- That same old student app does **NOT** support **specialized low-level requirements** — Framework/HAL/AOSP/Native-C++/crash·ANR/system-level debugging. Keep those `missing` unless the resume explicitly shows them.
- **OR-groups (`alternatives`):** if any one alternative is satisfied, do NOT downgrade the row to `missing`/`weak` just because the other options are absent (e.g. having TypeScript satisfies a "TypeScript/Flow" group).
- **Same-category tool groups (`requirement_category` + `alternative_match_policy`):** same-category tools are transferable but NOT identical.
  - For `exact_or_same_category` (state_management / styling / data_fetching / build_tooling / testing): a DIFFERENT tool in the same category is a valid **`adjacent`** match — do NOT downgrade it to `missing` just because the exact library name differs (e.g. Zustand for a Recoil/Jotai state-management group; styled-components/Tailwind for an Emotion/Vanilla-extract styling group). Keep `direct` only if an exact alternative is in the resume.
  - Do NOT upgrade `adjacent` to `direct` unless the exact tool (or a clearly equivalent one) is explicitly in the resume.
  - For `exact_only` (frameworks like React): a different framework (Vue/Angular/Svelte) is NOT a same-category substitute — keep it `weak`/`missing`, never `adjacent`/`direct`.
  - HOWEVER, exact-platform evidence (the SAME framework/platform, even old/shallow — e.g. an old Android Native app for an "Android 개발 경험" requirement) is a valid `weak`/`adjacent` match. Do NOT push it to `missing` just because the experience is shallow or `exact_only` is set.
- A **production company internship in web development** is **strong** evidence for **frontend/web** roles.
- Personal/side project deployment supports **deployment experience**, but NOT large-scale production operation.
- Using **Next.js supports React experience** (direct/adjacent is fine), but does not prove deep React internals.
- A school assignment or short activity is NOT professional production experience unless the resume explicitly says so.
- An internship is real professional experience, but is typically narrower than senior-level requirements.
- Self-reported user counts on personal projects show shipping, but are weaker than company production scale.

## Do NOT infer the following unless there is EXPLICIT evidence in the resume
- C/C++ proficiency, Android Framework/AOSP knowledge, HAL, crash/ANR or system-level debugging, embedded/firmware work, large-scale cloud architecture.
- Listing "Android Native" for one old app does NOT imply Framework/AOSP/Native-C++/system-debugging skill.

## Checks for each proposed match
1. Does the cited evidence really support THIS requirement, given its type/strength/recency?
2. Is the claimed match_level exaggerated relative to what the evidence proves?
3. What is the honest level: `direct | adjacent | weak | missing`?
4. Should it be downgraded?

## Rules
- You may only keep or LOWER the match_level (severity: direct > adjacent > weak > missing). Never raise it.
- If a match cites no quote or off-topic evidence, push toward `weak` or `missing`.
- Output JSON only. No markdown, no commentary, no percentages, no pass probability.

## Output
`{"verified": [ {"requirement_id": "...", "match_level": "...", "confidence": "high|medium|low", "exaggerated": true|false, "downgrade": true|false, "verifier_note": "..."} , ... ]}`
Include one entry per requirement_id in the matches below.

## Candidate resume text (ground truth)
<<<RESUME
{{RESUME_TEXT}}
RESUME

## Candidate evidence items (with type / strength / recency / source)
{{EVIDENCE}}

## Proposed matches to verify
{{MATCHES}}

Return ONLY the JSON object.
````

### A-6. `listwise_rerank.md`
````text
You are a **listwise reranker** for job–candidate FIT. The candidate is FIXED; only the jobs vary.

## What you compare
- ONLY how well THIS candidate fits each job, based on the provided compressed matching tables.
- Use ONLY the provided matching evidence (requirement coverage counts, strong matches, gaps, risks).

## What you must IGNORE
- Company fame, brand, prestige, salary, perceived attractiveness, or general desirability.
- Anything not present in the provided matching data. Do not bring in outside knowledge about the companies.

## Judging guidance
- A job is a better fit when more of its `critical`/`required` requirements are matched "direct" with solid confidence, and it has fewer **core_prerequisite_gaps** and fewer serious risks.
- **core_prerequisite_gaps** are unmet PREREQUISITES (prior skills/experience the candidate must already have). These matter most — many unmet should push a job DOWN hard.
- **product_duty_gaps_not_blocking** are things the candidate would DO on the job (e.g. "build a POS"), not prerequisites. Do NOT penalize a job for these — they are not gaps in the candidate.
- **behavioral_gaps** (proactive, root-cause, collaboration, "grows with us") should mostly affect your explanation, NOT drive the ranking.
- Use **domain_alignment** (strong/adjacent/weak/mismatch): a `strong`-aligned role with matched core requirements should generally outrank an `adjacent`/`weak`/`mismatch` role that only clears soft requirements. Do not treat an `adjacent` role (e.g. an old student mobile app vs. a specialized device role) as a top fit on thin evidence.
- `invalid_matches` are requirements whose evidence was non-extractive and removed — treat them as NOT met.
- Preferred/optional coverage is a tiebreaker, not a primary driver.

## Output (JSON only, no markdown, no percentages, no pass probability)
{
  "ranking": [ {"job_id": "...", "reason": "1-2 sentence FIT-only justification"}, ... ],   // best fit first, include EVERY job_id exactly once
  "uncertainty_notes": "where the ranking is shaky or jobs are nearly tied"
}

## Compressed matching tables (the ONLY input)
{{JOBS}}

Return ONLY the JSON object.
````

### A-7. `pairwise_compare.md`
````text
You compare TWO jobs (A and B) for how well a FIXED candidate fits each, then pick the better FIT.

## Rules
- Judge ONLY candidate–job fit, using ONLY the provided compressed matching data for A and B.
- IGNORE company fame, brand, prestige, salary, and general attractiveness.
- Better fit = more `critical`/`required` requirements matched "direct" with good confidence, fewer **core_prerequisite_gaps** (unmet prior skills/experience), fewer serious risks.
- **product_duty_gaps_not_blocking** are on-the-job duties, NOT prerequisites — do not count them against a candidate.
- **behavioral_gaps** should mostly inform your reason, NOT decide the winner. Do not pick a job as better fit just because the other has weak behavioral evidence.
- Consider **domain_alignment**: prefer a `strong`-aligned role over an `adjacent`/`weak`/`mismatch` role when core requirements are comparably matched. Thin evidence (e.g. one old student app) for an `adjacent` role is not a strong fit.
- `invalid_matches` count as NOT met.
- If A and B are genuinely close, answer "tie".
- Output JSON only. No markdown, no commentary, no percentages, no pass probability.

## Output
{ "winner": "a" | "b" | "tie", "confidence": "high" | "medium" | "low", "reason": "1-2 sentence FIT-only justification" }

## JOB A
{{JOB_A}}

## JOB B
{{JOB_B}}

Return ONLY the JSON object.
````

## 부록 B. LLM 시스템 프롬프트 (`JSON_SYSTEM`, verbatim)

```
You are a careful, literal information-extraction and evaluation engine. You follow
instructions exactly, never invent facts, and output ONLY valid JSON with no extra text,
no markdown, and no code fences.
```