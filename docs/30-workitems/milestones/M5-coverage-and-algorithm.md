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
- **커버리지 확대** — 네카라쿠배(자체 페이지) + 외국계(MS·Google·Moloco·Sendbird 등) + 스타트업 공식 채용. **ATS 어댑터 전략** 우선: Greenhouse/Lever/Workday/Ashby 등 표준 ATS를 *회사별*이 아니라 *ATS별 어댑터*로 묶어 커버리지를 곱셈으로 확장(공수 절감). 티어드(대기업→외국계→스타트업), 소스별 A-1형 게이트 + 커버리지 패널 연동.
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

## 3-1. 실행 wave (task `depends_on` 파생 — repair-plan round 3 재산출, 2026-06-07)
> task `## 9 depends_on`이 SSOT, 본 wave는 파생 스냅샷. 같은 wave 내 병렬 가능. (round3 의존성 변경 — T-067 depends_on에 T-065 추가[둘 다 `feed.controller` 편집 → 순차] 반영.)
- **Wave 1**(병렬): `T-062`(ATS 어댑터 인프라) · `T-064`(job_embeddings 테이블·임베딩 worker) · `T-066`(이력서 도메인 분류기 + resume_domains 계약) — 선행 없음.
- **Wave 2**(병렬): `T-063`(소스 레지스트리·커버리지 패널, `[T-062]`) · `T-065`(후보선별 + coarse/deep 분리 + feed.controller, `[T-064, T-066]`).
- **Wave 3**(병렬): `T-067`(도메인 탭 활성화, `[T-066, T-065]` — T-065의 feed.controller 변경 뒤 순차) · `T-068`(확대 표본 GS-1/GS-2 재검증, `[T-064, T-065, T-066]`).
- **Wave 4**: `T-069`(비용 회귀 + A-3 τ 실측, `[T-065, T-068]`).
>
> 임계 경로: T-064/T-066 → T-065 → T-068 → T-069 (4 wave). **round2 대비 변화**: T-067이 Wave2→Wave3(T-065와 `feed.controller` 동시 편집 충돌 해소). T-068은 T-063(소스 확대) 비의존(큐레이션 수기 fixture 독립).

## 4. 제외되는 기능 (잠정)
- 공개 배포(AWS/Vercel)·알림·cron 실가동 — M6.
- 애그리게이터(잡코리아·직행 등) 크롤링 — 영구 비범위.
- 자소서 자동작성/첨삭·새 페르소나 확장 — Charter §5 / DISCOVERY §13(검증 후 후보).
- 출력 계약(fit_level·evidence·recommendations·result shape) 변경 — M4 동결 유지(계약 변경 필요 시 별도 합의).

## 5. 완료 기준 (graduation checklist, 잠정)
- [ ] 모든 task status: done
- [ ] 통합 validate Pass + schema-contract green(신규 임베딩/정규화 JD 테이블 포함)
- [ ] **확대 커버리지 E2E** — **ATS 어댑터 ≥1종 + 공식 소스 ≥3개**(검증 가능 최소치, plan에서 상향 가능)에서 공고 수집 → 채점 → 피드 렌더, 소스별 커버리지 게이트 통과.
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

## 7. 열린 질문 (잠정)
- 커버리지 1차 티어 목표 회사·ATS 우선순위는? 소스별 유지보수 부채 상한은?
- 임베딩 모델·차원·인덱스(HNSW) 파라미터 + 캐시 키에 임베딩 버전 핀 정책(GS-1 정합).
- 도메인 자동분류를 결정적 규칙 vs LLM vs 임베딩 클러스터링 중 무엇으로?
- 비용 최적화에서 모델 티어링이 GS-1/GS-2를 흔들지 않는 경계(저가 모델 단계 한정).
- A-3 τ 실데이터 평가자 확보(창업자 1인 + 현업 1~2인)와 No-go(τ<0.6) 시 대응.

## 8. 회고 (stabilize 자동 채움)
- 목표 달성도: <정량/정성 1줄>
- scope creep 사례: <있으면 1줄, 없으면 "없음">
- 비목표(charter §5) 위반 사례: <있으면 1줄 — 커버리지 확대는 ADR로 정식 반전 시 위반 아님>
- 핵심 학습 3개 이내
