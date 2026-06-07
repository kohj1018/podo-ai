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

## M2

> `/stabilize-milestone M2` (2026-06-06) qa 위임 + 메인 세션 직접 검증 결과. 대상: T-018~T-031 (polyglot 서비스 와이어링 — DB 영속·API 서빙·crawler cron·feed UI·worker 경계 하드닝). 통합 validate exit 0(130 passed / 13 skipped — DB-gated + jsdom-deferred) 위에서 *lint/type/unit이 못 잡는* 결정성·소유권·엣지·게이트 정합 점검. **코드-결함 P0 0건 → graduation의 #5 (QA_FINDINGS P0) 기준은 충족.** (단 §5 #3 E2E·#6 GS-1-through-DB는 별도 — IMPROVEMENT_GUIDE 참조.) finding 전수 기록(ADR-046#d3). QA-M2-001은 qa subagent와 메인 세션이 독립 수렴 — 신뢰도 상승.

> **Fix round 2026-06-06** (메인 세션, stabilize 회수 + 커밋): **resolved** — QA-M2-001(report.py `sorted(pending_job_ids)` + test_report.py), QA-M2-002(recommendations `@@unique([run_id,job_posting_id])` + migration `20260606130000_rec_unique` + contract assert), QA-M2-006(feed currentRun `id desc` 보조정렬), QA-M2-007(crawler 빈 fetch 전체마감 guard + test), QA-M2-008(schema-contract `fit_level` nullable + unique assert). **deferred** — QA-M2-003(accepted-with-note 유지), QA-M2-004(coverage N+1 — 채널 확장 전), QA-M2-005(int 캐스팅 — 낮음). 검증: 게이트 exit 0(131 passed) + clean DB(podo_test) 5 passed.

> **Fix round 2 (E2E) 재grade 2026-06-06** (메인 세션): graduation §5 #3(fresh-clone E2E) + #6(GS-1-through-DB) 회수 → **졸업 가능 YES**. 코드결함 신규 0 — `### P0` 0 유지. 실측: keyed score 6 scored/0 held → keyless 재채점 result byte-identical(`3a4680f5`) → `pnpm e2e` exit 0(crawl fixture→웜캐시→api 서빙→feed/coverage assert). 상세 [IMPROVEMENT_GUIDE M2-E2E-001](IMPROVEMENT_GUIDE.md).

### P0
없음. (worker 소유권 write 경계·held(LLM miss) 보류 영속·verbatim JSONB 저장·복합키 upsert 모두 충족. 데이터 손실·무결성 파괴급 결함 없음.)

### P1
- **QA-M2-001** | P1 | [관측됨] | linked: T-022 | status: open | `ai/worker/src/worker/report.py:52` (← `pipeline.py:211/292/379`)
  - 발견: `build_report`가 `"pending_job_ids": list(pending_job_ids)`로 저장하는데 `pending_job_ids`는 `set[str]`(pipeline.py). `list(set[str])`의 순서는 PYTHONHASHSEED에 의해 **프로세스마다 비결정적** → `python -m worker`를 2회(별도 프로세스) 돌리면 저장된 `ranking_runs.result` JSONB의 `pending_job_ids` 배열 순서가 달라져 **byte-identical 위반**(FAC-2 / GS-1-through-DB).
  - 근거: jsonb는 객체 키만 정규화하고 **배열 순서는 보존**한다. `persistence.py:121`이 *recommendations held 행*은 `sorted(...)`하므로 사용자 노출 점수·정렬은 결정적이나, *result JSONB의 pending_job_ids*는 정렬 없이 저장. 무키 fresh-clone E2E 경로(전 공고 cache miss → 전부 held)에서는 held가 다수라 이 hole이 **상시 노출**. 인-프로세스 라운드트립 테스트(test_persistence.py)는 단일 프로세스라 동일 set→list 순서로 통과 → **검출 불가**(oracle gap).
  - 결정/권장: `report.py:52`를 `sorted(pending_job_ids, key=int)`(또는 `sorted(str(j) for j in pending_job_ids)`)로 교체(one-line). + 별도 프로세스 2회 실행 결정성 테스트 추가. `/repair-workitem T-022`.

### P2
- **QA-M2-002** | P2 | [관측됨] | linked: T-020,T-026 | status: open | `podo/apps/api/src/feed/feed.service.ts:41-55` + `prisma/schema.prisma:64-77`
  - 발견: `recommendations`에 `(run_id, job_posting_id)` UNIQUE 제약이 없다. feed의 per-page `seen` dedup + `nextCursor = recs.length===take`는 *run당 job_posting_id 유일*을 암묵 전제. persist_run이 각 공고를 scored XOR held로 1회만 insert하므로 현재는 무결하나, 제약 부재로 미래 중복 insert 시 dedup이 cross-page를 못 잡고 nextCursor가 어긋날 수 있는 *잠재* 위험. (reviewer REV-M2-003 DELETE-reinsert WHY와 수렴.)
  - 결정/권장: `@@unique([run_id, job_posting_id])` 추가(불변식을 DB로 승격) + `nextCursor`를 dedup-후 `items.length` 기준으로 견고화. accept-with-note(현 데이터 무결).
- **QA-M2-003** | P2 | [관측됨] | linked: T-023 | status: accepted-with-note | `ai/worker/src/worker/__main__.py:19-39`
  - 발견: `_ensure_seed_resume`가 `resumes`(§3-2상 **api 소유**)에 worker가 write — 소유권 규칙1 위반 외형. (qa subagent가 P1로 제기.)
  - 근거/완화: **T-023 §8에 문서화된 M2 편의 예외** — "M2엔 api 업로드 경로 부재 → 진입점이 seed 1회 멱등 주입, 후속 api seed 경로 생기면 이관." 의도적·문서화·follow-up 명시 → 경계 위반 아님(validator도 수용).
  - 결정/권장: M3에서 api/migration으로 seed 이관 시 닫음. 현 상태 accept.
- **QA-M2-004** | P2 | [관측됨] | linked: T-027 | status: open | `podo/apps/api/src/coverage/coverage.service.ts:27-48`
  - 발견: 채널당 2 쿼리 × 2채널 = 요청당 4 쿼리(N+1). 채널 2개라 즉각 문제 없음.
  - 결정/권장: `crawl_runs` 단일 `GROUP BY channel`(`MAX(run_at) FILTER (WHERE status='success')` + `DISTINCT ON`)로 통합. 채널 확장 전 리팩터.
- **QA-M2-005** | P2 | [가설] | linked: T-022 | status: open | `ai/worker/src/worker/persistence.py:107-118`
  - 발견: `int(fr["job_id"])`·`int(jid)` 암묵 캐스팅 — job_id가 비정수 문자열이면 `ValueError`. 정상 경로(DB autoincrement int)는 안전하나 픽스처/미래 소스 확장 시 취약.
  - 결정/권장: 의미 있는 에러 메시지 보강 또는 int 보존. 낮은 우선순위.
- **QA-M2-006** | P2 | [관측됨] | linked: T-026 | status: open | `podo/apps/api/src/feed/feed.service.ts:25-28`
  - 발견: `currentRun`을 `created_at: 'desc'`만으로 선택 — 동일 ms 두 run insert 시 tie 비결정적. warm-cache 재실행은 복합키 UPDATE(id 불변)라 안전, 다른 입력 두 run의 극단 동시 insert만 위험.
  - 결정/권장: `orderBy: [{created_at:'desc'},{id:'desc'}]` 보조 정렬 추가.
- **QA-M2-007** | P2 | [관측됨] | linked: T-024 | status: open | `crawler/src/crawler/persistence.py:76-84` (reviewer REV-M2-006 cross-list)
  - 발견: 빈 fetch(`jobs == []`)일 때 `closed = existing - today_urls`가 해당 source 전체 공고를 **마감 처리**. fetch 실패로 빈 결과가 온 날이면 정상 공고를 일괄 마감하는 오동작 가능. F-008 "신규 0건 날 정상 기록" 엣지와 충돌 소지.
  - 결정/권장: `if closed and jobs:` guard 또는 "빈 fetch=전체 마감이 의도" WHY 주석 명문화. `/repair-workitem T-024` 후보.
- **QA-M2-008** | P2 | [관측됨] | linked: T-020,T-021 | status: open | `ai/tests/test_schema_contract.py:69-78`
  - 발견: schema-contract가 `recommendations.fit_level` *존재*만 assert하고 **nullable 여부는 미검증**. nullable은 M2-repair-6(held=NULL) 핵심 불변식인데, 미래 마이그레이션이 `NOT NULL`로 되돌려도 contract가 green → held insert가 런타임에야 깨짐. `crawl_runs` 정렬 인덱스 assertion도 부재.
  - 결정/권장: `fit_level`의 `is_nullable='YES'` assert 추가(R6 가드를 M2-repair-6 불변식까지 확장). accept-with-note.

### 관찰 메모
- **13 DB-gated skips가 graduation 시점에 남기는 미검증**: 실 DB에서의 ① 7컬럼 복합 unique·인덱스 실존, ② GS-1 byte-identical JSONB(실 DB 왕복), ③ persist→feed end-to-end held NULL, ④ upsert 멱등성. *task-time(T-021/022/026/027 validation report)엔 DATABASE_URL 주입 라이브 green*이나, 본 stabilize run은 DATABASE_URL 미설정으로 skip. graduation E2E가 이를 닫아야 함.
- GS-1 사용자 노출 신호(fit_level·band·rank_position)는 결정적(recommendations sorted + ranking 결정론). 비결정성은 *evidence blob의 pending_job_ids 배열 순서*에 국한(QA-M2-001).
- crawler `__main__.py`: `now` 1회 생성 후 두 채널 공유 — 설계 의도(결정성), defect 아님(`last_success_at` MAX 파생은 정상).
- **M1 carryover**: QA-M1-001(GS2_MIN_SAMPLE 비강제)은 `gates.py:101`에 `total < GS2_MIN_SAMPLE` 강제 추가됨 → **likely 해소**. QA-M1-002(`_is_grounded` 토큰 휴리스틱)은 여전히 존재 → open 유지(M2 eval 비범위).

## M3

> **[정식 재grade 2026-06-07]** Fix round(`f1f17df`: e2e.mjs 업로드 경로 재배선 + `e2e_pii_scan.py` + 업로드 fixture 웜캐시) 후 `/stabilize-milestone M3` 재실행 — **졸업 가능 YES**. 본 재grade는 app 코드 무변경(Fix round = E2E 하니스+웜캐시+docs만)이라 qa/reviewer *전수 재위임 없이* 초판 finding을 그대로 유지하고, Fix work에 직결된 단일 finding **QA-M3-006(오라클 갭)을 resolved로 전이**(실 masker→DB end-to-end 실증). 본 세션 실측: validate exit 0(TS 32/Python 134 passed, 17 DB-skip) · `pnpm e2e` exit 0(업로드 resume_id=14→마스킹 placeholders=5→웜캐시 채점→PII scan 0/5 literal→feed scored 6/held 0/toss+daangn). **### P1 잔여 open = 0**(QA-M3-006 closed).
>
> `/stabilize-milestone M3` (2026-06-07, 초판) qa 위임 + 메인 세션 직접 검증 결과. 대상: T-032~T-041 (doc reconcile + 이력서 업로드 API·스키마·PII 마스킹·스코어링 연결·업로드 UI·PII Safety Pass). 통합 validate exit 0(TS 32 passed / Python 134 passed, 17 DB-gated skip) + `pnpm e2e`(초판=seed 경로 / 재grade=업로드 경로) exit 0 위에서 *lint/type/unit이 못 잡는* 마스킹 robustness·cross-stack subprocess 경계·결정성·소유권 정합 점검. **코드결함 P0 0건 → graduation #5(QA_FINDINGS P0) 기준 충족.** (단 §5 #3 업로드-경로 E2E는 미배선 — graduation E2E gate는 [IMPROVEMENT_GUIDE M3-E2E-001](IMPROVEMENT_GUIDE.md) 참조.) finding 전수 기록(ADR-046#d3). **메인 세션이 qa P1 2건을 검증 후 P2 하향**: QA-M3-001(이메일 내 RRN이라는 pathological 입력 필요 + 잔여는 비식별 도메인 파편), QA-M3-002(error.filter가 비-HttpException을 generic 'Internal server error'로 직렬화 → client 미노출 + worker는 *마스킹본*만 읽음). 수렴 신호(신뢰도↑): QA-M3-004(evidence-summary TS↔Python divergence)를 qa·reviewer(REV-M3-003) 독립 발견.

### P0
없음. (마스킹 하류 6표면 literal scan 0건[T-040, DB 주입 실증] + 캐시 키 결정성 보존[resume_id 추가가 정규화 입력만 확장] + 테이블 소유권 경계 유지[api=resumes write, worker=ranking_runs/recommendations]. 실 PII 누출·데이터 무결성 파괴급 결함 없음.)

### P1
- **QA-M3-006** | P1 | [관측됨] | linked: T-040 | status: **resolved (Fix round `f1f17df` + 정식 재grade 2026-06-07)** | `ai/tests/test_pii_safety.py:50-58` → `scripts/e2e_pii_scan.py`
  - 발견: PII Safety Pass(T-040)의 `resumes.content` 표면은 **고정 known-value 오라클**(테스트가 직접 placeholder 치환)로 생성되며, 실 `RegexResumeMasker`(NestJS TS)의 regex 경계 동작을 end-to-end로 검증하지 않는다. 실 masker→DB surface-1 링크는 stabilize E2E(실 업로드)가 authoritative인데, 현 `scripts/e2e.mjs`는 업로드 phase가 미배선(seed 경로로만 채점)이라 그 검증이 *부재*.
  - 근거: 하류 표면(`ranking_runs.result`·`recommendations`·로그·`.cache/llm`·웜캐시)의 raw PII 0은 실증됨(주 누출 표면 안전). 그러나 "NestJS 마스커가 모든 PII 변종을 실제로 잡아 surface-1을 만든다"의 end-to-end 보증은 oracle 치환으로 이연. T-036(마스커 단위) + T-040(하류 표면) + *업로드 E2E*(미완)의 3-way 커버리지 중 마지막 한 변이 비어 있음.
  - 결정/권장: M3-E2E-001(업로드-경로 E2E 배선) 시 e2e.mjs에 실 업로드 POST → `resumes.content` DB scan 단계를 추가해 실 masker end-to-end를 닫는다. graduation §5 #3·#7 직결.
  - **해소(Fix round + 재grade 실측):** `scripts/e2e.mjs` phase 5가 실 PII fixture를 `POST /api/v1/resumes`로 업로드 → NestJS `RegexResumeMasker`가 실제 마스킹(placeholders=5) → phase 6 `scripts/e2e_pii_scan.py`가 *실 DB*의 `resumes.content`(masker가 만든 surface-1) + `ranking_runs.result`를 읽어 fixture의 알려진 raw PII 5종(이름·email·phone·RRN·개인URL) literal scan = **0건**, `[MASKED_]` 토큰 존재 sanity 통과. 본 재grade 세션 `pnpm e2e` exit 0으로 실 masker→DB end-to-end 변을 실증 — 3-way 커버리지의 마지막 변이 채워짐. (잔여 P2: QA-M3-001 치환 순서 edge-case는 별개로 open.)

### P2
- **QA-M3-001** | P2 | [관측됨] | linked: T-036 | status: open | `podo/apps/api/src/resumes/resume-masker.port.ts:42-51`
  - 발견: 치환 순서가 RRN(1)→EMAIL(2)이라, 이메일 local-part에 raw 주민번호가 박힌 pathological 입력(`user900101-1234567@example.com`)에서 RRN이 먼저 `[MASKED_RRN]`로 치환되면 EMAIL_RE의 local-part 클래스(`[A-Za-z0-9._%+-]`)가 `]`를 불허해 매칭 실패 → `@example.com` 도메인 파편 평문 잔류.
  - 근거/완화: RRN 자체는 마스킹됨(직접 식별자 제거). 잔류는 비식별 도메인 파편이고, 이메일에 13자리 RRN을 local-part로 넣는 조합은 극히 희귀. over-masking(RRN regex가 일반 13자리 매칭)은 안전 방향.
  - 결정/권장: 치환 순서를 EMAIL→RRN→PHONE으로 교환(이메일 통째 토큰화 후 잔여에서 RRN). 낮은 우선순위.
- **QA-M3-002** | P2 | [관측됨] | linked: T-037 | status: open | `podo/apps/api/src/resumes/worker-runner.port.ts:22`
  - 발견: `SubprocessWorkerRunner`가 `stdio: 'inherit'`로 기동 → worker stdout/stderr가 api 프로세스 stdio로 직접 흐른다. Python traceback에 resume 스니펫이 실릴 경우 로그 유출 경로(단 worker는 *마스킹본*만 읽으므로 raw PII 아님). client 응답은 error.filter가 generic 'Internal server error'로 보호(노출 안 됨 — qa 초판 P1의 client-envelope 우려는 무효).
  - 결정/권장: `stdio: ['pipe','pipe','pipe']`로 stderr 수집 후 `console.error`만. 로그 위생 — masked-only라 P2.
- **QA-M3-003** | P2 | [관측됨] | linked: T-036 | status: open | `podo/apps/api/src/resumes/resume-masker.port.ts:19-31`
  - 발견: `/g` 플래그 정규식이 모듈 레벨 상수로 선언·`mask()`마다 재사용. 현재 `String.replace(regex, fn)`은 lastIndex를 reset하므로 안전하나, 미래에 `exec` 루프로 리팩터링되면 모듈 공유 `lastIndex`가 stateful 버그가 된다. (동형 잠재: `MaskingPreview.tsx:23` `PLACEHOLDER_RE.test()` — 현 alternation 구조에선 정상.)
  - 결정/권장: 방어적으로 `mask()` 내부에서 regex 재생성 또는 주석으로 "replace-only 가정" 명문화. accept-with-note.
- **QA-M3-004** | P2 | [가설] | linked: T-034,T-037 | status: open | `podo/apps/api/src/resumes/evidence-summary.ts` ↔ `ai/worker/src/worker/parse_resume.py` (reviewer REV-M3-003 cross-list)
  - 발견: 업로드 즉시 preview용 evidence 카운트(TS `evidence-summary.ts`)와 스코어러의 skills evidence(Python `parse_resume`)가 **독립 2구현**. 섹션 헤딩/불릿 인식 정규식이 미묘히 달라(예: Python은 불릿 라인도 섹션 경계로 인식, TS는 `#` 헤딩만) preview "스킬 N개"와 실제 채점 evidence 수가 어긋날 수 있음(데이터 무결성 아님, UX 불일치).
  - 결정/권장: 두 정규식 동치화 또는 evidence-summary.ts에 "parse_resume.py와 동기 필수" WHY 주석. (REV-M3-003 권장과 수렴.)
- **QA-M3-005** | P2 | [관측됨] | linked: T-037 | status: open | `ai/worker/src/worker/__main__.py` `_parse_resume_id`
  - 발견: `--resume-id`/`RESUME_ID` 값을 `int()`로 try/except 없이 파싱 → 비정수 입력 시 traceback + 비정상 종료. 정상 경로는 안전(controller가 `Number.parseInt`+양수 검증 후 전달).
  - 결정/권장: `ValueError` 처리 + `sys.exit(2)` + 도움말. 직접 CLI 오용 방어용 — 낮은 우선순위.

### 관찰 메모
- **OBS-M3-1** `worker-runner.port.ts:18` — `REPO_ROOT` 미설정 시 `process.cwd()/../../..` 가정. e2e.mjs가 올바른 cwd 보장이라 현재 무해하나, M4 컨테이너 분리/dist 번들 실행 시 경로 오산 가능 → 배포 전 `REPO_ROOT` env 필수 문서화.
- **OBS-M3-2** `persistence.py load_resume` — 업로드 이력서 domains를 config 기본(frontend/backend)으로 고정(자동 분류 비범위, T-037 §8). 타 도메인 이력서는 fit_level 편향 가능 — M4 자동 분류 시 회귀 메모(REV-M3-006과 수렴).
- **OBS-M3-3** `resumes.controller.ts` — 확장자 검증이 `originalname`(클라이언트 제공) 기반 → `evil.pdf`→`evil.txt` rename 우회 가능. 바이너리→utf8 디코드 시 `�` 혼입(데이터 품질 저하, PII 위험 아님). M4 MIME 검증 고려.
- **M2 carryover**: QA-M2-001(pending_job_ids sorted) **해소 확인**(Fix round 2 byte-identical 실측). QA-M2-003(worker가 `resumes`에 seed write — 소유권 편의 예외, "M3 api 이관 시 닫음") **부분 잔존**: M3가 api 업로드 write 경로를 신설했으나 *seed* 이력서는 여전히 worker `_ensure_seed_resume` 주입(keyless E2E 보존용 — REV-M3-007 M4 제거 후보). 완전 닫힘은 M4.
- GS-1-through-DB: `resume_id`는 캐시 키의 *이력서 정규화본* 축을 채울 뿐(시간·랜덤·env 무혼입) → 결정성 구조 불변(§3-1 규칙 충족). seed 경로(resume_id=None)도 M2와 byte 동일 동작.

## M4

> `/stabilize-milestone M4` (2026-06-08) qa 위임 + 메인 세션 직접 검증(worker consumer 코드 실독) 결과. 대상: T-042~T-052 (OAuth 멀티유저·데이터 격리 / SQS(LocalStack) 큐 트리거 + Python worker 상시 consumer / 동반자 피드 UX 8-상태·근거·모션·a11y / 지원기록). 통합 validate exit 0(TS 62 passed[api 25/web 37] + 10 DB-skip / Python 135 passed + 22 DB-skip) + **`pnpm e2e` exit 0**(2-user OAuth 우회→업로드(resume 26/27)→SQS 큐 드레인→격리 피드 A scored 4·B scored 6/held 0→데이터 격리(401·403/404)→지원기록 정리→PII scan 0 raw·0 account) 위에서 *lint/type/unit이 못 잡는* 데이터 격리·계정 PII 비유입·큐 멱등/실패·세션 보안·UX 상태 정합 점검. **코드결함 P0 0건 → graduation §5 #5(QA_FINDINGS P0) 충족.** finding 전수 기록(ADR-046#d3). **메인 세션이 qa P1 1건(QA-M4-001)을 worker 코드 실독 후 P2 하향**(delete-after-failed는 M4 의도 동작 — AC-4 terminate-on-failure·DLQ는 M6, failed 가시화는 T-045 §8 문서화 이연). 데이터 격리(핵심 안전 게이트)는 qa subagent·E2E assert·메인 세션이 독립 수렴 — 신뢰도↑.

### P0
없음. (모든 user-facing 쿼리/뮤테이션에 session user_id 스코프 또는 소유권 가드 존재 — feed(`where: resume.user_id`)·resumes/score(403)·scoring-jobs(404)·applications(deleteAction 403, getActions 본인 범위). E2E `assertIsolation`이 비인증 401·A→B 403/404 실증. 계정 PII는 SQS 페이로드 `{resume_id, job_id}`·세션 `{id}`만 — `ranking_runs.result`/`.cache/llm`/로그 유입 0(E2E account-pii-scan 4 literal 0). 크로스유저 유출·데이터 무결성 파괴급 결함 없음.)

### P1
없음. (qa subagent가 제기한 QA-M4-001은 메인 세션 검증 후 P2 하향 — 아래 근거. 상태채널 arch-debt는 reviewer surface로 [IMPROVEMENT_GUIDE REV-M4-003/010](IMPROVEMENT_GUIDE.md)에 P1 기록.)

### P2
- **QA-M4-001** | P2 (qa P1 → 메인 하향) | [관측됨] | linked: T-045 | status: open | `ai/worker/src/worker/__main__.py:172-176`
  - 발견: `consume_once`가 `process_message` 반환값(done/failed)과 무관하게 항상 `delete_message` → 재시도 한도(3회) 초과로 failed된 메시지도 큐에서 제거(DLQ 미이동).
  - 근거(하향): M4는 DLQ/redrive 미도입(M6 인프라). 메시지를 *남기면* visibility timeout 후 재배달→3회 재시도 무한 반복 = AC-4 "무한 재시도 없이 종료" 위반. 따라서 3회 후 삭제(종료)는 M4 의도 동작. 잔여(failed 상태가 `scoring_jobs.status`에 미반영 → 피드 영구 scoring 표시)는 T-045 §8이 "failed 가시화는 후속/M6"로 문서화 이연 + [REV-M4-003/010] 상태채널 arch-debt와 동일 뿌리.
  - 결정/권장: M6 DLQ(redrive policy) + 상태채널 consumer 도입 시 닫음. 현 M4 happy-path는 done(ranking_run join)으로 충분.
- **QA-M4-002** | P2 | [관측됨] | linked: T-051 | status: open | `podo/apps/web/components/JobCardActions.tsx:45-55`
  - 발견: `apply()`가 record API 호출 전 `onProcessed?.(jobId)`로 낙관적 정리 + `window.open`. 롤백(`onRestore`)은 존재·호출되나 부모가 `onRestore` prop을 안 주면 실패 시 카드가 영구 제거 잔류(서버엔 미기록).
  - 근거: FeedList/JobCard 결선에서 `onRestore` 전달 확인됨(web 회귀 0). 단 prop 의존이라 미전달 호출지점이 생기면 UI↔서버 불일치.
  - 결정/권장: `onRestore` 필수 prop 계약화 또는 url 유무에 따른 낙관적 정리 순서 명문화. 낮은 우선순위.
- **QA-M4-003** | P2 | [관측됨] | linked: T-044 | status: resolved (repair-workitem 2026-06-08 — 생성자 throw 적용) | `podo/apps/api/src/queue/queue.service.ts:19` (reviewer REV-M4-005 수렴)
  - 발견: `SQS_QUEUE_URL` 미설정 시 `?? ''` 빈 문자열로 부팅 — 주석은 "early detection"이나 실제 실패는 enqueue 시점(500). M6 배포 환경변수 누락을 startup이 아닌 런타임에 노출.
  - 결정/권장: 생성자 guard(`if(!url) throw`). qa·reviewer 독립 수렴(신뢰도↑).
- **QA-M4-004** | P2 | [관측됨] | linked: T-042 | status: open | `scoring-jobs.controller.ts` + `resumes.service.ts` score()
  - 발견: `user_id=null`(seed/레거시) 이력서에 대해 scoring-jobs 폴링은 404(아무도 조회 불가), `score()`는 통과(`if(resume.user_id && ...)`) — 소유권 비대칭.
  - 근거: T-042 §8 "소유권/격리는 user_id 있는 이력서에만(tolerant), seed(null)는 하위호환 미차단" 의도와 정합하나 폴링 404는 부수효과. 실 업로드는 항상 소유자 부여라 M4 위험 낮음.
  - 결정/권장: M5 seed 정리(REV-M3-007/REV-M4-002 seed shim 제거)와 함께 닫음.
- **QA-M4-005** | P2 | [관측됨] | linked: T-050 | status: open | applications dto + `JobCardActions.tsx`
  - 발견: `ApplicationAction`에 `'unfavorite'` 타입 정의되나 UI 버튼·E2E 커버리지 없음(dead type). favorite 토글 해제 경로 미노출.
  - 결정/권장: M5 즐겨찾기 페이지에서 구현 또는 타입 제거.

### 관찰 메모
- 세션 보안: `httpOnly:true` 고정 · `sameSite`/`secure` isProd 분기 · CORS `credentials:true` + 명시 origin(와일드카드 없음) · `/auth/test-session` `NODE_ENV!=='test'` 403 가드 — 전부 확인.
- 계정 PII 비유입(ADR-105 Amend1): SQS 페이로드·세션 직렬화·strategy validate()에 email/display_name/accessToken 로그 0. E2E account-pii-scan 0.
- GS-1-through-queue: `persist_run` 복합키 upsert 멱등(중복 SQS 메시지→1 ranking_run) + recommendations DELETE/재삽입. T-045 AC-2가 2회 채점 동일 단언.
- held 렌더: JobCard held→PendingState(FitScoreRing/PassBand 미렌더, 숫자 점수 0). 가짜 점수 없음.
- worker retry: `MAX_RETRIES=3` + 지수 backoff 상한 10s, 초과 시 failed 반환 — 무한 루프 없음(AC-4).
- feed currentRun tie-break: `orderBy [{created_at:desc},{id:desc}]` — QA-M2-006 해소 유지.
- M3 carryover: QA-M3-006(오라클 갭) resolved 유지. QA-M2-003/REV-M3-007 seed write 편의 예외 = M4도 worker `_ensure_seed_resume` 잔존(큐 경로는 미사용 → dead shim, [REV-M4-002]로 이관).

## 일반

### P0

### P1

### P2

### 관찰 메모
