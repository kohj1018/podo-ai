# QA 결과

> 본 문서는 마일스톤 단위로 누적된다. 각 마일스톤별 P0/P1/P2/관찰 메모를 중첩 헤더로 분리한다.
> 마일스톤이 정해지지 않은 초기 프로젝트는 `## 일반` 한 묶음만 둔다.

## 항목 스키마

각 발견 항목은 다음 형식으로 박는다.

- 필수 4필드: `ID | severity | evidence label | linked workitem`
- 권장 2필드: `status | decision`
- evidence label은 [boilerplate/ADR-022](../90-decisions/boilerplate/ADR-022-ratchet-principle.md)의 `[관측됨]` / `[외부실증]` / `[가설]` (+ 합성 표기) 중 1개.

예시:
```
- **F-M1-001** | P1 | [관측됨] | linked: T-002 | status: open
  - 발견: FAC-4 → T-002:AC-N 매핑 누락, validate 통과인데 spec gap.
  - 결정: 다음 라운드 plan에서 T-002에 AC-3 추가.
```

## 다운스트림 마이그레이션 가이드
이 보일러플레이트는 빈 템플릿이라 적용 즉시 변경 가능하다. 그러나 본 보일러플레이트로 시작한 다운스트림 프로젝트가 이미 평면 양식의 누적 데이터를 가질 수 있다.
- (1) 기존 평면 항목들을 `## M1` 또는 `## 일반` 한 묶음으로 감싼다(편집 1회).
- (2) 다음 회차부터 새 마일스톤 헤더로 누적한다.

---

## M1

> `/stabilize-milestone M1` (2026-06-05) qa 위임 결과. 대상: T-001~T-017 (알고리즘 + 오프라인 평가 포트, Python `ai/` + `crawler/`). 통합 validate exit 0 기준 위에서 *lint/type/unit이 못 잡는* 회귀·엣지·게이트 정합을 점검. **P0 0건 → 졸업 차단 없음.** finding 전수 기록(ADR-046#d3).

### P0
없음. (cache.py 키는 `model + system + user + schema_version` 명시 문자열만 — 시간/랜덤/env/dict-iteration 혼입 없음. GS-1 결정성 구조 충족.)

### P1
- **QA-M1-001** | P1 | [관측됨] | linked: T-016 | status: open | `ai/eval/src/eval/gates.py:95` + `golden_pairs.py`
  - 발견: `GS2_MIN_SAMPLE=30`이 정의만 되고 `GS2Gate.measure()`에서 표본 수 게이트로 강제되지 않는다. 표본 0~29건에도 `gate_pass=True` 가능.
  - 근거: SPEC §10-3 "표본 ≥30 requirement 중 hallucination ≤2%". 표본 1건(0/1)이면 ratio 0% → 통계적으로 무의미한데 통과. (T-016 validation report의 oracle gap과 **수렴 — 신뢰도 상승**.)
  - 결정/권장: `measure()` 진입 시 `total < GS2_MIN_SAMPLE → gate_pass=False, details=["sample_too_small"]`. `/repair-workitem T-016` 또는 M2 신규 task.
- **QA-M1-002** | P1 | [관측됨] | linked: T-016 | status: open | `ai/eval/src/eval/gates.py:53-70`
  - 발견: `_is_grounded`가 "내용 토큰(3자+) 과반이 JD에 개별 존재"면 grounded 판정. 토큰들이 JD 곳곳에 흩어져만 있어도(문장 단위 부재) grounded=True → 파라프레이즈/재조합 requirement가 hallucination으로 안 잡힐 수 있음(GS-2 false-negative).
  - 근거: GS-2는 "JD 원문에 실재하지 않는 requirement" 탐지가 목적인데 토큰 개별 존재 ≠ 문장 실재. (T-016 report가 "휴리스틱 프록시"로 명시한 설계결정의 *측정 위험* 정량화.)
  - 결정/권장: 짧은 요구(≤15토큰) bi/tri-gram 조건 추가 또는 한계를 `GS2Gate` docstring에 "known limitation"으로 명문화 후 accept-with-note. M2에서 결정.

### P2
- **QA-M1-003** | P2 | [관측됨] | linked: T-017 | status: open | `ai/eval/src/eval/a3_tau.py:96-101`
  - 발견: `compute_tau`가 τ-a(동점 쌍을 분모에서 제외) 구현. tie 다발 시 τ-b보다 +0.1~0.2 과대추정 가능 → A-3 임계값(0.6/0.7) 과통과 위험. 주석에 "τ-b 단순화" 명시는 있으나 Charter §9 임계값이 τ-a 기준 교정인지 불명확.
  - 결정/권장: Charter §9에 τ-a/τ-b 기준 명시 + `TauReport`에 tie 비율 노출. 실데이터 A-3 측정(T-017 §6-2 opt-out) 시 재검토.
- **QA-M1-004** | P2 | [관측됨] | linked: T-014 | status: open | `ai/eval/src/eval/regression.py:120-135`
  - 발견: 불변식 #8 `mismatch_priority_guard`는 `not mismatch_ranks or not nonmismatch_ranks → pass` 단락(short-circuit)을 갖는다. **현 픽스처(`original_3_jds.json`)는 marketing=mismatch + frontend/android=non-mismatch 보유 → 현재는 실제로 검사됨(vacuous 아님, 확인 완료).** 단 픽스처에서 mismatch 공고가 빠지면 무음 vacuous-pass가 되는 *잠재* 위험.
  - 결정/권장: 픽스처에 mismatch 1건 상시 보장(또는 빈 집합 시 fail). 회귀 픽스처 변경 시 점검. M2 accept-with-note.
- **QA-M1-005** | P2 | [관측됨] | linked: T-012 | status: open | `crawler/src/crawler/fetch_jobs.py:148-167`
  - 발견: 토스 *상세* fetch가 `raise_for_status()`라 단건 502/404가 전체 루프를 예외 중단 → 이미 파싱된 공고도 손실. `parse_toss_detail`의 `[content_missing]` fallback(비치명 skip 설계)과 일관성 불일치.
  - 결정/권장: 상세 fetch를 `try/except httpx.HTTPStatusError`로 감싸 단건 skip+log. (CoverageState 연동은 M1 비범위.) `/repair-workitem T-012` 후보.
- **QA-M1-006** | P2 | [가설] | linked: T-013 | status: open | `crawler/src/crawler/selection.py:189-206`
  - 발견: `build_pool` round-robin이 회사 버킷 단위로만 순환 → 한 회사가 여러 tier 공고를 가지면 pool 앞자리에 tier 혼합이 생겨 tier 정렬 효과가 희석될 수 있음.
  - 근거/완화: 단 `select_balanced`가 이후 tier 버킷으로 재분류하므로 최종 선택 결과에는 영향 없을 가능성 높음([가설] — 실데이터 미확인).
  - 결정/권장: tier 내 독립 round-robin 또는 "pool 순서는 select_balanced 무관" 근거로 accept-with-note.

### 관찰 메모
- `cache.py make_key` — 결정론 조건 완전 충족(sha256, 명시 입력만). env(SCHEMA_VERSION 등)은 모듈 로드 시 1회 고정.
- `verify_matches.py` — `missing→missing` DOWNGRADE_MAP 정의로 중복 강등 없음. 정상.
- `rank_aggregate.py aggregate` — 최종 tie-break가 job_id 알파벳 순 → 완전 결정론. mismatch 캡(role_evidence=0 → cap=1) 명시적.
- `a3_tau.py` — n<2 guard 정상, small-sample tau=0.0 → verdict=NOGO 안전.
- `selection.py select_balanced` — `selected[:limit]` 최종 슬라이스 + `used_ids` 중복 방지 정상.

## 일반

### P0

### P1

### P2

### 관찰 메모
