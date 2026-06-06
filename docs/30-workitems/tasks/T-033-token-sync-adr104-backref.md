# T-033-token-sync-adr104-backref

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
M1→M2 누적 문서 부채 중 (3) `globals.css` 색상 토큰 SSOT 동기와 (4) ADR-104 역참조 주석 부착을 회수한다. globals.css CSS 변수가 DESIGN §2 semantic 토큰과 어긋나면 raw hex drift 표면이 되고, ADR-104 backref 누락은 변경 시 동기 갱신 추적을 막는다(F-012 §2).

## 2. 작업 범위
- `podo/apps/web/app/globals.css` `:root` CSS 변수 이름 ↔ DESIGN §2 semantic 토큰 이름 1:1 정합 확인·동기.
- ADR-104 §Surfaces 대상 파일에 `# per ADR-104` 역참조 주석 부착 — 현재 3건 → 6건.

## 3. 구현 항목
1. `podo/apps/web/app/globals.css:6-27` — 현재: `:root`에 `--ink`·`--paper`·`--band-{1..5}-fill`·`--band-{1..5}-ink`·`--brand-gradient`·`--coverage-on-bg`·`--coverage-on-border`·`--faint` 정의(raw hex는 여기만) → 변경: DESIGN §2 semantic 토큰 이름과 대조해 불일치 var 이름을 DESIGN §2 기준으로 동기(또는 globals.css에만 있는 토큰을 DESIGN §2에 등록). → 확인: globals.css var 이름 집합과 DESIGN §2 토큰 이름 집합 diff 0. (AC-1)
2. (1)에서 DESIGN §2에 미등록 토큰 발견 시 — 현재: 코드 실측 토큰 > 설계 레지스트리 → 변경: DESIGN §2에 해당 토큰 1줄 등록(인벤토리 stale 보강). → 확인: 양방향 diff 0. (AC-1)
3. ADR-104 backref 현황 — 현재: `grep -rl "per ADR-104" ai/worker/`가 3건(`_prompts.py`·`_json_util.py`·`rank_aggregate.py`) → 변경: ADR-104 D2(JSON 추출) 소비자 3개에 `# per ADR-104` 주석 부착: `ai/worker/src/worker/compare_pairwise.py`·`llm.py`·`rerank_listwise.py`(각 `extract_json`/`_json_util` import 라인 근처). → 확인: `grep -rl "per ADR-104" ai/worker/` = 6건. (AC-2)

## 4. 제외 항목
- 새 토큰 설계·새 primitive 추가(DESIGN cross-check 시 architect/`bootstrap-design` 권장). · 컴포넌트 raw hex 도입. · ADR-104 D2/D3 *코드* 재중앙화(F-011/T-030·T-031에서 완료 — 본 task는 backref 주석만). · 용어 치환(T-032).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
globals.css CSS 변수가 DESIGN §2 semantic 토큰과 1:1 정합하고, ADR-104 §Surfaces 대상 파일 6건에 `per ADR-104` 역참조 주석이 존재한다.

## 6. Acceptance Criteria
- AC-1 [Given] `globals.css` `:root` 변수 집합과 DESIGN §2 semantic 토큰 이름 집합 [When] 대조·동기 [Then] 두 집합의 이름 diff가 0이다(globals.css 미등록 토큰은 DESIGN §2에 등록 완료).
- AC-2 [Given] ADR-104 §Surfaces 대상 파일 [When] D2 소비자 3개(`compare_pairwise.py`·`llm.py`·`rerank_listwise.py`)에 `# per ADR-104` 부착 [Then] `grep -rl "per ADR-104" ai/worker/`가 6개 파일을 반환한다(기존 3 + 신규 3).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → 토큰 이름 대조: globals.css `--*` 추출 ↔ DESIGN §2 토큰 목록 set diff = ∅
- AC-2 → grep 검증: `grep -rl "per ADR-104" ai/worker/ | wc -l` = 6

## 6-2. TDD opt-out
- 사유: 선언적 정합(토큰 이름 매칭 + 주석 부착) — grep/set-diff가 결정적 oracle. 코드 동작 변경 0.
- Follow-up task: 해당 없음(문서·주석 정합 task).

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Feature: [F-012-doc-reconcile](../features/F-012-doc-reconcile.md)
- Design: [DESIGN ## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md)

## 8. 메모
- 해석 확정: AC-2 "6건" = 기존 3(`_prompts`·`_json_util`·`rank_aggregate`) + D2 JSON 소비자 3(`compare_pairwise`·`llm`·`rerank_listwise`, ADR-104 근거상 silent-drift 위험 최상위). D3 프롬프트 소비자 4개(parse_resume/parse_job/verify_matches/matching)는 본 6건 밖 — 더 엄격한 커버리지 원하면 후속(scope creep 회피).
- globals.css:9 주석 "적합도(합격가능성)"의 "합격가능성"은 코드 주석 — T-032 doc 치환 scope 밖이나 정합 차원 relabel 권장(선택).
- repair-plan 2026-06-07 [default] P1 Plan-dep: Adopt — depends_on:[T-032] 추가(둘 다 DESIGN.md write → write race 제거, 병렬 wave 분리).

## 9. 의존성
- depends_on: [T-032]   # T-032가 DESIGN.md term 편집 → 같은 파일 write race 회피(repair-plan P1-dep)
- read_set: ["docs/20-system/DESIGN.md", "ai/worker/src/worker/**"]
- write_set: ["podo/apps/web/app/globals.css", "docs/20-system/DESIGN.md", "ai/worker/src/worker/compare_pairwise.py", "ai/worker/src/worker/llm.py", "ai/worker/src/worker/rerank_listwise.py"]
- verifier: "grep -rl \"per ADR-104\" ai/worker/"
- # T-032 이후 순차(둘 다 DESIGN.md write — write_set 교집합, 같은 wave 금지)
