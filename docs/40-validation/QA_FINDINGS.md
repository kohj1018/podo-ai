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

## 일반

### P0

### P1

### P2

### 관찰 메모
