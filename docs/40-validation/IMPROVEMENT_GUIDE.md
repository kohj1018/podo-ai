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

## 1. 우선순위

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

## 3. 권장 리팩토링

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
