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

### M2 — /stabilize-milestone (2026-06-06)
- **졸업 가능: NO (근소, 초판) → 재grade YES (Fix round 2, 2026-06-06)** — 14/14 task done · 통합 validate exit 0(134 passed / 15 skipped) · **E2E exit 0**(`pnpm e2e` 메인 세션 실측: crawl(fixture)→score(웜캐시)→api 서빙→assert scored 6/held 0/양 소스) · AC 매핑 32/32(100%) · **QA_FINDINGS 코드결함 P0 0**. 초판 미충족 2건 모두 회수:
  - **#3 E2E Pass — 미충족(현 커밋 상태로 fresh-clone 재현 불가):** (a) `app.enableCors()`(web:3000→api:3001 필수)가 **uncommitted**(`main.ts`), (b) `.cache/llm`이 **gitignored** + 무키 score용 fixture/오케스트레이션 부재 → 무키 fresh clone은 전 공고가 cache miss→**held**(점수 0건)라 "적합도 5단계 렌더" done-line 불성립(T-023 §8이 "무키 결정성은 웜캐시/fake 필요 — E2E 오케스트레이션 소관"이라 명시), (c) **단일 crawl→score→feed 오케스트레이션 명령·runbook 부재**(README는 "next: /plan-workitem M1"·구 "pass likelihood" 용어로 stale), (d) `nest-cli.json`·`tsconfig.build.json` untracked. *per-task validator는 DB-path 유닛(T-021/022/026/027 DATABASE_URL 주입 라이브 green)·UI(T-028/029 RTL)를 커버하나 통합 fresh-clone E2E는 자동 게이트로 미실증.* **→ 회수됨(Fix round 2, 26aa0c9/4ad8ca7):** 결정적 crawl fixture + 50-entry 웜캐시(`LLM_CACHE_DIR`) + 단일 오케스트레이션 `scripts/e2e.mjs`(`pnpm e2e` exit 0 실측) + CI `e2e-smoke.yml`(무키) + README runbook.
  - **#6 (선택) GS-1-through-DB — at risk:** QA-M2-001(pending_job_ids JSONB 배열 순서 비결정) — 무키 E2E(전부 held) 경로에서 상시 노출. report.py:52 one-line `sorted()`로 닫힘. **→ 회수됨:** keyed↔keyless 재채점 result **byte-identical**(`3a4680f5`) 실측(Fix round 2).
- **reviewer(code): P0 0 / P1 0 / P2 6** — **F-011이 M1 부채를 깨끗이 해소 확인**(REV-M1-001/002/007 `extract_json`·`load_prompt`/`render` 단일화 + REV-M1-002 `DOM_RANK` SSOT + REV-M1-003 eval private-import 0). reviewer(design): 메인 세션이 design subagent의 P0 2건(FitScoreRing ink·CoveragePanel error)을 검증 후 **P1로 하향**(graduation P0 게이트는 QA_FINDINGS 기준이므로 무관, but 과대평가 회피). qa: [QA_FINDINGS `## M2`](QA_FINDINGS.md) (P0 0 / P1 1 / P2 7). **수렴(신뢰도↑):** QA-M2-001 결정성 hole을 qa subagent·메인 세션이 독립 발견.
- **Dependency hygiene:** `pip-audit`(uv export → uvx, 1회) → **No known vulnerabilities found** ✅ (로컬 workspace pkg `core/eval/worker/crawler`는 PyPI 부재로 skip — 정상). `pnpm audit --prod` → **22건 (high 8 / moderate 12 / low 2)** — 주범 `next`(<15.5.16, 14 advisories) + `@nestjs/common`·`@nestjs/core`. → 아래 §2 P1. 6개월 unused deps 해당없음(신생 monorepo).
- **Deterministic preflight:** ADR-ref 전부 resolve(M2 신규 doc은 기존 ADR만 인용 · 미존재 boilerplate#는 Reserved/Parked/Dropped 표 · bare `ADR-1`=`ADR-1NN` 템플릿 placeholder FP) · anchor(#arch-7-1/3/4 · #design-2-colors/7-components) 전부 존재 · FAC↔AC unmapped 0(27/27). **ADR-104 Surfaces 등재 6 usage-site backref 누락 → 아래 §2 P1.** globals.css `--ink`(#2a2630)·`--paper`(#fffbf7)가 DESIGN §2-1 SSOT(#2B2433 / #FFFBF6)와 drift → §2 P1(미세). raw-hex 컴포넌트 0(globals.css=토큰 instantiation 층). Doc-link 외부검사 **skip**(markdown-link-check 미설치). ARCH §7-x `### Don'ts` header 부재 → 5-4 grep skip(문서화된 milestone-level gap — 소유권·read-only·opaque 경계는 per-task validate + reviewer가 커버).
- **DISCOVERY↔Charter staleness:** mtime drift 없음(Charter가 DISCOVERY보다 최신). 단 **용어 divergence 확인 — M2 결정 "적합도 5단계" ↔ Charter/DISCOVERY "합격가능성"**(Charter 6× · DISCOVERY 12×) → §2 P1 reconcile(M2 §7 · F-010 §12 열린 질문과 정합). DISCOVERY §15 Insight Backlog I-1/I-2/I-3가 **M2 F-010에서 실제 구현됐는데 status=open 잔존** → §2 P1 promote.

```
Telemetry — M2
- Tasks: 14 / 14 (100%)
- AC↔테스트 매핑: 32 / 32 (100%)
- FAC coverage: 27 / 27 (100%)
- Evidence Bundle 신뢰도: High 14 / Medium 0 / Low 0
- Validate exit code: 0 (134 passed / 15 skipped) · E2E exit 0 (`pnpm e2e` 메인 세션 실측)
- Findings: P0 0 / P1 9 / P2 18  (초판 P0=E2E fresh-clone gap → Fix round 2 회수; QA_FINDINGS 코드결함 P0 = 0)
- Cross-stabilize 회귀 신호: 2건 — [Design-draft]·[Discovery-insight]가 M1→M2 재등장(patterned doc-state drift: M1이 권고한 DESIGN status 정리·insight promote·용어 reconcile가 마일스톤 간 미적용 — M3 전 회수 권장)
- 재grade (Fix round 2, 2026-06-06): 졸업 가능 NO→**YES**. graduation §5 6/6 충족(task done·validate exit 0·E2E exit 0·AC 100%·P0 0·GS-1-through-DB byte-identical)
```

### M3 — /stabilize-milestone (2026-06-07)
- **졸업 가능: NO (초판, 단일 차단 §5 #3) → Fix round로 §5 #3 closed → 정식 재grade (2026-06-07) YES.** 10/10 task done · 통합 validate exit 0(TS 32 passed[api 17/web 15, 4 jsdom-skip] / Python 134 passed, 17 DB-gated skip — 본 재grade 세션 재측정) · **E2E exit 0**(`pnpm e2e` 업로드 경로 *본 세션 실측*: upload `resume_id=14`→마스킹 placeholders=5→웜캐시 채점 `ranking_run id=19`→실 masker PII scan 0/5 literal→feed scored 6/held 0/toss+daangn) · AC 매핑 21/21(100%) · FAC 17/17(100%) · **QA_FINDINGS 코드결함 P0 0** · **PII Safety Pass green**(실 masker end-to-end + 하류 6표면 literal scan 0, DB 실증) · **doc reconcile 핵심표면 완료**(용어 grep DISCOVERY/Charter/DESIGN/F-001 = 0 · Insight I-1 done/I-2·I-3 planned+linked). **QA-M3-006(오라클 갭) resolved.** 재grade는 app 코드 무변경(Fix round=E2E 하니스+웜캐시+docs)이라 qa/reviewer 전수 재위임 생략 — 초판 finding 유지 + Fix-work 직결 단일 finding만 전이.
  - **초판 미충족 §5 #3** (stabilize report-only라 차단): `pnpm e2e`가 seed 경로(`uv run python -m worker`)로만 채점 → 업로드→마스킹→`resume_id` 채점→feed 경로 미배선. **→ Fix round(커밋 `f1f17df`)로 회수**: e2e.mjs 업로드 경로 재배선 + `e2e_pii_scan.py`(실 masker end-to-end scan) + 업로드 fixture 웜캐시 재생성(+47). 무키 `pnpm e2e` exit 0 실측(scored 6/held 0). §2 M3-E2E-001 closed 참조.
- **단일 미충족 = §5 #3:** `scripts/e2e.mjs`가 seed 경로로만 채점(`uv run python -m worker`, phase 4)하고 **업로드→마스킹→`resume_id` 채점→feed 경로를 자동 게이트로 미실증**. 웜캐시(49 entries)도 seed 기반(마스킹 fixture 미반영). M3 done-line의 핵심("업로드 경로가 scoring loop에 연결되는가")이 E2E로 미증명. **M2-E2E-001과 동형**(M2 초판 NO → 별도 Fix round 코드 작업 → 재grade YES). stabilize는 report-only라 e2e 배선·웜캐시 재생성을 *직접 못 함* → 아래 §2 M3-E2E-001(P0 후속, main-session/`/repair-workitem`).
- **reviewer(code): P1 4 / P2 5** — [Arch-iface-7-3] subprocess 오케스트레이션 ADR 미신설(REV-M3-002), [Arch-iface-7-1] manual validation vs §7-1 컨벤션(REV-M3-001), evidence-summary TS↔Python 이중 파싱(REV-M3-003), controller SRP(REV-M3-004). **reviewer(design): 메인 세션이 design P0 3건(label/aria-busy/role=region 미구현)을 검증 후 P1 하향** — graduation P0 게이트는 QA_FINDINGS 기준이라 무관 + M3=로컬 단일사용자 pre-deploy + F-015 §8 Lighthouse a11y "선택" 표기. 단 셋은 F-015 §8-1 명시 요구이나 *어느 task AC에도 미매핑* → [Spec-gap]. qa: [QA_FINDINGS `## M3`](QA_FINDINGS.md)(P0 0 / P1 1 / P2 5). **수렴(신뢰도↑):** [Arch-iface-7-3]=T-037 report+REV-M3-002 · [Arch-iface-7-1]=T-034 report+REV-M3-001 · evidence-summary divergence=QA-M3-004+REV-M3-003.
- **Dependency hygiene:** `pip-audit`(uv export→uvx, 로컬 editable 필터) → **No known vulnerabilities found** ✅. `pnpm audit --prod`(podo/) → **22건 (high 8 / moderate 12 / low 2)** — `next`(<15.5.16) + `@nestjs/*`. **M2 [Dependency] 재등장**(deferred "별도 task") → 아래 §2 P1. 6개월 unused deps 해당없음.
- **Deterministic preflight:** ADR-ref 전부 resolve(**ADR-105 신규 존재 ✅ status=accepted · ARCH §8/§10 backref 실재** — T-036 AC-3 충족). FAC↔AC unmapped 0(17/17). 용어 grep: **DISCOVERY/Charter/DESIGN/F-001 = 0건 ✅**(F-012 reconcile 성공). 잔여: **ARCH §6(glossary)·§7-4 "합격가능성 밴드" 2건**(T-032 scope 밖 — ARCH 미포함) + **DESIGN_RESEARCH 2건**(연구 doc) → 아래 §3 P2. raw-hex: 컴포넌트 .tsx 0(globals.css `:root`만 = 토큰 instantiation 층, 5-2 제외 대상 동형). markdown-link-check 미설치 → Doc-link 외부검사 **skip**. mode-label 불일치 0. ARCH §7-x `### Don'ts` 부재 → 5-4 grep skip(문서화된 gap).
- **DISCOVERY↔Charter staleness:** signal 1 firing(DISCOVERY mtime 01:58 > Charter 01:50) — **단 F-012가 방금 reconcile 수행 + 용어 grep으로 Charter 본문 clean 확인** → benign edit-ordering(Insight promote가 Charter snapshot 후 DISCOVERY-only 편집, §15는 Charter 미스냅샷). *content drift 아님* → 아래 §3 P2(저신뢰). **Insight backlog 0 open**(I-1 done/I-2·I-3 planned) → 미반영 인사이트 신호 0 — **M1→M2 [Insight-backlog] 재발 해소**. (status 정리: DISCOVERY/Charter `## 0. Status`는 여전히 `draft` — F-012 §4 "status 현행화" scope가 어느 task AC에도 미포함 → §3 P2 minor.)
- **헤드라인:** M1→M2 patterned doc-drift 4종([Insight-backlog]·[Design-token-drift]·[Surface-backref]·용어 divergence)이 **F-012/T-032/T-033으로 실제 해소**(반복 권고만 하던 부채를 milestone 첫 feature로 흡수한 효과). 잔존 cross-stabilize 회귀는 **[Dependency] 1종**(deferred dep bump)뿐 + [Design-draft] label 약한 잔존.

```
Telemetry — M3 (정식 재grade 2026-06-07 — 졸업 가능 YES)
- Tasks: 10 / 10 (100%)
- AC↔테스트 매핑: 21 / 21 (100%)
- FAC coverage: 17 / 17 (100%)
- Evidence Bundle 신뢰도: High 5 (T-033·035·038·039·041) / Medium 5 (T-032·034·036·037·040) / Low 0
- Validate exit code: 0 (TS 32 passed[api 17/web 15, 4 jsdom-skip] / Python 134 passed, 17 DB-skip — 본 재grade 세션 재측정) · **E2E exit 0** (`pnpm e2e` 업로드 경로 본 세션 실측: upload resume_id=14→mask placeholders=5→웜캐시 score ranking_run id=19→실 masker PII scan 0/5 literal→feed scored 6/held 0/toss+daangn)
- Findings: P0 0 (M3-E2E-001 = §5 #3 업로드 E2E gap → **closed 커밋 f1f17df + 재grade 실측**; QA_FINDINGS 코드결함 P0 = 0) / P1 6 open (QA-M3-006 → resolved; 잔여 [Arch-iface-7-3]/ADR-106·[Arch-iface-7-1]·[Design-a11y]·[Dependency]·evidence-summary 동기·[Spec-grep-selfref]) / P2 ~15
- Cross-stabilize 회귀 신호: 1건 명확 — [Dependency](M2→M3 재등장, next/NestJS bump deferred — Fix round 무변경). + [Design-draft] label 약한 잔존(DESIGN status=draft, 단 M3가 §7 인벤토리 능동 갱신). **해소 4종**([Insight-backlog]·[Design-token-drift]·[Surface-backref]·용어 divergence) — patterned doc-drift가 F-012로 끊김(개선 신호).
```

## 1. 우선순위

### M3
1. (P0) ✅ **CLOSED (Fix round 커밋 `f1f17df` + 정식 재grade 2026-06-07 YES)** — **§5 #3 업로드-경로 E2E 배선 + 웜캐시 재생성** (M3-E2E-001): `scripts/e2e.mjs` 업로드 phase(`POST /api/v1/resumes` → `POST /resumes/:id/score` → feed 적합도 배지 assert) + `scripts/e2e_pii_scan.py`(실 masker end-to-end `resumes.content`+`ranking_runs.result` scan, QA-M3-006 닫음) + 업로드 fixture 웜캐시 재생성(+47). **재grade 세션 `pnpm e2e` exit 0 실측**(upload resume_id=14→mask placeholders=5→score ranking_run id=19→PII scan 0/5→feed scored 6/held 0). graduation §5 필수 7/7 충족 → **졸업 가능 YES**. **잔여(외부검증만): push 시 CI e2e-smoke green 1회.**
2. (P1) **[Arch-iface-7-3] + ADR-106 후보** — NestJS api가 `uv run python -m worker --resume-id` subprocess를 spawn하는 cross-stack 오케스트레이션이 ARCH §7-3("api는 산출물 서빙·미계산/미트리거")에 미기재. REV-M3-002 + T-037 report 수렴. M4 컨테이너 분리 시 spawn 동작 불가 → ADR로 "M3 로컬 spawn=임시, M4 큐/HTTP 트리거 교체" 명문화 + §7-3 본문 보강. **architect 호출 권장.**
3. (P1) **[Arch-iface-7-1]** — `resumes.controller.ts` manual 포맷/크기 검증이 ARCH §7-1 "ValidationPipe + class-validator DTO" 컨벤션과 divergence(class-validator 미설치). REV-M3-001 + T-034 report 수렴. §7-1 본문에 "multipart inline guard 예외" 1줄 sync 또는 class-validator 설치.
4. (P1) **[Design-a11y] + [Spec-gap]** — F-015 §8-1 접근성(파일 input `<label>`·업로드 중 `aria-busy`·preview `role=region`)이 미구현·미테스트(DSN-M3-001/002/003, 메인 세션 P0→P1 하향). 셋 다 *어느 task AC에도 미매핑* → `/plan-workitem F-015`로 a11y task 추가 회수.
5. (P1) **[Dependency]** — `next`≥15.5.16 + NestJS bump 후 재audit(pnpm high 8건). M2 재등장 — 별도 bump task. pip-audit clean.
6. (P1) **evidence-summary TS↔Python 동기 위험** — preview 카운트(TS)와 채점 evidence(Python)가 독립 2구현 → 정규식 drift 시 UX 불일치(REV-M3-003/QA-M3-004). WHY 주석 + 동기 규율.
7. (P1) **[Spec-grep-selfref]** — T-032 AC-1/F-012 FAC-1의 `grep "합격가능성 밴드"` 검증이 *grep 명령·FAC 정의를 적은 spec-doc 자체*를 매칭(논리적 self-reference). T-032 report가 stabilize 회수 요청 → grep 범위를 spec-doc 제외로 좁히는 plan touch-up.
8. (P2) reviewer 리팩토링(REV-M3-004~009) + design 폴리시(DSN-M3-004~008) + ARCH §6/§7-4·DESIGN_RESEARCH 용어 잔여 + DISCOVERY/Charter status=draft — 전부 비차단.

### M2
1. (P0) **E2E fresh-clone 재현성 확보** — `enableCors()` 커밋 + 무키 score 경로(`.cache/llm` 커밋 or 합성 fixture) + 단일 crawl→score→feed 오케스트레이션 명령/runbook(README 갱신). graduation §5 #3 직결.
2. (P1) **GS-1-through-DB 결정성 hole** — `report.py:52` `sorted()`(QA-M2-001). 게이트 직결·one-line.
3. (P1) **web UI error/empty 상태 + CoveragePanel 에러 표면화** — Fail#3(거짓 완전성 차단·G3) 직결. CoveragePanel `.catch(()=>{})`·FeedList 무-catch silent fail 제거.
4. (P1) **의존성** — `next`≥15.5.16 bump + NestJS 갱신 + 재audit(high 8건).
5. (P1) **doc reconcile 일괄** — DISCOVERY/Charter/DESIGN "적합도" 용어 통일 + Insight I-1/2/3 promote + DESIGN status=draft 정리 + globals.css token SSOT 동기 + ADR-104 backref 6건.
6. (P2) reviewer 리팩토링 6건(REV-M2-001~006) + design 폴리시(8-state·GreetingCard·dashed-border) — 전부 behavior-preserving.

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

### M2

> **Fix round 2026-06-06** (메인 세션, stabilize 회수 + 커밋): **resolved** — M2-GS1-002/QA-M2-001(report.py sorted), REV-M2-UI-001(CoveragePanel/FeedList error·empty 상태 + res.ok 체크 + 테스트), REV-M2-003+QA-M2-002(recommendations `@@unique` + migration + WHY), REV-M2-006+QA-M2-007(crawler 빈 fetch guard), QA-M2-006(feed `id desc`), QA-M2-008(contract nullable/unique assert), [Design-token-drift](globals.css `--ink`/`--paper`→DESIGN §2-1 SSOT). **M2-E2E-001 부분 해소**: (a)enableCors·(d)nest-cli/tsconfig.build는 커밋 `57df9fc`로 닫힘; (b)무키 score fixture·(c)단일 오케스트레이션/README runbook은 잔존(아래 status). **deferred** — [Surface-backref](doc-trace 실질↓), [Dependency](next 메이저 bump=별도 task), [DISCOVERY-Charter-drift]·[Insight-backlog]·[Design-draft](/bootstrap-project SSOT reconcile 경로), DSN-M2-FITRING·DSN-M2-P2(비주얼 폴리시 — 사용자 "기능까지만" 결정), REV-M2-001/002/004/005(behavior-preserving 리팩토링).
>
> **Fix round 2 (E2E) 2026-06-06** (메인 세션, 사용자 결정=웜캐시 커밋, 사용자 키 1회 실행): **M2-E2E-001 closed (실측 demonstrated, 커밋 `26aa0c9`)** — 결정적 crawl fixture(`crawler/fixtures/seed_jobs.txt` + `CRAWL_FIXTURE` 오프라인 모드, `load_fixture`/`crawl(fixture_jobs=)`), 단일 오케스트레이션 `scripts/e2e.mjs`(compose up→migrate→crawl→score(웜캐시)→api 서빙→feed/coverage assert) + `pnpm e2e`/`e2e:warm`, CI 졸업 게이트 `.github/workflows/e2e-smoke.yml`(무키), 웜캐시 `ai/worker/fixtures/llm_cache`(50 entries, `LLM_CACHE_DIR`로 `.cache/llm`과 분리), README/README_ko E2E runbook([Doc-stale] resolved). **실측**: fresh DB(truncate)→crawl(토스3·당근3)→keyed score(6 scored/0 held)→keyless 재채점 result **byte-identical**(`3a4680f5`, GS-1-through-DB §5 #6)→실행 api `/feed` 6건 scored+evidence+dedup·`/coverage` 양채널 success. **잔여(외부검증)**: push 시 CI e2e-smoke green + `/stabilize-milestone M2` 정식 재grade(NO→YES).

- **M2-E2E-001** | P0 | [관측됨] | linked: M2,T-018,T-022,T-023 | status: **closed (demonstrated, 커밋 26aa0c9 / Fix round 2)** | `crawler/__main__.py` · `scripts/e2e.mjs` · `.github/workflows/e2e-smoke.yml` · `ai/worker/fixtures/llm_cache/`
  - 발견: M2 done-line(§5 #3 "fresh clone → docker compose up + prisma migrate + seed + 단일 오케스트레이션으로 crawl→score→feed 완주 + localhost:3000 렌더")이 stabilize 커밋 상태로 **재현 불가**였음. (a) enableCors uncommitted, (b) `.cache/llm` gitignored + 무키 score fixture/오케스트레이션 부재 → 전 공고 held, (c) 단일 오케스트레이션·runbook 부재, (d) nest 설정 untracked.
  - 해소: (a)(d) 커밋 `57df9fc`. (b) 웜캐시 경로 — fixture 공고로 캐시 키 고정(`make_key`는 JD raw_text 기반이라 DB id 무관) + `LLM_CACHE_DIR` tracked dir + 50-entry 웜캐시 커밋. (c) `scripts/e2e.mjs` + `pnpm e2e` + CI 게이트 + README runbook.
  - 실측(메인 세션): keyed score 6 scored/0 held → keyless 재채점 result byte-identical(웜캐시 완전 + 결정성) → 실행 api가 fixture feed/coverage를 정상 서빙. graduation §5 #3·#6 실증.
  - 잔여(외부검증): push 시 CI e2e-smoke green 1회 확인 → `/stabilize-milestone M2`로 graduation NO→YES 정식 재grade.
- **M2-GS1-002** | P1 | [관측됨] | linked: T-022 | status: open | `ai/worker/src/worker/report.py:52`
  - 발견/권장: pending_job_ids `set`→`list` 비결정 — [QA_FINDINGS QA-M2-001](QA_FINDINGS.md) 참조. `sorted(...)` one-line. (게이트 finding이라 QA_FINDINGS owning, 우선순위 가시성 위해 cross-list.)
- **REV-M2-UI-001 [Web-error-state]** | P1 | [관측됨] | linked: T-028,T-029 | status: open | `podo/apps/web/components/CoveragePanel.tsx:33` · `FeedList.tsx:22-40`
  - 발견: web UI에 error/empty 상태가 부재. CoveragePanel은 `.catch(() => {})`로 fetch 실패를 **삼켜** 영구 "수집 현황 불러오는 중…" 표시 → 수집 API 장애 시 *거짓 완전성*(Fail #3 / Charter G3 — CoveragePanel의 존재 이유와 정면 충돌). FeedList `loadMore`도 catch 없음 → fetch reject 시 빈 `<ul>`만, EmptyState/ErrorState/skeleton 미구현(DESIGN §7-3/§7-4 일급 상태).
  - 근거: DESIGN §7-4 CoveragePanel error="수집 실패" 경고(danger) 필수 · §9 "ErrorState 숨기지 않고 노출". 해피패스만 구현, 실패 분기 누락.
  - 권장: CoveragePanel catch에서 error state(`var(--band-1-ink)` danger "수집 실패") + FeedList error/empty 렌더 + 초기 skeleton. `/repair-workitem T-029`.
- **DSN-M2-FITRING** | P1 | [관측됨] | linked: T-028 | status: open | `podo/apps/web/components/FitScoreRing.tsx:6-13`
  - 발견: 링이 SVG arc가 아니라 **원 전체를 brand-gradient로 채우고** 점수 숫자 색이 `var(--paper)`(크림 흰색). DESIGN §7-2 "점수 숫자는 ink(장식 금지)" 위반 + §2-4는 gradient를 *arc*에 fence. gradient 밝은 끝(#f5709f)에서 흰 숫자 AA 대비 미달 우려(§2-5).
  - 근거: design subagent가 P0로 제기 → 메인 세션 검증 결과 *기능 결함 아님(숫자 렌더·색만 의존 아님)·graduation 비차단* → **P1 하향**. 단 DESIGN §7-2/§2-4/§2-5 다중 위반.
  - 권장: SVG strokeDasharray arc + 중앙 숫자 `var(--ink)` on paper track. 또는 최소 숫자색 ink + 대비 확인.
- **[Design-token-drift]** | P1 | [관측됨] | linked: T-018,T-028 | status: open | `podo/apps/web/app/globals.css:7,8`
  - 발견: globals.css `--ink: #2a2630`·`--paper: #fffbf7`가 DESIGN §2-1 SSOT(`ink:#2B2433`·`paper:#FFFBF6`)와 **불일치**. 5-band 신호 토큰은 정확히 일치하나 두 중립색이 drift. raw-hex grep은 컴포넌트가 토큰명을 쓰므로 *구조적으로 못 잡음* — 본 SSOT 정합 검사가 유일 가드.
  - 근거: ADR-027 DESIGN=시각 SSOT. 시각 영향은 미세(~1 hex unit)하나 token=SSOT 계약 위반.
  - 권장: globals.css 2값을 DESIGN §2-1로 동기(trivial). 누락 토큰(`--muted`·`--grape-*` 등 컴포넌트 미참조분)은 필요 시 추가.
- **[Surface-backref]** | P1 | [관측됨] | linked: F-011,T-030 | status: open | `compare_pairwise.py:17`·`llm.py:14`·`rerank_listwise.py:19`·`parse_resume.py:16`·`parse_job.py:14`·`matching.py:22`
  - 발견: ADR-104 `## Surfaces`가 등재한 6개 usage-site가 leaf util(`_json_util`/`_prompts`)을 import하나 **`ADR-104` 역참조 주석 부재**(F-011 §4 "변경 파일에 `per ADR-104` 부착" 미이행). 신규 leaf 모듈·`rank_aggregate`(DOM_RANK)에는 backref 존재.
  - 근거: ADR-045#d3 Surfaces forward check. *실질(중복 제거·import)은 충족* — 순수 doc-trace gap.
  - 권장: 6개 import 라인에 `# per ADR-104` 1줄 부착. 낮은 실질 우선순위.
- **[Dependency]** | P1 | [관측됨] | linked: F-005,T-018 | status: open | `podo/apps/web/package.json`(next) · `podo/apps/api/package.json`(@nestjs/*)
  - 발견: `pnpm audit --prod` 22건(high 8 / moderate 12 / low 2). `next`(<15.5.16) 14 advisories(cache poisoning 등) + `@nestjs/common`·`@nestjs/core`.
  - 권장: `next`≥15.5.16 bump, NestJS 갱신 후 재audit. pip-audit는 clean.
- **[DISCOVERY-Charter-drift]** | P1 | [관측됨] | linked: docs/10-charter, M2 | status: open
  - 발견: M2가 "적합도 5단계" 노출로 확정했으나 Charter(§3.1/§4)·DISCOVERY는 "합격가능성"(Charter 6×·DISCOVERY 12×) 잔존. UI 코드는 이미 "적합도"로 통일(design subagent 확인) → *user-visible 불일치는 없고 doc SSOT만 lag*.
  - 권장: `/bootstrap-project --apply` 또는 `/discover-product --update`로 DISCOVERY(SSOT)→Charter 용어 reconcile + DESIGN §2/§7 라벨 동기(M2 §7·F-010 §12 열린 질문 닫음).
- **[Insight-backlog]** | P1 | [관측됨] | linked: docs/10-charter/DISCOVERY.md §15 | status: open
  - 발견: I-1(신뢰 thesis 보류·근거)·I-2(5단계 밴드)·I-3(누락0 투명성 커버리지)가 **M2 F-010에서 실제 UI로 구현**됐으나 §15 status=open 잔존(M1 stabilize도 동일 지적 — 미적용 재발).
  - 권장: 외부 증거(인터뷰/라벨) 수집 후 promote, 또는 "구현 반영됨(증거는 출시 후)"로 status 갱신. `/plan-workitem`이 회수.
- **[Design-draft]** | P1 | [관측됨] | linked: docs/20-system/DESIGN.md | status: open (실질↓, M1→M2 재발)
  - 발견: DESIGN.md `status=draft` + M2는 실제 UI 구현(T-028/029) → ADR-027#amend-3 신호. M1이 "status 라벨 정리" 권고했으나 미적용(Cross-stabilize 회귀 신호).
  - 권장: DESIGN.md status를 accepted로 승격(또는 프로젝트 draft 컨벤션 명문화). `/bootstrap-design` 재실행은 불필요(문서 충실).

### M3

> **Fix round 2026-06-07** (메인 세션, stabilize 회수 + 커밋 `f1f17df`): **M3-E2E-001 closed (demonstrated)** — `scripts/e2e.mjs`를 업로드 경로로 재배선(api 채점-전 기동 → `POST /resumes`(실 PII fixture→NestJS 마스킹) → `POST /resumes/:id/score`(worker `--resume-id`, 웜캐시) → PII scan → feed assert) + `scripts/e2e_pii_scan.py`(실 masker end-to-end resumes.content+ranking_runs.result 스캔, QA-M3-006 종결) + 업로드 fixture 웜캐시 재생성(+47 엔트리, 사용자 키 1회). **실측**: 무키 `pnpm e2e` exit 0 — upload→마스킹(resume_id, placeholders=5)→score(웜캐시 hit, 무 LLM)→PII scan 0건→feed **scored 6/held 0/toss+daangn**. graduation §5 #3·#7 자동 게이트 충족. **[정식 재grade 2026-06-07 완료]** `/stabilize-milestone M3` 재실행 — 본 세션 `pnpm e2e` exit 0 재현(동일 실측) + validate exit 0 → graduation §5 필수 7/7 → **졸업 가능 NO→YES**. **잔여(외부검증만)**: push 시 CI e2e-smoke green 1회. 나머지 M3 P1/P2(아래)는 여전히 open.

- **M3-E2E-001** | P0 | [관측됨] | linked: M3,T-037,T-039,T-040 | status: **closed (demonstrated, 커밋 f1f17df / Fix round 2026-06-07)** | `scripts/e2e.mjs` · `scripts/e2e_pii_scan.py` · `ai/worker/fixtures/llm_cache/`
  - 발견: M3 done-line(§5 #3 "이력서 업로드 → 마스킹 → 파싱 → crawl→score→feed 완주 + 업로드 이력서 기준 적합도 배지 렌더")이 자동 게이트로 **미실증**. `pnpm e2e`는 exit 0이나 phase 4가 `uv run python -m worker`(seed 경로 = `_ensure_seed_resume`)로만 채점 — `POST /api/v1/resumes`(업로드·마스킹)·`POST /resumes/:id/score`(`--resume-id` 채점)·업로드 이력서 feed 렌더를 *전혀 거치지 않는다*. 웜캐시 49개도 seed 기반(마스킹 fixture 이력서 미반영 → 업로드 채점은 cache miss→held가 될 것). 결과: M3 핵심 입력 경로(합성 seed→실 업로드 교체)가 E2E로 미검증.
  - 결: **PII Safety Pass(§5 #7)도 부분 이연** — T-040은 하류 6표면 안전을 실증하나, 실 NestJS masker→DB `resumes.content` end-to-end(surface-1)는 업로드 E2E 의존(QA-M3-006). 두 게이트가 같은 배선으로 동시에 닫힌다.
  - 해소(필요 작업 — stabilize report-only 경계 밖, main-session/`/repair-workitem`): (a) 마스킹 fixture 이력서(`crawler/fixtures` 또는 신규) + e2e.mjs phase에 업로드 POST→score(:id)→feed assert(업로드 resume band)+`resumes.content` literal scan, (b) `pnpm e2e:warm`(사용자 OPENAI_API_KEY 1회)로 *마스킹 fixture × JD* 캐시 키 웜캐시 재생성→커밋(`make_key`는 이력서 정규화본 기반이라 seed↔업로드 키 상이), (c) 재배선 후 `/stabilize-milestone M3` 재grade(NO→YES). **M2-E2E-001 closed 패턴 정합.**
- **REV-M3-002 [Arch-iface-7-3]** | P1 | [관측됨] [ADR-candidate] [Arch-debt] | linked: T-037 | status: open | `podo/apps/api/src/resumes/worker-runner.port.ts` · ARCH §7-3
  - 발견: NestJS api가 `SubprocessWorkerRunner`로 `uv run python -m worker --resume-id N`를 spawn(동기 트리거)하는 cross-stack 오케스트레이션은 ARCH §7-3("api = user-facing CRUD + Worker 산출물 *서빙*, ranking/score 미계산")의 경계와 새로 어긋난다. T-037 §8이 "architect 권장"으로 이미 플래깅(ADR 미신설). T-037 report도 동일 P1.
  - 근거: M4 배포(컨테이너 분리) 시 동일 프로세스 `spawn`은 동작 불가 — process-boundary 소유권 미문서화 시 M4 설계 충돌. 단 port(`WorkerRunner`) 추상화는 깔끔(테스트 fake 주입 가능).
  - 권장: **ADR-106(가칭) 신설** — "M3 로컬 단일프로세스 spawn=임시 결정, M4 큐(pg-boss/BullMQ) 또는 HTTP 트리거 교체 예정" + ARCH §7-3 본문에 "M3 예외: subprocess 트리거(로컬 한정)" 1줄. **architect 호출 권장**(메인 세션, 본 skill은 텍스트 제안만).
- **REV-M3-001 [Arch-iface-7-1]** | P1 | [관측됨] [ADR-candidate] | linked: T-034 | status: open | `podo/apps/api/src/resumes/resumes.controller.ts` · ARCH §7-1:179
  - 발견: 컨트롤러가 파일 확장자·크기·byteLength를 inline으로 직접 검증(`UploadedResumeFile` 인터페이스 자작). ARCH §7-1 "입력 검증: NestJS ValidationPipe + class-validator DTO" 컨벤션과 divergence. T-034 report도 동일 P1(class-validator 미설치 + 네트워크 차단 → manual fallback). 관측 동작은 정확(201/413/415 envelope).
  - 권장: §7-1 본문에 "multipart 파일 검증은 controller inline guard 허용(예외 — `@types/multer`/class-validator 의존 회피, WHY)" 1줄 sync, 또는 class-validator 설치 후 정석. **stabilize는 ARCH 수정 권한 없음 → 텍스트 제안만**(write 금지 영역).
- **REV-M3-003 [Cross-lang-dup]** | P1 | [관측됨] [Clean-Code: Duplication] | linked: T-034,T-037 | status: open | `podo/apps/api/src/resumes/evidence-summary.ts` ↔ `ai/worker/src/worker/parse_resume.py`
  - 발견: skills/experience 헤딩·불릿 파싱이 TS(업로드 즉시 preview 카운트)·Python(채점 evidence) 2스택에 독립 존재. 주석은 "동치"만 적고 *변경 시 양쪽 동기*·*왜 분리했나*가 없음. 정규식 drift 시 preview "스킬 N개" ≠ 채점 evidence(QA-M3-004와 수렴, UX 불일치).
  - 근거: 각 1회 사용(rule-of-3 미달 → 통합 강제 아님, 스택 경계 crossing cost > 중복 유지 cost). 단 무음 divergence 위험.
  - 권장: evidence-summary.ts 상단에 "parse_resume.py 상수와 동치 유지 필수(변경 시 동시 수정), 단일화는 M4+ 범위" WHY 주석.
- **[Design-a11y] DSN-M3-001/002/003 [Spec-gap]** | P1 | [관측됨] | linked: T-038,F-015 | status: open | `ResumeUpload.tsx:127,152` · `MaskingPreview.tsx:29`
  - 발견: F-015 §8-1 명시 접근성 3종 미구현 — 파일 `<input>`에 `<label>`/`id` 없음(DSN-M3-001), 업로드 중 `aria-busy` 없음(DSN-M3-002), MaskingPreview에 `role="region"`/aria-label 없음(DSN-M3-003). design subagent가 P0로 제기 → **메인 세션 검증 후 P1 하향**(graduation P0=QA_FINDINGS 기준 무관 + M3 로컬 단일사용자 pre-deploy + F-015 §8 Lighthouse "선택").
  - 근거: F-015 §8-1이 셋을 명문화했으나 T-038/T-041 *어느 AC에도 미매핑* → spec-coverage gap(ADR-037). 기능은 동작(렌더·업로드·채점) — a11y 일급화만 누락.
  - 권장: `/plan-workitem F-015`로 a11y task(label/aria-busy/role + 단위 단언) 추가. 1~3줄 수정 규모.
- **[Dependency]** | P1 | [관측됨] | linked: F-005,T-018,M2 | status: open (M2→M3 재등장) | `podo/apps/web/package.json`(next) · `podo/apps/api/package.json`(@nestjs/*)
  - 발견: `pnpm audit --prod` 22건(high 8/mod 12/low 2). `next`(<15.5.16, cache-poisoning 등) + `@nestjs/common`·`@nestjs/core`. M2 [Dependency] P1이 미적용 상태로 재등장(cross-stabilize 회귀 신호).
  - 권장: `next`≥15.5.16 + NestJS 갱신 후 재audit. pip-audit는 clean(Python). 별도 bump task.
- **[Spec-grep-selfref]** | P1 | [관측됨] | linked: T-032,F-012 | status: open | `docs/30-workitems/features/F-012` · `T-032` AC-1
  - 발견: F-012 FAC-1/T-032 AC-1의 "`grep "합격가능성 밴드"` = 0" 검증이 *grep 명령·치환대상 정의를 적은 spec/FAC/reconcile-meta doc 자체*를 매칭(논리적 self-reference — 검색어를 안 적고 검사 기술 불가). 유효 기준(정책/제품 표면 = DISCOVERY/Charter/DESIGN/F-001)은 0 충족. T-032 report가 stabilize 회수 명시 요청.
  - 권장: F-012 FAC-1·T-032 AC-1 grep 범위를 *제품/정책 표면 한정*(spec-doc 제외)으로 좁히는 plan touch-up. 회귀 가드는 유지하되 self-ref FP 제거.

## 3. 권장 리팩토링

### M3 (P2 — reviewer 위임 + design 폴리시 + qa cross-list, 전부 behavior-preserving)
- **REV-M3-004** | P2 | [관측됨] [Clean-Code: Function-size/SRP] | T-034 | `resumes.controller.ts:32-76` — `create()`가 multipart/paste 2경로 × (포맷·크기·raw 추출) 44줄 혼재. `extractRawFromFile`/`extractRawFromPaste` private 분리 후보(rule-of-3 미달 — 강제 아님).
- **REV-M3-005** | P2 | [관측됨] [Clean-Code: Naming] | T-034 | `resumes.controller.ts:16` — `UploadedResumeFile`이 실제로는 multer `File` 최소 서브셋. `MinimalMulterFile`/`RawUploadedFile`로 리네임(의도 명확화) 또는 `@types/multer` 정석 타입.
- **REV-M3-006** | P2 | [관측됨] [Clean-Code: Comment-WHY] | T-037 | `persistence.py:74-78` `load_resume` — domains frontend/backend 하드코딩 WHY는 있으나 "타 도메인 이력서 fit_level 편향" downstream 효과 미기재. 1줄 추가(OBS-M3-2와 수렴).
- **REV-M3-007** | P2 | [가설] [Clean-Code: Dead-code 예고] | T-037 | `__main__.py:21-41` `_ensure_seed_resume` — M2 무키 E2E 보존용(현재 dead 아님). M4 seed 경로 제거 시 삭제 후보 — "M4 제거 후보" 주석으로 추적(QA-M2-003 잔존·OBS-M3-2 정합).
- **REV-M3-008** | P2 | [관측됨] [Arch-debt] | T-037 | `resumes.controller.ts` `score()` — 비정수 id의 parseInt 실패가 404 `RESUME_NOT_FOUND` 반환(의미상 400 BAD_REQUEST). `INVALID_RESUME_ID`(400)로 1줄 교체 권장.
- **REV-M3-009** | P2 | [관측됨] [Clean-Code: Comment-WHY] | T-034 | `resumes.controller.ts:53` — `file.size > MAX || file.buffer.length > MAX` 이중 크기검사 WHY 부재(multer `size` 미집계 방어 추정) → 1줄 주석.
- **DSN-M3-004** | P2 | [가설] | T-038 | `MaskingPreview.tsx:30` — evidence 요약 본문이 `var(--faint)`. DESIGN §2-1이 faint를 "장식·<4.5 contrast, body 금지"로 두면 정보성 본문에 부적합 → `var(--muted)` 권장(DESIGN §2-1 대비 규칙 확인 후).
- **DSN-M3-005** | P2 | [관측됨] | T-041 | `ResumeUpload.tsx:159` — error toast "업로드 실패. 다시 시도해보세요." ↔ F-015 §8-1 copy "업로드에 실패했어요. 다시 시도해주세요."(podo 톤). 문구 동기.
- **DSN-M3-006** | P2 | [관측됨] | T-041 | `ResumeUpload.tsx:75` — 무입력 시 `if(!hasInput) return` 조용한 early-return. textarea placeholder는 있으나 F-015 §8-1 empty 흐름("이력서를 업로드하거나…" podo 안내)은 미구현. empty 안내 노드 추가 권장.
- **DSN-M3-007** | P2 | [관측됨] | T-038,T-041 | `ResumeUpload.tsx:138,158` — error/danger 색에 `var(--band-1-ink)`(적합도 밴드 신호 토큰) 재사용 → 토큰 의미 레이어 혼용. globals.css에 `--color-danger: var(--band-1-fill)` semantic 명명 후 참조 권장(렌더는 무결).
- **DSN-M3-008** | P2 | [가설] | T-041 | `ResumeUpload.tsx:169-184` — skeleton div가 `.shimmer` 클래스만(inline 배경 없음). T-041이 inline 제거로 gradient 노출했다 기록 — 실 브라우저 시각 확인 권장(jsdom 미평가).
- qa P2(QA-M3-001 마스킹 순서·QA-M3-002 stdio:'inherit'·QA-M3-003 module /g regex·QA-M3-005 int(argv))는 [QA_FINDINGS `## M3`](QA_FINDINGS.md)에 기록.
- **[Term-residual]** | P2 | [관측됨] | linked: T-032 | `docs/20-system/ARCHITECTURE_OVERVIEW.md:103,221`·`DESIGN_RESEARCH.md:14,33` — ARCH §6 glossary·§7-4 + DESIGN_RESEARCH에 "합격가능성 밴드" 잔존(T-032 scope=DISCOVERY/Charter/DESIGN/F-001이라 ARCH·연구doc 미포함). 정책/제품 표면은 0. ARCH는 "적합도 5단계"로 동기 권장(연구doc은 과거표현 허용).
- **[DISCOVERY-Charter-mtime]** | P2 | [관측됨, 저신뢰] | linked: docs/10-charter | mtime signal 1(DISCOVERY 01:58 > Charter 01:50) firing이나 F-012가 방금 reconcile + Charter 용어 grep 0 → benign edit-ordering(§15 Insight promote는 Charter 미스냅샷). content drift 아님 — Charter snapshot이 최신 DISCOVERY 반영했는지 1회 확인 권장.
- **[Doc-status-draft]** | P2 | [관측됨] | linked: F-012 | DISCOVERY/Charter/DESIGN `## 0. Status`=draft 잔존(F-012 §4 "status 현행화" scope가 T-032 AC에 미포함). [Design-draft]와 정합 — label 정리 또는 draft 컨벤션 명문화(M1·M2도 동일 권고).

### M2 (P2 — reviewer 위임 + design 폴리시, 전부 behavior-preserving)
- **REV-M2-001** | P2 | [관측됨] [Clean-Code: Naming] | T-022 | `persistence.py:21-23` — `SCORING_MODE`(고정) vs `DEFAULT_RANKING_MODE`(디폴트) 역할 차이가 이름에 안 드러남. `_FIXED_SCORING_MODE` 또는 주석으로 "변경불가 고정값" 명시.
- **REV-M2-002** | P2 | [관측됨] [Clean-Code: Function-size/SRP] | T-022 | `persistence.py:62-127` — `persist_run`이 직렬화+ranking upsert+rec DELETE+scored insert+held insert 5단계 혼재. `_upsert_ranking_run`/`_replace_recommendations` 분리 후보(rule-of-3 미달이라 강제 아님).
- **REV-M2-003** | P2 | [관측됨] [Clean-Code: Comment-WHY] | T-022 | `persistence.py:104` — DELETE-reinsert WHY에 *숨은 invariant*(recommendations에 `(run_id,job_posting_id)` unique 부재 → full delete 필수) 누락. QA-M2-002와 수렴 — DB unique 추가가 근본 해법.
- **REV-M2-004** | P2 | [관측됨] [Clean-Code: Naming] | T-023 | `__main__.py:19-39` — `_ensure_seed_resume` 독스트링의 `bootstrap`↔이름 `ensure` 동사 혼용. `_get_or_insert_seed_resume` 또는 독스트링 통일.
- **REV-M2-005** | P2 | [관측됨] [Clean-Code: Duplication] | T-022,T-024 | `persistence.py:100-102`·`crawler/persistence.py:107-110`·`__main__.py:37-38` — `fetchone()+assert+int(row[0])` 패턴 3회(rule-of-3 충족). `core/db.py`에 `_fetch_returning_id(cur)` 추출 후보(레이어 정합 확인 후).
- **REV-M2-006** | P2 | [관측됨] [Clean-Code: Comment-WHY / behavior 경계] | T-024 | `crawler/persistence.py:76-84` — 빈 fetch 시 `closed = existing - today_urls`가 전체 마감 처리(WHY/guard 부재). [QA_FINDINGS QA-M2-007](QA_FINDINGS.md)로도 기록 — `if closed and jobs:` guard 권장.
- **DSN-M2-P2** | P2 | [관측됨] | T-028,T-029 | design 폴리시 묶음 — held 링이 solid `border`(DESIGN §6 dashed 1.5px 미적용) · `GreetingCard` 미구현(DESIGN §7-2 등재, empty-state strip) → `[Design-inventory-pending]` · `FeedList` DESIGN §7 미등재(layout wrapper) → `[Design-inventory-drift]` · "더 보기"가 raw `<button>`(DESIGN §7-1 Button.ghost 미사용) · JobCard hover/focus·8-state skeleton 미구현. M2(로컬 E2E) 규모상 폴리시 이연 가능, M3 전 정리 권장.
- **[Doc-stale]** | P2 | [관측됨] | T-018 | `README.md`·`README_ko.md` — status: **resolved**(Fix round 2). Status(M1·M2 done)·Next steps(→M3)·"Local E2E" runbook 갱신. (구 "pass likelihood" thesis/scope 라인은 [DISCOVERY-Charter-drift] 용어 reconcile 배치 소관 — 범위 분리 유지.)

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

### M2 — ADR 후보 + instruction 개선 후보
**ADR 후보:** **없음.** M2는 ARCH §3-1 레이어 경계·의존성 규칙을 *변경하지 않았다*(milestone §1 "새 layer 아니라 물리 매핑 인스턴스화"). 필요했던 경계 ADR(ADR-103 eval↔worker / ADR-104 worker shared-util)은 M2 진입 전 이미 생성됐고 F-011이 집행 완료. *유일한 결정-기록 후보*는 "무키 fresh-clone E2E 결정성 전략"(웜캐시 커밋 vs 합성 score fixture vs 항상-키)이나, ADR보다 M2-E2E-001 repair task의 결정으로 충분(layer 규칙 아님).

**Instruction 개선 후보 (ADR-022 ratchet evidence label 부착 — *보고만*, AGENTS.md/agent/skill body 자동 수정 X):**
- [관측됨 · 본 세션 reviewer 1회 + M1 qa 2회] **subagent budget-exhaustion 재발이 reviewer로 확산.** 첫 reviewer(code) 위임이 24 tool-use를 탐색에 소진하고 `"Now let me check…"` process line으로 종료 — finding 블록 미출력. 재spawn 시 *"≤6 reads · first message=findings · F-011은 이미 검증됨(재확인 금지)"* 제약으로 6 tool-use에 정상 출력. 후보: stabilize 단계 4·5 위임 프롬프트(또는 `qa.md`/`reviewer.md`)에 **명시적 read-budget + "final message MUST be findings" self-check**를 박기(M1은 qa만, M2는 reviewer까지 → 공통화). SendMessage 부재로 paused subagent 재개 불가 → 위임 *self-contained + output-first* 디폴트 재확인.
- [관측됨 · 본 세션 1회] **design subagent severity 인플레.** design surface 위임이 P0 2건(FitScoreRing·CoveragePanel)을 제기했으나 메인 세션 검증 결과 둘 다 *기능/그래듀에이션 비차단* → P1 하향. design 위임은 DESIGN의 *aspirational* 8-state 매트릭스를 *위반*으로 과보고하는 경향. 후보: design 위임 프롬프트에 **"P0 = 기능/접근성 *차단*만; 미구현 폴리시·상태는 P1 이하"** severity 기준 명시.
- [관측됨 · Cross-stabilize] **마일스톤 간 doc-reconcile 누락 패턴.** M1이 권고한 DESIGN status 정리·Insight promote·용어 reconcile가 M2까지 미적용([Design-draft]·[Discovery-insight] 재등장 = 회귀 신호 2건). 후보: graduation checklist에 *"직전 stabilize의 P1 doc-reconcile 항목 close 여부"* 점검 1줄 추가 검토(ADR-014 graduation contract 확장 후보).

### M3 — ADR 후보 + instruction 개선 후보
**ADR 후보 (M3 중 내려진 결정인데 ADR 부재 — cross-stack process 경계는 ADR-006 정책상 ADR 대상):**
1. **ADR-106(가칭) — NestJS→Python worker 트리거(subprocess) 경계** (REV-M3-002 / T-037 §8·report): api가 `uv run python -m worker --resume-id`를 spawn하는 cross-stack 오케스트레이션이 ARCH §7-3("api 미계산/미트리거")와 새로 어긋남. "M3 로컬 단일프로세스 spawn=임시, M4 큐(pg-boss/BullMQ) 또는 HTTP 트리거로 교체, process-boundary 소유권" 명문화 필요. **architect 검토 권장**(메인 세션 호출, 본 skill은 텍스트 제안만).
> (ADR-105 PII 마스킹 정책은 M3에서 *신설 완료* — accepted, ARCH §8/§10 backref 존재. 추가 ADR 대상 아님.)

**Instruction 개선 후보 (ADR-022 ratchet evidence label 부착 — *보고만*, AGENTS.md/agent/skill body 자동 수정 X):**
- [관측됨 · 본 세션 reviewer 1회 / M1·M2 누적 3회차] **subagent budget-exhaustion 재발.** 첫 reviewer(code) 위임이 20 tool-use를 탐색에 소진하고 `"Now let me check…"` process line으로 종료(finding 미출력). 재spawn 시 *"≤6 reads · FIRST message=findings · 기지사실 명시(재확인 금지)"* 제약으로 6 tool-use에 정상 출력 — M2 처방 그대로 재현 성공. **M2 instruction 후보(stabilize 단계 4·5 위임에 read-budget + "final message MUST be findings" self-check 명문화)가 여전히 미적용 → 우선 회수 권장.** SendMessage가 본 하니스 deferred-tool 목록에 *부재* → paused subagent 재개 불가(M1/M2 메모 정합) → 위임 self-contained + output-first 디폴트 필수.
- [관측됨 · 본 세션 1회 / M2에 이어 재발] **design subagent severity 인플레.** a11y 3건(label/aria-busy/role=region)을 P0로 제기 → 메인 세션 검증 후 *graduation 비차단·로컬 pre-deploy* 근거로 P1 하향. M2 instruction 후보("P0 = 기능/접근성 *차단*만; 미구현 폴리시·상태는 P1 이하")가 미적용 — 재확인.
- [관측됨 · 본 세션] **"stabilize *phase* 책임" ↔ "stabilize *skill* report-only" 표기 혼동.** M3 task(T-039/T-040 §4)·운영 메모가 "e2e.mjs 업로드 경로 재배선 = stabilize-milestone M3 책임"으로 적었으나, 본 skill은 코드 수정 금지(report-only). M2-E2E-001도 동일(stabilize가 surface → 별도 main-session Fix round가 코드 → 재grade). 후보: task §4(비범위)에 "stabilize *phase*(=surface + 후속 main-session round)" vs "stabilize *skill* 직접 수행(=report only)" 구분 1줄 — 매 milestone E2E-gap에서 반복되는 혼동.
- [관측됨 · Cross-stabilize 개선 신호] **M1·M2가 반복 권고만 하던 doc-reconcile([Insight-backlog]·[Design-token-drift]·[Surface-backref]·용어 divergence)이 M3에서 F-012(첫 feature 흡수)로 실제 해소.** M2 §4 instruction 후보("직전 stabilize의 P1 doc-reconcile close 여부 graduation 점검")의 *대안 처방*(권고를 다음 milestone의 task로 박기)이 효과적임을 실증 — graduation checklist 확장보다 *plan 회수 강제*가 닫는 데 유효.

## 5. Repair decision log

`/repair-plan`이 feature(F-NNN) 또는 milestone(M-N) 단위로 호출됐을 때 본 라운드의 P0+P1 결정을 영속 기록하는 자리 (ADR-047 D7 durable correction history + D1 inspectability). `## 2. 즉시 수정할 항목` / `## 3. 권장 리팩토링`과 의미 분리 — 이 두 섹션은 *open items*이고 본 섹션은 *closed records*(지나간 판단).

- task scope (T-NNN) 결정은 해당 task `## 8. 메모`에 직접 append — 본 섹션 아님.
- ID 컨벤션: `<workitem-id>-repair-<N>` (예: `F-001-repair-1`, `M1-repair-2`).
- evidence label은 기본 `[관측됨]` (finding 자체는 리뷰어의 *로컬 문서 관측*에서 나옴 — cross-review 방식의 외부실증은 ADR-038 본문이 owning).
- 형식은 본 파일 `## 항목 스키마` SSOT 따름.

<!-- 마일스톤별 그룹핑(`### M1`, `### M2`)은 `/repair-plan`이 *첫 호출 시* 해당 마일스톤 헤더를 자동 신설하고 그 아래에 append. /stabilize-milestone은 본 sub-section을 *추가하거나 수정하지 않음* — /repair-plan만 직접 append. 본 ## 5 sub-section은 *신설 시 헤더 + 본 안내 주석만* 두고 `### M-N` 그룹은 비워둔다. -->

### M2

> `/repair-plan M2` (2026-06-06) — cross-LLM `/validate-plan`(reviewer-tag: default, M2 + F-005~F-011, tasks 제외) 회수. P0 1 + P1 4 영속(P2 1건 = F-007 doc-link은 cap 보호로 미영속, F-007 문서에 직접 수정 적용).

- **M2-repair-1** | P0 | [관측됨] | linked: M2,F-006,F-007,F-009,F-010 | status: applied | decision: Adopt-modified
  - 발견 (cross-LLM review default): `ranking_runs.result` opaque JSONB pass-through(ARCH §7-1) ↔ `GET /api/v1/feed` 적합도 순 cursor feed(F-009/F-010) 충돌 — opaque만으론 정렬·페이지네이션 계약면 부재.
  - 결정: Adopt-modified — worker 소유 **`recommendations` feed projection**(scalar `rank_position`·`fit_level`·`status`) 추가(ARCH §3-2가 이미 worker-owned로 명명). NestJS는 projection으로 정렬·커서, `result`는 evidence로 opaque 유지. F-006(스키마)·F-007(영속)·F-009(서빙)·F-010(소비)·M2(§2) 반영.
- **M2-repair-2** | P1 | [관측됨] | linked: M2,F-010 | status: applied | decision: Adopt
  - 발견: 직군 분리 탭이 M2 §7·F-010 §5/§12에서 포함/비범위 미확정.
  - 결정: Adopt — **M2 비범위 확정**(A-7 의존, 단일 모델 시작 — Charter §5). M2 §4·F-010 §5/§12 닫음.
- **M2-repair-3** | P1 | [관측됨] | linked: F-006,F-008,F-009 | status: applied | decision: Adopt-modified
  - 발견: `crawl_runs` row cardinality 미정(coverage 기록 ↔ coverage API 동일 shape 의존).
  - 결정: Adopt-modified — **run별 1행 append** + coverage `last_success_at` = 채널별 `MAX(run_at WHERE status='success')` 파생. F-006 §4/§6 고정.
- **M2-repair-4** | P1 | [관측됨] | linked: F-011,M2 | status: applied | decision: Adopt
  - 발견: `worker.grounding` 이전 vs re-export 미정(ADR-103 alias 기각과 정합 필요).
  - 결정: Adopt — **이전(migrate) 확정**. F-011 §12 닫음(T-031 §8 해석 확정과 정합).
- **M2-repair-5** | P1 | [관측됨] | linked: F-007 | status: applied | decision: Adopt
  - 발견: `ranking_runs` upsert 키 미정(FAC-2 바이트 동일성·중복 run 방지 직결).
  - 결정: Adopt — `(resume_id, job_set_hash, model, prompt_version, scoring_mode, ranking_mode, cache_key_version)` 결정적 복합키. F-007 §6/§12 고정 → F-006 unique 제약 반영.

> `/repair-plan M2` round 2 (2026-06-06) — cross-LLM `/validate-plan`(default, **task-level T-018~T-031**) 회수. P0 1(cross-feature → 아래) + P1 5(task-scope → 각 task `## 8`) + P2 1(상위문서 "4테이블"→5, 직접 수정).

- **M2-repair-6** | P0 | [관측됨] | linked: F-007,F-010,T-020,T-022,T-023,T-026,T-029 | status: applied | decision: Adopt-modified
  - 발견 (cross-LLM review default, round 2): 보류(held) 공고가 end-to-end 미커버 — `run_scoring`은 held를 `pending_job_ids`에 두고 `final_ranking.ranking`에서 제외(pipeline.py:379/report.py:52)하는데, T-022는 `ranking`에서만 projection 생성 + T-020은 `fit_level Int`(non-null) → held 행 미생성/가짜 fit_level 강제 → F-010 "가짜 점수 대신 보류" AC 붕괴.
  - 결정: Adopt-modified — `recommendations.fit_level` **nullable** + held projection을 `pending_job_ids`에서 생성(fit_level=NULL·status='held'·scored 뒤 rank_position). T-020(nullable+`(run_id,rank_position)` index)·T-022(held 도출)·T-026(feed 포함·current run)·T-029(보류 렌더)·F-006/F-007 반영.

### M3

> `/repair-plan M3` (2026-06-07) — cross-LLM `/validate-plan`(reviewer-tag: default, M3 milestone + F-012~F-015 + tasks T-032~T-039) 회수. P0 1(feature scope, 아래) + P1 7(task scope → 각 task `## 8`) + P2 1(T-036 doc-link, cap 보호로 §5 미영속·T-036에 직접 적용). 사이징 split로 **T-040(PII Safety Pass)·T-041(upload states)** 신설 — 의존성 변경(wave 재산출 필요).

- **M3-repair-1** | P0 | [관측됨] | linked: F-015,T-034,T-038 | status: applied | decision: Adopt
  - 발견 (cross-LLM review default): F-015:FAC-1 preview/evidence 요약 렌더에 필요한 데이터를 backend AC가 생산 안 함 — T-034 응답(`{resume_id,masked,placeholders}`)·F-013 NFR(content 미포함)이 T-038의 masked_preview/evidence 가정과 어긋남(builder가 mock/UI만 green 낼 위험).
  - 결정: Adopt — T-034 응답·AC-1에 `masked_preview`(마스킹본) + 결정적 `evidence_summary`(스킬·경력 수, `extract_skills_evidence` 비-LLM 부분 TS 이식) 추가. T-038 §8 인터페이스 갭 경고 해소(확정 계약 소비).

### M4

> `/repair-plan M4` (2026-06-07) — cross-LLM `/validate-plan`(reviewer-tag: default, M4 milestone + F-016~F-019, tasks 제외) 회수. 판정 ALL_GOOD. P0 0 + P1 3 영속(P2 0). 의존성 변경 없음.

- **M4-repair-1** | P1 | [관측됨] | linked: F-017 | status: applied | decision: Adopt-modified
  - 발견 (cross-LLM review default): 작업 상태 저장이 `scoring_jobs` 테이블(api) vs SQS로 열려 있고 api가 `queued` 기록 후 worker가 `running/done` 갱신 — DB 테이블이면 ARCH §3-2 "단일 writer" 위반.
  - 결정: Adopt-modified — 상태 테이블 **api 단일 소유**(폴링 대상), worker는 자기 테이블(`ranking_runs`)만 write·완료는 큐/산출물로 api에 전달(shared-write 금지). F-017 §1·§4·§12 반영.
- **M4-repair-2** | P1 | [관측됨] | linked: F-017 | status: applied | decision: Adopt
  - 발견: `held`가 job-level인지 recommendation-level인지 흔들림(상태머신 `done|held`를 작업 상태처럼 제시).
  - 결정: Adopt — **작업 상태 = `queued/running/done/failed`**, 개별 공고 `scored/held`는 `recommendations` 레벨로 분리. F-017 §1·§4·FAC-2 반영.
- **M4-repair-3** | P1 | [관측됨] | linked: F-018 | status: applied | decision: Adopt-modified
  - 발견: lottie가 F-018 범위에 들어왔으나 DESIGN.md §7/§8에 lottie 규칙 부재(문서 먼저 위반).
  - 결정: Adopt-modified — lottie 유지하되 **DESIGN.md lottie 규칙 추가를 UI task 선행 필수**(repair-plan 범위 밖)로 명시 + 미반영 시 CSS 모션 대체. F-018 §10·§12 반영.

### M5

> `/repair-plan M5` (2026-06-07) — cross-LLM `/validate-plan`(reviewer-tag: default, M5 milestone + F-020~F-023, tasks 제외) 회수. 판정 NEEDS_CHANGES. P0 2 + P1 3 영속(P2 0). 의존성 변경 없음. **비-workitem(Charter §5·ADR-108 D3·DESIGN §7) 편집은 repair-plan 범위 밖 → owed.**

- **M5-repair-1** | P0 | [관측됨] | linked: M5,F-020 | status: applied | decision: Adopt-modified
  - 발견 (cross-LLM review default): Charter §5 "다채널 비목표"를 반전하는 M5/F-020이 상위 승인(Charter scope-note)을 "나중"으로 미뤄 하위가 먼저 생김.
  - 결정: Adopt-modified — Charter §5 scope-note를 **M5 task 생성 전 필수 선행(blocking gate)**으로 격상(M5 §1·F-020 §0). Charter 편집 자체는 범위 밖 → 메인세션 owed.
- **M5-repair-2** | P0 | [관측됨] | linked: F-021 | status: applied | decision: Adopt-modified
  - 발견: coarse "피드 시 pgvector 즉석 쿼리"가 ARCH §3-2/§7-3(vector DML=Worker, api는 서빙만) 경계 위반.
  - 결정: Adopt-modified — coarse를 **worker-소유 projection에 materialize·api read-only**로 고침(F-021 §4). ADR-108 D3 "즉석 쿼리" 문구 정합은 범위 밖 → owed.
- **M5-repair-3** | P1 | [관측됨] | linked: M5,F-020 | status: applied | decision: Adopt
  - 발견: `N개 소스`·`목표 티어`가 미정이라 graduation 다의적.
  - 결정: Adopt — **ATS 어댑터 ≥1종 + 공식 소스 ≥3개** 검증 가능 최소치(F-020 FAC-1·M5 §5).
- **M5-repair-4** | P1 | [관측됨] | linked: F-021 | status: applied | decision: Adopt
  - 발견: per-JD 증분이 §3 Alternate path엔 즉시 deep, FAC-6엔 "다음 run"으로 흔들림.
  - 결정: Adopt — M5 필수=K-batch로 통일, per-JD 증분은 후속(F-021 §3 정합, ADR-108 D5).
- **M5-repair-5** | P1 | [관측됨] | linked: F-021 | status: applied | decision: Adopt-modified
  - 발견: coarse 섹션 UI가 DESIGN §7 인벤토리에 없음.
  - 결정: Adopt-modified — coarse = **기존 JobCard를 적합도 배지 없이 재사용**(신규 컴포넌트 X)로 명시(F-021 §4). DESIGN §7 변형 추가는 owed.

### M6

> `/repair-plan M6` (2026-06-07) — cross-LLM `/validate-plan`(reviewer-tag: default, M6 milestone + F-024~F-027, tasks 제외) 회수. 판정 ALL_GOOD. P0 0 + P1 3 영속 + P2 2(doc-link/section-order, cap 보호로 §5 미영속·문서에 직접 적용). **의존성 변경(M6-repair-1) → wave 재산출 필요.**

- **M6-repair-1** | P1 | [관측됨] | linked: F-025,F-027 | status: applied | decision: Adopt
  - 발견 (cross-LLM review default): F-025↔F-027 선후관계 순환(둘 다 상대를 선행으로 둠).
  - 결정: Adopt — **단일 worker 배포(F-025) → 공유 캐시·다중화(F-027)** 일방향으로 끊음. F-025 §4·§10·F-027 §10 반영(**의존성 변경**).
- **M6-repair-2** | P1 | [관측됨] | linked: M6,F-024,F-027 | status: applied | decision: Adopt-modified
  - 발견: S3 실물 이전 소유자 불명확(M6/F-027은 S3 암시, F-024 FAC엔 없음).
  - 결정: Adopt-modified — 공유 캐시 **Postgres로 핀**(ARCH §7-3), **S3 미사용**(바이너리 저장 없음) 명시. M6 §2·F-024 §5·F-027 §1/§4 반영.
- **M6-repair-3** | P1 | [관측됨] | linked: F-025 | status: applied | decision: Adopt
  - 발견: crawler 실행면이 ARCH §7-3/ADR-101(GHA cron)와 다르게 "AWS 호스팅"으로 읽힘.
  - 결정: Adopt — **crawler=GitHub Actions cron, api/worker=AWS 호스팅**으로 분리(F-025 §1·§4).

> **repair-plan M4 round 2 (2026-06-07)** — cross-LLM `/validate-plan`(default, M4 + F-016~019 + **tasks T-042~052**) 회수. P0 4 + P1 5 영속(P2 1 doc-link=cap 보호 미영속·iface 줄 직접 적용). 의존성 변경 없음.

- **M4-repair-4** | P0 | [관측됨] | linked: F-016,T-042 | status: applied | decision: Adopt
  - 발견/결정: FAC-1 OAuth callback(users upsert+세션) 경로가 AC에 미매핑(T-042:AC-1=우회세션만) → T-042 **AC-5**(mock profile→`findOrCreateUser` upsert) 추가, FAC-1 재매핑.
- **M4-repair-5** | P0 | [관측됨] | linked: F-017,T-045 | status: applied | decision: Adopt
  - 발견/결정: FAC-2 worker `failed`(재시도 한도 초과) 미테스트 → T-045 **AC-4** 추가, FAC-2 재매핑.
- **M4-repair-6** | P0 | [관측됨] | linked: F-018,T-046 | status: applied | decision: Adopt
  - 발견/결정: FAC-4 empty/error 상태가 AC로 안 닫힘 → T-046 **AC-4**(empty+error) 추가, FAC-4 재매핑.
- **M4-repair-7** | P0 | [관측됨] | linked: F-019,T-050 | status: applied | decision: Adopt
  - 발견/결정: FAC-3 "skip→기본 피드 제외" 미명시 → T-050 AC-1을 `applied`/`skipped` 둘 다 제외로 확장.
- **M4-repair-8** | P1 | [관측됨] | linked: T-044,T-046,T-047,T-050 | status: applied | decision: Adopt-modified
  - 발견/결정: sizing >1 RGR 지적. **분할 대신 예외 사유** — M2/M3와 동일 vertical-slice granularity(CRUD/UI feature task=1 RGR), 사용자 anti-과분해. (예외 사유 본 log에 기록.)
- **M4-repair-9** | P1 | [관측됨] | linked: T-042,T-046~049,T-051,T-052 | status: applied | decision: Adopt
  - 발견/결정: 경로 불일치 정정 — web `src/components`→`components`, `schema_contract_test.py`→`test_schema_contract.py`, bare `--filter web`→`@podo/web`. *T-042는 이미 `@podo/api`였음(리뷰어 부분 FP).*
- **M4-repair-10** | P1 | [관측됨] | linked: T-047 | status: applied | decision: Adopt
  - 발견/결정: T-047 메모의 fenced gradient 위치(피드/카드 배경) ≠ DESIGN §2-4(로고·fit링·인사strip) → 정정(전면/카드 배경 gradient 금지).
- **M4-repair-11** | P1 | [관측됨] | linked: T-052 | status: applied | decision: Adopt
  - 발견/결정: T-052 §6-2 opt-out 형식(사유+Follow-up task 분리) 정정.

> **repair-plan M5 round 2 (2026-06-07)** — cross-LLM `/validate-plan`(default, M5 + F-020~023 + tasks T-062~069). P0 3 + P1 4 영속(P2 1 미영속). 의존성 변경 없음.

- **M5-repair-6** | P0 | [관측됨] | linked: T-063,T-065,T-067 | status: applied | decision: Adopt
  - 발견/결정: API task가 `src/routes/*.ts`+`/api/`(NestJS 아님) → 기존 NestJS module/controller/service + `/api/v1/`(ARCH §7-1, 실 repo `feed/`·`coverage/`)로 정정.
- **M5-repair-7** | P0 | [관측됨] | linked: F-022,T-066,T-067 | status: applied | decision: Adopt-modified
  - 발견/결정: T-067 confidence UI AC가 DB/API 계약 없이 worker `DomainResult.confidence`에만 의존 → T-066에 **worker-소유 `resume_domains` 영속(DDL=Prisma/DML=Python) + api read-only 서빙 AC-5** 추가, T-067은 그 계약 소비로 명시.
- **M5-repair-8** | P0 | [관측됨] | linked: F-022,T-068 | status: applied | decision: Adopt
  - 발견/결정: FAC-2 "분류→fit/랭킹 *실제 변경*" 미검증(분류 output/accuracy만) → T-068 **AC-4**(backend vs data 분류가 domain_alignment→fit/랭킹 바꿈) 추가, FAC-2 재매핑.
- **M5-repair-9** | P1 | [관측됨] | linked: T-062~069 | status: applied | decision: Adopt
  - 발견/결정: 경로 정정 — `crawler/`→`crawler/src/crawler/`, `ai/worker/*.py`→`ai/worker/src/worker/`, `podo/prisma`→`podo/apps/api/prisma`, `tests/crawler|api|web`→실경로, bare filter→`@podo/*`. (잔여 path 정규화는 validate-workitem이 실 repo 대비 검증.)
- **M5-repair-10** | P1 | [관측됨] | linked: T-062,T-063,T-065 | status: applied | decision: Adopt-modified
  - 발견/결정: sizing — 분할 대신 예외 사유(vertical-slice 선례, M4-repair-8 동일 근거).
- **M5-repair-11** | P1 | [관측됨] | linked: T-068 | status: applied | decision: Adopt-modified
  - 발견/결정: T-068↔F-020 의존: 확대 표본은 `ai/eval/fixtures/m5_expanded/` **큐레이션 수기 fixture(독립)** → depends_on 유지 + 주석으로 T-063 불요 명시.
- **M5-repair-12** | P1 | [관측됨] | linked: T-063 | status: applied | decision: Adopt
  - 발견/결정: T-063 §3-item6의 dangling `AC-4` 참조 → 애그리게이터 가드는 **T-062:AC-3**가 F-020 FAC-4 커버로 정정(별도 AC 불요).

> **repair-plan M6 round 2 (2026-06-07)** — cross-LLM `/validate-plan`(default, M6 + F-024~027 + tasks T-082~089). P0 0 + P1 4 영속(P2 3 미영속·prisma 경로/opt-out 직접 적용). **의존성 변경(M6-repair-13/14) → wave 재산출 필요.**

- **M6-repair-13** | P1 | [관측됨] | linked: T-084,T-086 | status: applied | decision: Adopt
  - 발견/결정: e2e-smoke 소유권 순환(deploy가 smoke green 요구↔smoke가 deploy URL 요구) → **T-084=deploy + pre-deploy schema-contract gate(URL 불요), e2e-smoke=T-086 소유**로 분리. T-084 AC-3·§4-1·§9 정정.
- **M6-repair-14** | P1 | [관측됨] | linked: T-088 | status: applied | decision: Adopt
  - 발견/결정: T-088 depends_on `[T-082,T-085]`(T-085=crawl cron 무관) → `[T-082,T-084]`(단일 worker 배포 선행).
- **M6-repair-15** | P1 | [관측됨] | linked: M6,T-082,T-083,T-084 | status: applied | decision: Adopt-modified
  - 발견/결정: IaC/호스팅 미정인데 task가 Terraform/ECS 전제 → **M6 §7에 Terraform+ECS/Fargate 기본 핀**(변경 시 AWS 호스팅 ADR + task §3/verifier 갱신).
- **M6-repair-16** | P1 | [관측됨] | linked: T-089 | status: applied | decision: Adopt-modified
  - 발견/결정: T-089 sizing(PII·dep·header 다관심) → 분할 대신 예외 사유(보안 baseline 단일 task) + opt-out 형식 정정.

> **repair-plan M4/M5/M6 round 3 (2026-06-07)** — cross-LLM `/validate-plan`(default; *실제 repo 파일까지 회수* — prisma schema·controller·cache.py·models.py). P0 4 + P1 16 영속(P2 3 미영속·직접 적용). **의존성 변경(M5-repair-16) → M5 wave 재산출.** 리뷰어 정확도 높음(repo 타입/경로 실측).

- **M4-repair-17** | P0 | [관측됨] | linked: T-042 | status: applied | decision: Adopt
  - 발견/결정: test-session이 AC=POST ↔ 구현=GET body 충돌(GET body는 ARCH §7-1 위반) → `POST /auth/test-session`으로 통일.
- **M4-repair-18** | P1 | [관측됨] | linked: T-042,044,045,046,047,050 | status: applied | decision: Adopt-modified
  - 발견/결정: sizing 재지적 → round2 M4-repair-8과 동일 결정 유지(vertical-slice=1 RGR, M2/M3 선례, 분할 X).
- **M4-repair-19** | P1 | [관측됨] | linked: T-044,T-045 | status: applied | decision: Adopt-modified
  - 발견/결정: 단일-writer 하 `running`/`failed` 갱신 경로 불명확 → **worker→`scoring-status-queue` 이벤트 emit → api status consumer가 `scoring_jobs` 갱신**(api 단일 writer)으로 일원화. T-044/T-045 반영.
- **M4-repair-20** | P1 | [관측됨] | linked: T-048,T-050,T-051 | status: applied | decision: Adopt
  - 발견/결정: §4-1↔write_set 불일치 → 테스트 파일·dotLottie package/lockfile(T-048)·migration/test/schema-contract(T-050)·spec(T-051) write_set 보강.
- **M4-repair-21** | P1 | [관측됨] | linked: T-048 | status: applied | decision: Adopt
  - 발견/결정: AC-2 "정적 프레임(또는 무렌더)" 모호 → **정적 첫 프레임(poster) 렌더**로 고정(마스코트 보임).

- **M5-repair-13** | P0 | [관측됨] | linked: T-063,T-065,T-067 | status: applied | decision: Adopt
  - 발견/결정: unversioned `/api/coverage`·`/api/feed` 잔여 → 전부 `/api/v1/...`(ARCH §7-1·기존 controller) 정렬.
- **M5-repair-14** | P0 | [관측됨] | linked: T-064,T-065,T-066 | status: applied | decision: Adopt
  - 발견/결정: `job_embeddings.job_posting_id TEXT` ↔ 실제 `JobPosting.id Int` 타입 불일치(migration 실패) → **INTEGER**로 정정 + coarse_candidates(job_posting_id INT·user_id TEXT)·resume_domains(resume_id INT) FK 타입 명시.
- **M5-repair-15** | P1 | [관측됨] | linked: T-062,063,065,066,068,069 | status: applied | decision: Adopt-modified
  - 발견/결정: sizing → vertical-slice 예외 사유(분할 X, 선례 일관).
- **M5-repair-16** | P1 | [관측됨] | linked: T-065,T-066,T-067 | status: applied | decision: Adopt
  - 발견/결정: T-066 write_set이 Prisma/API/schema-contract 누락 + T-065/T-067 모두 feed.controller 편집(병렬 충돌) → T-066 write_set 보강 + **T-067 depends_on에 T-065 추가(순차)**. *(의존성 변경 → M5 wave 재산출.)*
- **M5-repair-17** | P1 | [관측됨] | linked: T-066 | status: applied | decision: Adopt
  - 발견/결정: T-066 AC-5(resume_domains 영속·서빙)가 `## 3 구현 항목`에 단계 없음 → §3 item 5(migration+upsert+api+schema-contract) 추가.
- **M5-repair-18** | P1 | [관측됨] | linked: T-065 | status: applied | decision: Adopt-modified
  - 발견/결정: 스킬 매칭이 없는 `job_postings.tech_stack` 컬럼 가정 → **raw_text 키워드 기반**(구조화 JD JSONB는 ADR-108 D1 후속, M5 미도입).
- **M5-repair-19** | P1 | [관측됨] | linked: T-063 | status: applied | decision: Adopt
  - 발견/결정: AC-3(CoveragePanel UI)이 api test로 매핑 → web 컴포넌트 test(`coverage_panel.spec.tsx`)로 정정.
- **M5-repair-20** | P1 | [관측됨] | linked: T-065 | status: applied | decision: Adopt-modified
  - 발견/결정: CoarseSection 신설이 DESIGN §7-3(JobCard variant 재사용)과 충돌 우려 → **섹션 wrapper**(JobCard no-badge variant 렌더, 새 카드 X)로 명시.

- **M6-repair-17** | P0 | [관측됨] | linked: F-025 | status: applied | decision: Adopt
  - 발견/결정: FAC-1 "배포 전 e2e-smoke green"이 round2 split(post-deploy smoke)과 불일치 → "schema-contract pre-deploy gate + e2e-smoke post-deploy"로 정정, 매핑 T-084:AC-1·T-086:AC-1.
- **M6-repair-18** | P1 | [관측됨] | linked: T-084,T-086 | status: applied | decision: Adopt
  - 발견/결정: T-086 §3-5가 deploy-*.yml에 `needs:[…,e2e-smoke]` 추가 지시(순환 재발) → 제거. T-086은 post-deploy e2e-smoke만 소유.
- **M6-repair-19** | P1 | [관측됨] | linked: T-085 | status: applied | decision: Adopt
  - 발견/결정: crawler cron이 `OPENAI_API_KEY` 포함 → crawler=Collector(LLM 미호출, ARCH §3-2) → **DATABASE_URL만**으로 좁힘.
- **M6-repair-20** | P1 | [관측됨] | linked: T-085 | status: applied | decision: Adopt
  - 발견/결정: prisma 경로 오류 + 새 last_crawl 컬럼 대신 **기존 `crawl_runs`(M2) 재사용**(migration 불요) + coverage API write_set 보강.
- **M6-repair-21** | P1 | [관측됨] | linked: T-088 | status: applied | decision: Adopt
  - 발견/결정: cache 경로 `ai/worker/cache.py` → 실제 `ai/worker/src/worker/cache.py`로 정정(orphan 파일 방지).
- **M6-repair-22** | P1 | [관측됨] | linked: T-086 | status: applied | decision: Adopt-modified
  - 발견/결정: Playwright 신규 도입(deps/config 누락) → **기존 `scripts/e2e.mjs`를 `E2E_BASE_URL`로 재사용**(T-052/M2 패턴, 신규 dep 0).
- **M6-repair-23** | P1 | [관측됨] | linked: M6,T-082,T-083 | status: applied | decision: Adopt
  - 발견/결정: IaC 도구 "열린 질문"이 verifier(terraform)와 모순 → **Terraform 확정**(M6 §7 정합) task 본문 반영.
