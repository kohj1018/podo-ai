# M4-product-mvp

## 0. Status
draft

## 1. 목적
M1~M3가 "검증된 알고리즘 → 도는 로컬 서비스 → 실 이력서 입력(마스킹)"까지 *기계*를 완성했다면, M4는 그 위에서 **DISCOVERY/Charter의 가장 핵심 워크플로우를, "진짜 나만의 맞춤형 AI 취업 에이전트"로 느껴지는 UI/UX로 끝까지 완성**한다. 네 축:
1. **핵심 일일 워크플로우 완성** — 사용자가 진입해 *자기* 단일 피드에서 신규/마감 diff가 반영된 공고를 적합도 5단계 배지·근거와 함께 보고, 지원/스킵·즐겨찾기로 처리해 "다음 날 누락 0"을 유지하는 루프(Charter §8 흐름1·2).
2. **동반자 에이전트 경험(UX 1순위)** — [DESIGN.md](../../20-system/DESIGN.md)가 박은 **"포도 ai · 포지션 도착! 마스코트가 매일 아침 맞는 자리를 골라 배달하는 동반자"** 정체성을 *실제로 실현*한다. 뻔한 SaaS가 아니라, 포도가 인사하고(GreetingCard)·공고가 "도착"하고(arrival 모션·lottie)·보류/빈 상태조차 포도가 정직하게 안내하는, 창의적이고 세련된 맞춤형 에이전트 경험. M2/M3가 기능 컴포넌트만 깐 것을 *경험으로* 끌어올린다.
3. **멀티유저(OAuth)** — GitHub·Google 소셜 로그인 + 사용자별 데이터 격리로 본인 이력서·피드·지원기록만.
4. **아키텍처 1차 완성** — M2가 "인증 미정"으로, M3가 "subprocess spawn(로컬 임시)"으로 둔 user-facing·오케스트레이션 계층을 [ARCH §7-1/§7-3](../../20-system/ARCHITECTURE_OVERVIEW.md)·[ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)이 박아둔 대로 실체화.

**새 스코어링 로직은 0** — 알고리즘 본체([SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md))는 SSOT 불변이고, 결정론(GS-1)·grounding(GS-2) 게이트는 멀티유저·큐 경로를 통과해도 보존된다.

> **배포·알림 기능·알고리즘 보강은 M4 비범위.** M4 done-line은 *로컬 멀티유저 E2E* — 단, **로컬 docker compose에서 LocalStack이 AWS(SQS/S3)를 대역**해 실제로 돌려본다(가정 A-INFRA). 공개 배포(실 AWS/Vercel)·매일 오전 cron 실가동은 **M6**, 이메일/푸시 알림 기능은 **나중**(M6도 cron만), 채용공고 커버리지 확대·벡터 사전필터·정규화 JD 영속·도메인 자동분류 같은 *알고리즘/데이터 보강*은 **M5**. (사용자 판단 2026-06-07.)

> **출력 계약 동결 (M4 진입 규율):** `fit_level`(1~5)·`recommendations` projection(rank_position·fit_level·domain_alignment·status)·`ranking_runs.result` JSONB shape를 **M4에서 freeze**한다. M5의 알고리즘 "강화"는 *이 계약 안에서의 정확도·비용*만 건드리고 출력 shape는 바꾸지 않는다 — 그래야 M4에서 완성한 UI가 M5에 재작업되지 않는다. 계약을 바꿔야 하는 변경(예: 새 evidence 필드·직군 분기 출력)은 M4 폴리싱 *전에* 결정한다.

> **Charter §5 "멀티유저" 비목표 반전 → ADR 선결.** Charter §5는 멀티유저를 self-proxy 단일 사용자 기준 *비목표*로 박았다. M4가 OAuth 멀티유저를 채택하므로 **구현 착수 전 ADR-107(멀티유저·OAuth 인증 범위 변경)을 신설**해 Charter/ARCH 범위를 정식 변경한다(M3 §4가 이미 "M4에서 다루려면 ADR로 범위 변경 선결"이라 예고).

## 2. 범위
M3 §4가 *비범위로 선고지*한 **"공개 배포 + auth + 멀티유저"** 중 **auth(OAuth) + 멀티유저**를 닫고(배포는 M6 잔류), M2/M3가 누적한 user-facing·UI 부채를 회수한다. 알고리즘 본체·캐시 키·feed projection 구조는 불변 — 새 스코어링 로직 0.
- **OAuth 인증 + 멀티유저** — 소셜 로그인(**GitHub·Google**) + httpOnly 쿠키 세션 + `users` 테이블(api 소유, ARCH §3-2) + `resumes`·`ranking_runs`·`recommendations` 및 신규 user-facing 테이블을 **사용자 범위로 격리**(본인 데이터만 조회·채점). 채점 트리거는 *요청 사용자가 해당 이력서의 소유자인지* 인가 후에만. **계정 PII 정책(ADR-105 amendment):** 계정 식별자(이메일·표시이름·provider account id·아바타 URL)는 식별이 *목적*이라 마스킹 안 함 → `users`에 **최소 식별자만** 저장(OAuth 토큰 미영속, 로그인 시점만 사용) + **계정 PII는 스코어링 경로(prompt·LLM·`.cache/llm`·`ranking_runs.result`·로그)에 절대 유입 금지**(M3 안전 불변식 유지) + 이력서 content는 기존대로 마스킹. [ARCH §7-1 인증 "미정→결정"]
- **워커 트리거 비동기화(ADR-106)** — M3의 NestJS→`uv run python -m worker --resume-id N` **subprocess spawn**(로컬 단일프로세스 임시)을 **큐 기반 트리거**로 교체한다. 멀티유저 동시 채점·재시도·상태(queued/running/done/held)를 받아내고, *LocalStack SQS로 로컬 구현 → M6에서 실 AWS SQS로 엔드포인트만 교체*(연습=실전 동일 경로, 폴리글랏 친화: NestJS AWS SDK enqueue / Python boto3 consume). 워커는 일회성 subprocess가 아니라 큐를 소비하는 상시 서비스로. [ARCH §7-3, IMPROVEMENT_GUIDE REV-M3-002]
- **동반자 에이전트 피드 경험 (UX 핵심, F-018)** — 진입 → GreetingCard(포도 인사+오늘의 카운트) → 단일 피드(중복제거 + **신규/마감 diff** + arrival 모션) → JobCard(적합도 5단계 배지 + FitScoreRing + 근거 펼침: JD 인용 grounding + 이력서↔JD 매핑) → 커버리지 투명성 패널. **로딩·에러·empty·보류 상태를 DESIGN.md §7-4 8-상태 매트릭스대로 일급으로**(포도가 안내) + 접근성 + lottie(arrival·로딩 등 *의미 전달*에 한정, 장식 금지) + 온보딩(첫 진입). DESIGN.md 시각 계약(토큰·fenced 그라데이션·마스코트 규율) 준수. M2/M3 deferred UI 부채(REV-M2-UI-001 error/empty·DSN-M3-001~003 a11y) 회수. [Charter §8 흐름1·2, DESIGN.md, ADR-049]
- **지원 의사결정 기록 (F-019)** — 지원/스킵·즐겨찾기 기록 + 처리완료 정리("다음 날 누락 0", Charter §8 흐름1-7). user-facing CRUD(NestJS 소유 신규 테이블). Fail #8(지원 기록 저장 실패) 대응. [Charter §6 happy 6·7 / alternate 2]
- **스키마 확장** — `users` + 사용자 격리 FK + 지원/즐겨찾기 테이블. Prisma DDL = 폴리글랏 계약 SSOT(ARCH §3-2), schema-contract test 동반 갱신.

> **폴더/구조 리팩토링은 *수술적·필요기반*으로 (사용자 판단 2026-06-07).** 현 `podo/`(TS Turborepo) + `ai/`·`crawler/`(Python uv) 분산 배치는 이미 폴리글랏 경계가 깨끗하고 M4 목표(멀티유저·큐·UX·지원기록)에 *구조 이동이 불필요*하다. 전면 `apps/services/packages` 이동은 *조직적 미관*일 뿐 기능 이득 0 + 모든 import·CI 경로 필터·turbo/uv 설정·웜캐시(`ai/worker/fixtures/llm_cache`)·`scripts/e2e.mjs`를 건드리는 고위험 작업이라 **M4에서 하지 않는다.** 구조 리팩토링은 *기능적으로 필요한 부분만*(예: M5 크롤러 source 어댑터 `crawler/sources/*`, M6 서비스별 Dockerfile), 해당 마일스톤에서, 전 경로·CI·캐시 영향 사전 정밀 분석 + 격리 PR + validate green으로. 기록은 신규 ADR 아니라 **ADR-101(D-MONO) amendment**로. 전면 미관 정리를 원하면 마일스톤 사이 단독 PR로.

> **불변 유지:** `RankingRun` 복합 unique 캐시 키·`Recommendation` projection·`ranking_runs.result` opaque JSONB는 M2/M3 구조 그대로. 멀티유저는 *어느 사용자의 어느 이력서인가*를 api 인가·쿼리 범위로 처리하고, 캐시 키(이력서 정규화본 기반)는 그대로 GS-1-through-DB를 보존한다. **벡터/임베딩·정규화 JD 영속은 도입하지 않는다**(M5).

## 3. 포함되는 기능 (F-016 ~ F-019, 잠정)
> 아래 F-NNN은 `/plan-workitem M4`가 정식 분해한다. 번호·경계는 plan 단계에서 조정 가능. **UX(F-018)에 task 비중을 가장 크게 둔다**(사용자 우선순위).
- **F-016 (oauth-and-multiuser)** — OAuth 소셜 로그인(GitHub·Google) + httpOnly 쿠키 세션 + `users` + 사용자별 데이터 격리(횡단 접근 차단) + 채점 인가 + 테스트 인증 우회 경로. **ADR-107 신설**(멀티유저·OAuth 범위 변경 + 세션 전략) + **ADR-105 amendment**(계정 PII). M4 **첫 작업**(다른 feature가 user 컨텍스트 의존). [ARCH §7-1, Charter §5 반전]
- **F-017 (worker-trigger-queue)** — ADR-106 실행: subprocess spawn → 큐(LocalStack SQS→AWS SQS) 트리거 + 채점 상태머신 + 동시성·재시도 + 워커 상시 소비 서비스화. = REV-M3-002 회수. [ARCH §7-3]
- **F-018 (companion-feed-experience)** — *UX 1순위*. 동반자 에이전트 피드 경험 완성: GreetingCard·arrival 모션·lottie·온보딩·JobCard(배지·근거)·커버리지 패널 + 8-상태 매트릭스(로딩/에러/empty/보류) + 접근성 + 마스코트 규율. M2/M3 UI 부채 회수. [Charter §8 흐름1·2, DESIGN.md, ADR-049]
- **F-019 (application-tracking)** — 지원/스킵·즐겨찾기 기록 + 처리완료 정리(누락 0). user-facing CRUD(NestJS 소유). [Charter §6 happy 6·7 / alternate 2, Fail #8]

## 4. 제외되는 기능
- **공개 배포(실 AWS/Vercel)** — M6. M4 done-line은 *로컬 멀티유저 E2E*(docker compose + **LocalStack이 AWS 대역**). 실 AWS 이전·CI/CD deploy workflow 실가동·도메인은 M6.
- **이메일/푸시 알림 기능 + 매일 오전 cron 실가동** — M6(그것도 cron만, 알림 기능 자체는 나중). **단, "매일 오전 크롤러가 신규 JD를 수집한다"는 전제를 반영한 UI/UX(신규/마감 diff 표시)는 M4 포함**(F-018). diff 데이터는 crawler가 이미 set하는 `diff_status`를 읽어 렌더 — 트리거(cron) 실가동만 M6. (사용자 판단 2026-06-07.)
- **전면 레포 구조 리팩토링** — M4 비범위(§2 수술적·필요기반 원칙). M5/M6에서 기능 동인 있는 국소 리팩토링만.
- **채용공고 커버리지 확대 + 알고리즘/비용 보강** — M5. 토스·당근 2곳 유지. 벡터 사전필터·정규화 JD 영속·증분 채점·업로드 이력서 도메인 자동분류·비용↔정확도 최적화 전부 M5(현 코드 미구현 — `persistence.load_resume` 도메인 하드코딩·pgvector 미사용 확인됨).
- **직군 분리 탭(Charter §8 흐름3)** — 업로드 이력서 도메인이 현재 하드코딩(frontend/backend)이라 직군 분기 UI가 *가짜*가 된다 → **도메인 자동분류(M5) 의존 → M4 보류**(단일 피드로 시작). M5에서 분류 생기면 탭 활성.
- **PDF/docx 업로드 — 확정 제외(사용자 판단 2026-06-07).** `.txt`/`.md`/paste만 유지(M3 동일). 바이너리 포맷 추출은 후속.
- **raw PII 영속·암호화 / 간접 재식별 방어** — M3 정책(마스킹본 only) 유지 + *본인만 접근*(F-016 인가). raw 암호화 at-rest·간접 재식별 방어는 공개 배포(M6)와 함께 재검토.
- **새 스코어링 로직·캐시 키 재설계** — SPEC SSOT 불변. 출력 계약 동결(§1).

## 5. 완료 기준 (graduation checklist)
> sprint contract: 외부 검증 가능한 "done" 기준 (ADR-014).
- [ ] 모든 task status: done
- [ ] 통합 validate Pass (ruff·mypy strict·pytest + Biome/Vitest + **schema-contract green** — `users`·격리 FK·지원/즐겨찾기 테이블 포함)
- [ ] **멀티유저 E2E Pass** — fresh clone → `docker compose up`(Postgres+pgvector + LocalStack SQS) + `prisma migrate dev` → **사용자 2명 OAuth 로그인(테스트 우회 경로) → 각자 이력서(`.txt`/paste) 업로드 → 마스킹 → 큐(SQS) 경유 채점 → 각자 *격리된* 피드에 적합도 5단계 배지 + 근거(JD 인용) + 커버리지 패널 + 신규/마감 diff 렌더 → 지원/즐겨찾기 기록 → 처리완료 정리**. 무키 결정성 경로는 *마스킹 fixture 이력서 + 웜캐시 + 큐 드레인*으로 보존(M2/M3 E2E 패턴 + 큐 재배선). 실 이력서 live score는 `OPENAI_API_KEY` 보유 시.
- [ ] AC 매핑 100% (validation report 기준)
- [ ] P0 severity finding 0건 (QA_FINDINGS의 M4 헤더 기준)
- [ ] **데이터 격리 Pass (필수)** — 사용자 A가 사용자 B의 이력서·피드·지원기록·채점결과에 *어떤 경로로도* 접근 불가(직접 id 추측·API 우회 포함)를 검증. 멀티유저 핵심 안전 게이트.
- [ ] **PII 불변식 유지** — M3 마스킹본-only(raw PII 미영속·미전송) + 본인만 접근 + 계정 PII는 `users` 최소 저장·스코어링 경로 미유입. ADR-105(amendment) 정합.
- [ ] **UX 완결성 (필수)** — DESIGN.md §7-4 8-상태(로딩/에러/empty/보류)·마스코트 규율·fenced 그라데이션·접근성이 핵심 화면에서 테스트로 단언. 동반자 경험(GreetingCard·arrival·온보딩)이 실제 동작.
- [ ] (선택) **GS-1-through-queue:** 동일 (이력서, 공고집합)을 큐 경로로 2회 채점 → 저장된 band/score/evidence 변동 0(캐시 hit).

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§5 멀티유저 비목표 — ADR-107로 반전, §6 GS-1/GS-2, §8 흐름1·2)
- Discovery (SSOT): [DISCOVERY](../../10-charter/DISCOVERY.md) (§6 시나리오 happy/alternate/fail, §7 F2·F5·F6·F7)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 폴리글랏 매핑·소유권, §7-1 인증·API, §7-3 워커 트리거·큐, §7-4 프론트)
- Design (UI SSOT): [DESIGN.md](../../20-system/DESIGN.md) (포도 동반자 정체성·마스코트·8-상태·arrival 모션·fenced 그라데이션)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (출력 계약 동결 기준 — 불변)
- 선행 마일스톤: [M3-resume-upload](M3-resume-upload.md) (§4 비범위 = M4 범위 정의)
- 개선 부채: [IMPROVEMENT_GUIDE](../../40-validation/IMPROVEMENT_GUIDE.md) (REV-M3-002 트리거 ADR / REV-M2-UI-001 error-state / DSN-M3-001~003 a11y / [Dependency])
- ADR: **새 ADR 2개** — ADR-106(가칭, 워커 트리거 큐/SQS — F-017) · ADR-107(가칭, OAuth 멀티유저 — F-016). **amendment 2개** — [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)#amend(D-MONO 구조 — 국소 리팩토링 시) · [ADR-105](../../90-decisions/project/ADR-105-pii-masking-policy.md)#amend(계정 PII). 그 외 인용: [ADR-103](../../90-decisions/project/ADR-103-eval-worker-boundary.md)·[ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md)(워커 경계).

## 7. 열린 질문
> **굵게 = 확정/권장 기본값.** ADR-106/107 + plan에서 마무리.
- **OAuth provider (ADR-107)** — **GitHub + Google 확정**(사용자 판단). 세션 = **httpOnly 쿠키 세션**(SSR Next.js 정합) 확정.
- **OAuth 로컬/CI 마찰** — redirect callback이 필요해 무키 E2E/CI는 **테스트 인증 우회(fake provider/시드 세션)** 경로 필수(웜캐시 패턴 정합) — 확정. 구체 우회 설계는 plan.
- **워커 트리거 메커니즘 (ADR-106)** — **LocalStack SQS → AWS SQS 권장**(연습=실전). 대안 Prisma `scoring_jobs` 테이블 폴링(최단순, AWS 미연습). plan/ADR에서 최종 확정.
- **출력 계약 동결 범위** — fit_level·evidence·recommendations·result JSONB shape 동결을 어디까지 문서화(SPEC §11 / F-001)할지 — plan에서 freeze 지점 명시.
- **신규/마감 diff 시드** — cron 실가동은 M6이므로 M4 E2E는 *수동/로컬 크롤 1회*로 `diff_status`를 시드해 UI가 신규/마감을 렌더. 이 경계를 graduation에 명시.

## 8. 회고 (stabilize 자동 채움)
- 목표 달성도: <정량/정성 1줄>
- scope creep 사례: <있으면 1줄, 없으면 "없음">
- 비목표(charter §5) 위반 사례: <있으면 1줄 — 멀티유저는 ADR-107로 정식 반전했으므로 위반 아님>
- 핵심 학습 3개 이내
