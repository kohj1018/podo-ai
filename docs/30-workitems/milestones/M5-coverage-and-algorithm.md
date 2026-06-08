# M5-coverage-and-algorithm

## 0. Status
draft

> **잠정 초안.** M4 졸업 후 `/plan-workitem M5` 진입 전에 갱신·확정한다. 본 문서는 방향·경계를 박는 스냅샷이며, 특히 *알고리즘 핵심 변경은 사용자와 논의 후 진행*(사용자 판단 2026-06-07).

## 1. 목적
M4가 "핵심 워크플로우가 도는 멀티유저 MVP"를 완성하면, M5는 **(1) 채용공고 커버리지를 토스·당근 2곳 → 다수 IT기업 공식 채용으로 확대**하고, **(2) 정말 많아진 JD와 다종 이력서 위에서 fit 적합도가 여전히 정확·일관·저비용으로 작동하도록 알고리즘을 보강**한다. 핵심 thesis(GS-1 일관성·GS-2 grounding)는 *확대된 입력 위에서도* 보존되어야 하며, M3 코드 감사로 드러난 구조적 한계(벡터 사전필터 부재·세트 상대적 비증분 채점·업로드 이력서 도메인 하드코딩)가 "많은 JD"에서 비용·정확도로 직결된다.

> **M5의 핵심 = "새 알고리즘 추가"가 아니라 *비용 구조 전환* (사용자 판단 2026-06-07).** 목표는 채점 비용을 **N개 전체 깊은 분석 → 후보 K개 깊은 분석**으로 바꾸는 것. 모든 구현 판단은 이 목표에 종속한다(추측성 추상화·계획에 없는 헬퍼 금지 — ADR-006). 두 가드레일: ① **coarse signal(임베딩 유사도·후보선별 점수)과 deep fit을 UI·DB에서 명확히 분리** — fit_level은 matching/verify/compute_fit까지 통과한 deep 공고에만 부여, 유사도는 "적합도 5단계"로 절대 표시 안 함. ② **후보선별은 recall 우선** — 벡터+도메인/role_family+스킬/키워드 *합집합*. 출력 계약(fit_level·evidence·recommendations·result shape)은 M4 동결.

> **크롤링 원칙:** **각 회사 공식 채용 페이지에서만** 수집한다. 잡코리아·직행·원티드 같은 애그리게이터 크롤링은 하지 않는다(Charter §5 ToS 입장·A-1 방식 유지). (사용자 판단 2026-06-07.)

> **Charter §5 "다채널 풀커버리지 비목표" 범위 갱신 (별도 ADR 불필요).** Charter §5는 "다채널 풀커버리지(7개+ 전부)"를 *비목표*(F2 커버리지 명시로 대체)로 박았다. M5는 그 *숫자 상한*만 올린다 — **Charter §5 scope-note 반영이 M5 task 생성 *전* 필수 선행(blocking gate)**: 상위(Charter) 승인 없이 하위 task 착수 금지(AGENTS.md). scope-note = 공식 페이지 한정·티어드·소스별 게이트. *Charter 편집은 repair-plan 범위 밖 → 메인세션 별도 처리.* 별도 ADR은 불필요: 검증된 A-1 크롤링 재사용·가역적·"공식만"은 기존 ToS 입장의 연장이라 비가역 트레이드오프 없음(사용자 판단 2026-06-07). 각 신규 소스는 A-1형 검증(차단/구조변경/캡차) 게이트를 통과해야 커버리지 패널에 "수집 중"으로 승격.

## 2. 범위 (잠정)
- **커버리지 확대 (target universe ↔ graduation line 분리 — 사용자 결정 2026-06-08)** — *Target universe*(웹검색 실측 픽스, ~85개사 — 회사 목록은 per-tier task T-072~076에 명시): **Tier1 네카라쿠배+계열사(최우선) / Tier2 외국계 한국 / Tier3 Series C+·유니콘 스타트업 / Tier4 국내 대기업+IT계열사 / Tier5 금융권+IT자회사** — 자체 공식사이트 한정(애그리게이터 영구 제외). **discovery 선행(T-070)** → 어댑터 2 family: (A) ATS(실측 우선순위 **그리팅·Workday > Lever·Ashby**, Greenhouse=T-062 기반, 한국 위탁SaaS recruiter.co.kr/incruit/careerlink 후보) + (B) 자체사이트 bespoke(`BaseCustomAdapter`, Tier1 우선). **location 1급화**(외국계 한국만). **⚠️ Tier4/5 대부분 login-gated** → 목록 공개분만 수집, 로그인 목록은 `login-required`로 투명 노출. *"최대한 많이"는 universe, 졸업선은 §5.*
- **알고리즘/데이터 보강 (코드 감사 직결 — 출력 계약 §M4 동결 안에서)**:
  - **벡터 사전필터 실구현 (핵심 비용 레버)** — pgvector(현재 extension만 설치, 컬럼·코드 0). **`job_embeddings`(vector) 테이블에 JD 임베딩 1회 영속·재사용** → resume↔JD 유사도 + 도메인 + 스킬 *합집합*으로 후보 K개 선별 → 매칭·검증·랭킹을 K개에만. 현재 listwise는 *공고 전체를 한 프롬프트*에 넣어 JD 수에 비용 폭증 → N→K로 전환. **구조화 JD(requirements)는 이미 디스크 캐시(JD-only 키)로 재사용되므로 DB 테이블로 영속하지 않는다**(비용 레버 아님 — YAGNI).
  - **증분/세트 분리 채점** — 공고 1개 추가 시 그 JD만 deep(결정적 fit_level), LLM listwise·pairwise는 top 후보 변동 시에만(`job_set_hash` 전체 재계산 회피).
  - **업로드 이력서 도메인 자동분류** — `persistence.load_resume`이 모든 업로드 이력서를 `primary=frontend/secondary=backend`로 하드코딩 → 백엔드·데이터 이력서 오정렬. 자동 도메인 분류로 교체(직군 분리 탭 M4 보류분과 연동).
  - **비용↔정확도 최적화** — 저렴 모델로 단계 분리(예: 추출은 저가, 검증은 고가)·배치·프롬프트 압축·캐시 적중률 향상. LLM 비용을 최대한 아끼며 정확도 유지.
- **검증** — 다종 이력서 × 다종 JD에서 fit 품질 측정 + GS-1/GS-2를 *확대 입력*에서 재실측(JD 종류 폭증 = hallucination 표면↑) + A-3 τ 실데이터 1회(하니스 `ai/eval/a3_tau.py` 기보유, M1 미실행분).

## 3. 포함되는 기능 (F-020 ~ F-023, 잠정)
> feature 초안 작성됨(메인세션 plan 대행, task 분해 X). **알고리즘 핵심(F-021·F-022)은 사용자 논의 후 task화**(사용자 판단).
- **F-020 (source-coverage-expansion)** — 공식 채용 페이지 ATS 어댑터 전략 + 회사별 어댑터 + 소스별 A-1형 게이트 + 커버리지 패널. Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요).
- **F-021 (jd-vectorization-and-cost)** — 정규화 JD 영속 + pgvector 후보 사전필터 + 증분 채점 + 모델 티어링/배치(비용↓). 출력계약 동결 안.
- **F-022 (resume-domain-classification)** — 업로드 이력서 도메인 자동분류(하드코딩 교체) + 직군 분리 탭 활성.
- **F-023 (expanded-fit-validation)** — 확대 입력 GS-1/GS-2 재측정 + 비용 전후 회귀 + A-3 τ 실데이터 1회.

## 3-1. 실행 wave (task `depends_on` 파생 — 커버리지 확대 반영 재산출, 2026-06-08)
> task `## 9 depends_on`이 SSOT, 본 wave는 파생 스냅샷. **두 트랙이 대체로 독립 병렬**: (A) 커버리지, (B) 알고리즘.
>
> **(A) 커버리지 트랙**
> - **Wave A1**(병렬): `T-062`(ATS 인프라 + location 1급) · `T-070`(discovery → registry_seed) — 선행 없음.
> - **Wave A2**(병렬): `T-071`(ATS family 그리팅·Workday·Lever·Ashby, `[T-062, T-070]`) · `T-072`(Tier1 커스텀+BaseCustomAdapter, `[T-062, T-070]`).
> - **Wave A3**(병렬): `T-073`(Tier2 외국계)·`T-074`(Tier3 스타트업)·`T-075`(Tier4 대기업) — `[T-070, T-071, T-072]`(T-075=`[T-070, T-072]`).
> - **Wave A4**: `T-076`(Tier5 금융권, `[T-070, T-072, T-075]` — recruiter.co.kr 어댑터 재사용).
> - **Wave A5**: `T-063`(레지스트리 등록·상태·커버리지 패널, `[T-070~072, T-073~076]`).
>
> **(B) 알고리즘 트랙**
> - **Wave B1**(병렬): `T-064`(job/resume embeddings) · `T-066`(도메인 분류기 + resume_domains).
> - **Wave B2**: `T-065`(후보선별 coarse/deep + feed.controller, `[T-064, T-066]`).
> - **Wave B3**(병렬): `T-067`(도메인 탭, `[T-066, T-065]`) · `T-068`(확대표본 GS-1/2 재검증, `[T-064, T-065, T-066]`).
> - **Wave B4**: `T-069`(비용회귀 + A-3 τ, `[T-065, T-068]`).
>
> 임계 경로: 커버리지 `T-070 → T-071/T-072 → T-073/074/075 → T-076 → T-063` · 알고리즘 `T-064·T-066 → T-065 → T-068 → T-069`. 두 트랙은 대체로 독립(커버리지=입력 JD 확대, 알고리즘=처리). T-068은 큐레이션 fixture라 커버리지 비의존. 진행 순서(사용자): **T-070 discovery → ATS family(T-071) → Tier1 커스텀(T-072) → Tier2~5(T-073~076) → 레지스트리/패널(T-063) → 알고리즘 연결.**
> **공유 표면 주의**: `ai/tests/test_schema_contract.py`·`prisma/migrations/`는 다수 task가 추가(폴더 분리라 충돌 0, schema-contract.py만 공유 → 순차 편집). `depends_on` 불변.

## 4. 제외되는 기능 (잠정)
- 공개 배포(AWS/Vercel)·알림·cron 실가동 — M6.
- 애그리게이터(잡코리아·직행 등) 크롤링 — 영구 비범위.
- 자소서 자동작성/첨삭·새 페르소나 확장 — Charter §5 / DISCOVERY §13(검증 후 후보).
- 출력 계약(fit_level·evidence·recommendations·result shape) 변경 — M4 동결 유지(계약 변경 필요 시 별도 합의).

## 5. 완료 기준 (graduation checklist, 잠정)
- [ ] 모든 task status: done
- [ ] 통합 validate Pass + schema-contract green(신규 임베딩/정규화 JD 테이블 포함)
- [ ] **커버리지 graduation line** (target universe(~85개사) ≠ 졸업선 — "최대한 많이"는 universe이지 졸업 조건 아님):
  - [ ] T-070 discovery가 *전 5-tier target*의 공식 URL·method·location·**view-vs-apply 로그인**·status를 레지스트리에 기록(미수집도 상태로).
  - [ ] **수집 가능분 최대한 수집**: ATS(그리팅·Workday·Greenhouse·Lever·Ashby) ats-ready + Tier2 외국계(location=KR) + Tier3 스타트업 + **Tier1 본사 커스텀** + Tier4/5 중 *목록 공개* 소스.
  - [ ] Tier4/5 login-gated(목록 로그인)·no-korea·unsupported는 status로 **커버리지 패널에 투명 노출**(거짓 완전성 0, Fail #3) — 미수집도 정직하게.
  - [ ] 수집 → 채점 → 피드 렌더 E2E(무키, fixture 임베딩 seed).
- [ ] **게이트 보존(확대 입력)** — GS-1 캐시 hit 변동 0 + GS-2 hallucinated requirement ≤2%가 *확대된 JD/이력서 표본*에서 유지.
- [ ] **비용 측정** — 보강 전/후 채점 LLM 비용(토큰/호출 수) 비교로 절감 실증.
- [ ] AC 100% / P0 0.
- [ ] (선택) A-3 τ 실데이터 1회 판정 기록(Charter §6 / DISCOVERY §12 A-3).

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§5 다채널 비목표 — ADR로 반전, §6 GS-1/2/3)
- Discovery (SSOT): [DISCOVERY](../../10-charter/DISCOVERY.md) (§12 A-3·A-7·A-9, §11 열린 질문)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 pgvector DDL=Prisma/DML=Python, §6 외부 연동, §7-3 워커)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- 선행 마일스톤: [M4-product-mvp](M4-product-mvp.md)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md)(스코어링 비용 구조 — 벡터+하이브리드 후보 사전필터, **작성됨**). *커버리지 확대는 별도 ADR 불필요 — Charter §5 scope-note(M5 진입 시).*

## 7. 열린 질문 — 결정 확정 (2026-06-08, 사용자 승인)
- ✅ **임베딩**: `text-embedding-3-small`/1536(공식문서 검증), `OPENAI_API_KEY` 재사용, **JD·resume 양쪽 영속+재사용**(OpenAI 임베딩 호출 비결정 실측 → GS-1은 저장 벡터 재사용으로 보장), 무키 E2E는 fixture 임베딩 seed. `model_id`/`created_at` 동봉(모델 update 감지). (T-064)
- ✅ **도메인 분류**: 결정적 규칙(LLM·클러스터링 아님) + **기존 `ROLE_FAMILY_TO_DOMAINS` 토큰 재사용**(새 어휘 X). SKILL_DOMAIN_RULES 확정(다의어·kotlin 제외). (T-066)
- ✅ **후보선별**: 하이브리드 합집합(벡터 ∪ 도메인 ∪ **raw_text 스킬키워드** — `tech_stack` 컬럼 없음 확정), **K_v=50 / K_max=80**(F-023 후 30/50 검토). (T-065)
- ✅ **구조화 JD JSONB**: M5 미신설(raw_text로 시작) — 디스크 캐시는 SSOT로 취급 안 함, recall 부족 시 F-023 후 재검토. (ADR-108 D1)
- ✅ **커버리지 1차 티어**: ATS 어댑터 우선순위 **그리팅·Workday > Lever·Ashby**(Greenhouse=T-062, T-070 실측 반영). 5-tier universe(~85개사) — 회사 목록은 Tier별 task T-072~076. (T-062/T-063)
- ✅ **A-3 τ**: 우선 **내부 golden-pair/persona eval 확장**으로 진행, 사람 평가자는 후속 검증 게이트(τ<0.6 No-go 대응은 그 시점). (T-068/T-069)
- ✅ **상태채널(M4 잔여 REV-M4-003/010)**: M5 비범위 — **M6 DLQ/운영안정화와 묶음**. M5는 비용구조·후보선별 정확도 집중.
- ⏸ **모델 티어링**(저가/고가 분리): F-023 GS-2(근거 사실성 ≤2%) 측정 후 적용(ADR-108 D7). HNSW `m`/`ef_construction`은 pgvector 기본값 시작.

## 8. 회고 (stabilize 자동 채움)
> `/stabilize-milestone M5` (2026-06-08). 졸업 가능 **NO** — task 15/15 done·validate exit 0(Py 236/TS 72)·AC 51/51·FAC 20/20이나 **P0 2건**(코어 비용레버 미배선 + 무키 E2E red). 상세 [QA_FINDINGS ## M5](../../40-validation/QA_FINDINGS.md) · [IMPROVEMENT_GUIDE §0~§4 M5](../../40-validation/IMPROVEMENT_GUIDE.md).
> **↳ 갱신 2026-06-08 (repair)**: P0 2건 *해소* — `run_full_scoring`·`embed_new_jobs`·domain 탭·coverage 배선 + 무키 import 안전화(커밋 `2821a79`) + 웜캐시 재생성 → **`pnpm e2e` fresh-volume exit 0** 실증. 졸업 *재grade*는 `/stabilize-milestone M5` 재실행으로 확정(본 NO 판정은 최초 stabilize 기록 보존).
- 목표 달성도: **부분(≈50%)** — 커버리지 트랙(5-tier 어댑터·discovery·레지스트리·패널)은 구현·테스트 완결, 알고리즘 모듈(임베딩·prefilter·coarse·도메인분류·확대검증 eval)도 단위 green. **그러나 M5 *핵심*인 "비용 구조 전환 N→K"가 서비스 경로에 미배선**(`run_full_scoring`·`embed_new_jobs`가 진입점에서 0회 호출 — worker는 여전히 N개 전체 `run_scoring`) → 비용 절감·coarse 섹션이 프로덕션 미실현. 도메인분류기(T-066)만 run_scoring에 배선됨.
- scope creep 사례: 없음 — 변경은 AC로 역추적 가능. 커버리지 확대는 Charter §5 scope-note(공식페이지·티어드·게이트)와 ADR-108 범위 안.
- 비목표(charter §5) 위반 사례: 없음 — 커버리지 확대는 *공식 채용 페이지 한정* + Charter §5 scope-note 기록(M5-repair-1 적용, 별도 ADR 불필요는 사용자 판단)으로 *정식 반전*. 애그리게이터 영구 비범위 준수.
- 핵심 학습:
  1. **모듈 green ≠ 서비스 실현.** 함수 단위 AC(T-065 AC-2가 `run_full_scoring`를 직접 호출)는 "서비스가 그 함수를 쓰는가"를 검증 못 한다(oracle gap). milestone 분해에 *running 진입점 배선 task + 그 경로를 타는 E2E AC*가 명시적으로 필요(T-065 §4-1 write_set에 `__main__.py` 부재가 근인).
  2. **알고리즘 변경이 LLM 캐시 키를 바꾸면 웜캐시 재생성이 동반돼야 무키 E2E가 산다** — T-066 도메인분류 주입이 listwise 캐시 키를 바꿨으나 웜캐시 미재생성 → 무키 크래시. M2/M3/M5 3회째 E2E·웜캐시 동기 누락(patterned drift).
  3. **"비차단 arch-debt"의 이연 비용은 상승한다** — M4에서 비차단으로 둔 status 큐 consumer 부재가 M5 E2E에서 fail-fast를 막아 차단 신호로 전이.
