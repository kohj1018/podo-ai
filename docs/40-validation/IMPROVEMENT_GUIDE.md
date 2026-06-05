# 개선 가이드

> 본 문서는 Living Doc이다. 각 섹션 안에서 `### M1`, `### M2` 식의 마일스톤 단위 그룹핑을 권장한다.
> `/stabilize-milestone`이 reviewer 결과를 누적 기록할 때 마일스톤 헤더를 사용한다.

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

## 0. 요약

### M1 — /stabilize-milestone (2026-06-05)
- **졸업 가능: YES** — 모든 task done(17/17) · 통합 validate exit 0 · E2E 해당없음(Python 단독, `podo/` 미scaffold → Playwright 단계 비활성) · AC 매핑 52/52(100%) · P0 finding 0.
- 게이트 측정 경로(GS-1/GS-2/GS-3)는 동작·테스트됨(T-014/T-016/T-017). 단 *실데이터 게이트 수치*(실 LLM 호출·창업자 수기 라벨·100회 반복)는 미실행 — LLM fake-only는 M1 비범위의 명시된 oracle gap.
- reviewer(surface: code): P0 0 / P1 3 / P2 5 + ADR 후보 2. qa: [QA_FINDINGS `## M1`](QA_FINDINGS.md) (P1 2 / P2 4). **수렴 신호(신뢰도↑):** GS2_MIN_SAMPLE 비강제를 qa(QA-M1-001)·T-016 validation report·SPEC §10-3가 동시 지적.
- **Dependency hygiene:** `pip-audit`(uvx 1회) → **No known vulnerabilities found** ✅. `npm audit` 해당없음(pnpm repo + 루트 production JS deps 0 + TS 스택 미scaffold). 6개월 unused deps 판정 해당없음(신생 워크스페이스).
- **Deterministic preflight:** ADR-ref 전부 resolve · 내부 anchor(#arch-7-1/7-3/7-4·#design-2-colors·#adr-101-amend-1) 전부 존재 · FAC↔AC unmapped 0(20/20) · mode-label 불일치 0. Doc-link 외부검사 **skip**(markdown-link-check 미설치). ARCH §7-x `### Don'ts` 부재 → 5-4 grep skip(문서화된 milestone-level gap).

```
Telemetry — M1
- Tasks: 17 / 17 (100%)
- AC↔테스트 매핑: 52 / 52 (100%)
- FAC coverage: 20 / 20 (100%)
- Evidence Bundle 신뢰도: High 17 / Medium 0 / Low 0
- Validate exit code: 0
- Findings: P0 0 / P1 7 / P2 9
- Cross-stabilize 회귀 신호: 0건 (M1 = 첫 마일스톤, 선행 없음)
```

## 1. 우선순위

### M1
1. (P1) **GS-2 측정 신뢰성** — GS2_MIN_SAMPLE 강제 + `_is_grounded` 한계 명문화 (QA-M1-001/002, T-016). 게이트 정합 직결.
2. (P1) **캘리브레이션 상수/함수 SSOT 단일화** — DOM_RANK·_extract_json·_load_prompt 중복 제거 (REV-M1-001/002/007). silent numeric regression 차단(GS-1 보강).
3. (P1) **eval↔worker private 심볼 의존 정리 + 경계 ADR** (REV-M1-003).
4. (P1, 실질↓) Design-draft 라벨 정리 / Discovery insight 외부 증거 회수 (문서 상태 — 아래 §2 참조).
5. (P2) WHY 주석·네이밍·crawler 내결함성 정리 (REV-M1-004~008, QA-M1-003~006 → QA_FINDINGS).

## 2. 즉시 수정할 항목

### M1
(P0 없음.)

- **REV-M1-001** | P1 | [관측됨] [Clean-Code: Duplication] | linked: T-009,T-010 | status: open | `rerank_listwise.py:149-157`, `compare_pairwise.py:34-42`, `llm.py:29-42`
  - 발견: `_extract_json`("code-fence 제거 → greedy shrink") 본문이 3곳 복제 — 주석이 스스로 "동일 로직" 시인.
  - 근거: rule-of-3 위반. JSON 파싱 정책을 한 곳만 고치면 나머지 2곳 무음 방치.
  - 권장: `ai/worker/src/worker/_json_util.py` 단일 `extract_json()` → 3곳 import(순환 import 없음).
- **REV-M1-002** | P1 | [관측됨] [Clean-Code: Duplication] | linked: T-003,T-009 | status: open | `rerank_listwise.py:22`, `rank_aggregate.py:364`
  - 발견: `DOM_RANK={"strong":3,"adjacent":2,"weak":1,"mismatch":0}` 캘리브레이션 상수가 별도 2곳 동일 값(rerank 주석이 중복 인정).
  - 근거: 한 쪽 drift 시 listwise fallback 삽입 순서 ↔ BT-aggregate 정렬 키가 *무음*으로 어긋남 — GS-1 게이트가 못 잡을 수 있는 silent regression.
  - 권장: `rank_aggregate.DOM_RANK` 단일 공개 → `rerank_listwise`가 import(현재 단방향, 순환 없음).
- **REV-M1-003** | P1 | [관측됨] [Arch-debt] [ADR-candidate] | linked: T-014,T-015 | status: open | `regression.py:21`, `eval_resumes.py:23` ← `worker.verify_matches._build_haystack`/`_is_extractive`
  - 발견: eval 레이어가 worker private(`_` 접두) 심볼을 직접 import. verify_matches에 "T-014가 재사용 — 공개 유지" 주석만 있고 계약은 주석으로만 강제(취약).
  - 근거: ARCH §3-2상 eval→worker 의존은 허용이나 private 직접 노출은 worker 내부 리팩토링 시 eval 무음 브레이킹.
  - 권장: 공개 alias(`build_haystack`/`is_extractive`) 또는 `worker.grounding` 분리 노출 + **경계 ADR**(§4 후보 1).
- **[Design-draft]** | P1 | [관측됨] | linked: docs/20-system/DESIGN.md | status: open (실질 우선순위 ↓)
  - 발견: ADR-027#amend-3 절차상 DESIGN.md `status=draft` + UI 신호(Next.js 스택·ARCH §7-4·F2 Feed) → 기록 대상.
  - 실상: DESIGN.md는 colors/components/원칙까지 *충실히 작성됨* (`/bootstrap-design` 이미 수행). 또한 M1은 UI 0줄 구현(Feed 비범위) → 5-2 raw-hex grep / 5-3 컴포넌트 inventory drift **발견 0**(변경 파일이 .py/.md뿐, `podo/` 미scaffold).
  - 권장: 실제 액션 = status 라벨 정리(또는 프로젝트 전반 draft 컨벤션 유지). **`/bootstrap-design` 재실행 불필요** — 휴리스틱 false-positive에 가까움.
- **[Discovery-insight]** | P1 | [관측됨] | linked: docs/10-charter/DISCOVERY.md §15 | status: open
  - 발견: Insight Backlog 미반영(status=open) 3건 — I-1(신뢰 thesis "틀린 점수 > 근거 없는 점수") / I-2(5단계 밴드) / I-3(누락0 투명성). (ADR-035#amend-2 시그널 4)
  - 실상: 셋 다 M1 게이트-우선 설계(F-001 GS-1/GS-2, F-002 CoverageState)에 *구조적으로 이미 반영*. open인 이유는 §15 주석대로 *외부 증거 미수집*(인터뷰/라벨링).
  - 권장: 액션 = "스코프 회수"가 아니라 외부 증거 수집 후 promote. `/plan-workitem`이 회수.
  - 참고: DISCOVERY↔Charter drift(시그널 1~3)는 **clean** — Charter mtime이 DISCOVERY보다 최신 + §2.1/§3.1/§9 모두 채워짐 → drift P1 미발생.

## 3. 권장 리팩토링

### M1 (P2 — 전부 behavior-preserving)
- **REV-M1-004** | P2 | [Clean-Code: WHY-comment] | T-003 | `rank_aggregate.py:188-191` — `STATUS_WEIGHT.get(...,0.7)` unknown-status default의 calibration WHY 주석 추가.
- **REV-M1-005** | P2 | [Clean-Code: WHY-comment] | T-003 | `rank_aggregate.py:271-279` — 레벨 경계 0.80/0.62/0.42/0.22 calibration 출처 WHY(임의 변경 시 GS-1 F1~F5 레벨 불변식 회귀 위험).
- **REV-M1-006** | P2 | [Clean-Code: WHY-comment] | T-003 | `rank_aggregate.py:373-374` — BT `iters=300, prior=0.5` calibration 근거 1줄(BT score가 aggregate 정렬 키에 직접 사용).
- **REV-M1-007** | P2 | [Clean-Code: Duplication] | T-006,T-007,T-008 | `parse_resume.py`·`parse_job.py`·`matching.py`·`verify_matches.py` — `_load_prompt`/`_render` 4파일 동일 복제 → `worker/_prompts.py` 추출(rule-of-3 충족).
- **REV-M1-008** | P2 | [Clean-Code: Naming/mutable-default] | T-013 | `selection.py:117-119` — `USER_PRIMARY/SECONDARY_DOMAINS` 모듈 전역 mutable default(테스트 격리 위험) → `tuple`/`frozenset` 고정 또는 주석 명확화.

> qa P2(QA-M1-003 τ-a/τ-b · QA-M1-004 불변식 #8 잠재 vacuous · QA-M1-005 toss 상세 fetch 중단 · QA-M1-006 build_pool tier 혼합)는 [QA_FINDINGS `## M1`](QA_FINDINGS.md)에 기록.

## 4. 보류 항목

### M1 — ADR 후보 + instruction 개선 후보
**ADR 후보 (M1 중 내려진 결정인데 ADR 부재 — layer 경계·의존성 규칙 변경은 ADR-006 정책상 ADR 대상):**
1. **eval↔worker 경계 규칙 ADR** (REV-M1-003): "eval은 worker 공개 심볼만 import한다. private(`_`) 심볼이 필요하면 공개 alias를 제공한다." — 현 ARCH §3-2는 *방향*만, private 접근 세칙 부재.
2. **worker shared-util 경계 ADR** (REV-M1-001/007): `_extract_json`·`_load_prompt/_render` 등 cross-module 공통 util 위치 규칙 부재 — "순환 import 방지" 로컬 복사 허용 vs `worker._util` 집중 결정 필요.
> 위 2건은 모듈 경계·의존성 규칙 후보 → **architect 검토 권장**(메인 세션 호출, 본 skill은 텍스트 제안만).

**Instruction 개선 후보 (ADR-022 ratchet evidence label 부착 — *보고만*, AGENTS.md/agent/skill body 자동 수정 X):**
- [관측됨 · 본 세션 2회] qa subagent가 *광범위 다영역* 위임 프롬프트에서 조사만 반복하고 finding 블록을 turn 내 미출력(각 35·27 tool-use). 3차에 "Read-only · ~10 reads · output-first · pytest 금지(이미 green)" 제약을 주자 12 tool-use에 정상 출력. 후보: `qa.md`(또는 stabilize 단계 4 위임 프롬프트)에 *tool-call 예산 + finding-block-before-turn-end self-check* 명문화. (동일 제약에서 reviewer는 정상 출력 — qa 쪽 고유 friction.)
- [관측됨] 본 하니스에 SendMessage 부재 → paused subagent 재개 불가. 위임 프롬프트는 *self-contained + output-first*를 디폴트로 둬야 안전(재spawn 비용 회피).

## 5. Repair decision log

`/repair-plan`이 feature(F-NNN) 또는 milestone(M-N) 단위로 호출됐을 때 본 라운드의 P0+P1 결정을 영속 기록하는 자리 (ADR-047 D7 durable correction history + D1 inspectability). `## 2. 즉시 수정할 항목` / `## 3. 권장 리팩토링`과 의미 분리 — 이 두 섹션은 *open items*이고 본 섹션은 *closed records*(지나간 판단).

- task scope (T-NNN) 결정은 해당 task `## 8. 메모`에 직접 append — 본 섹션 아님.
- ID 컨벤션: `<workitem-id>-repair-<N>` (예: `F-001-repair-1`, `M1-repair-2`).
- evidence label은 기본 `[관측됨]` (finding 자체는 리뷰어의 *로컬 문서 관측*에서 나옴 — cross-review 방식의 외부실증은 ADR-038 본문이 owning).
- 형식은 본 파일 `## 항목 스키마` SSOT 따름.

<!-- 마일스톤별 그룹핑(`### M1`, `### M2`)은 `/repair-plan`이 *첫 호출 시* 해당 마일스톤 헤더를 자동 신설하고 그 아래에 append. /stabilize-milestone은 본 sub-section을 *추가하거나 수정하지 않음* — /repair-plan만 직접 append. 본 ## 5 sub-section은 *신설 시 헤더 + 본 안내 주석만* 두고 `### M-N` 그룹은 비워둔다. -->
