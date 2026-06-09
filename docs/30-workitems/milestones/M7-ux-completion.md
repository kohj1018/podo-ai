# M7-ux-completion

## 0. Status
draft

> **잠정 초안 (메인세션 gap-분석 + resume↔알고리즘 결합 조사 대행, 2026-06-10).** `/plan-workitem M7` 진입 시 feature/task로 분해·확정한다. 스코프 결정(2026-06-10): 알림=이연 · 검색/정렬=이연 · shadcn 리팩토링=이연. 추가 요청 반영: 전 로딩 UI/UX 정비 · 핵심 온보딩 플로우 강화+버그 스윕 · resume 페이지 재설계 · 마이페이지+전역 네비. **resume 재설계 깊이 결정(2026-06-10): 구조화 데이터 모델 미도입 — 폼은 작성 scaffold, 출력은 마크다운 → 기존 단일 blob 흐름(알고리즘·스키마 무변경).**

## 1. 목적
배포된 제품(M6 LIVE, podoai.xyz)의 **핵심 사용자 흐름을 끝까지 매끄럽게 잇고**, persona pain을 직접 더는 화면을 완성한다. 두 축:
1. **핵심 온보딩 플로우(로그인 → resume 입력 → 제출 → 피드 분석결과)를 "물 흐르듯" 만든다** — UX 매끄러움 + 기존/예상 버그 제거 + 전 로딩 지점 처리.
2. **이미 설계(DESIGN.md "Podo Buddy")·API에 준비된 surface를 화면으로 완성**한다 — 마감 섹션·CoarseSection·즐겨찾기/지원기록 뷰·마이페이지.

신규 작업인 **resume 입력 재설계**는 *구조화 데이터 모델 없이* 두 입력 모드(파일 업로드 / 직접작성 폼→마크다운)로만 하므로 스코어링 알고리즘과 닿지 않는다(§2-C·§2-H). 원칙: **알고리즘 결정론(GS-1)·grounding(GS-2)·raw PII 미저장(M3) 불변식을 깨지 않는다.**

> **상위 문서 갱신 범위**: 전 surface가 DESIGN/Charter 명세 범위 내(명세↔구현 gap만 닫음). resume 재설계도 구조화 영속을 안 하므로 `SCORING_PIPELINE_SPEC.md`(Resume 입력 계약) **변경 불필요**.

## 2. 범위

### 2-A. 핵심 시나리오 완성 (코어, UI)
- **마감 임박 전용 섹션** — 피드 "마감 임박 / 오늘의 추천" 섹션 분리(DESIGN §7-3). 현재 GreetingCard "마감 N건" 카운트 + 카드 내부 DeadlineRow만, 전용 섹션 없음. Charter Happy#5 / Fail#4(🔴). ⚠️ **데이터 의존**: `closing_at`을 크롤러가 미수집 → `expiring_count` 항상 0(feed.service.ts:125·137). 섹션 UI는 만들되 데이터 없으면 *정직한 빈/숨김*. closing_at 수집은 크롤러 작업(M7 범위 밖) — §7 결정 필요.
- **CoarseSection 피드 마운트** — `CoarseSection.tsx`(M5 F-021, ADR-108 D3)는 구현·테스트만 있고 import 0(죽은 화면). "아직 깊이 안 본 공고" 별도 섹션·cursor로 노출(fit 점수/밴드 절대 없음 — thesis 보호).
- **최근 7일 미처리 재노출 액션** — `FeedView.tsx:163`이 문구만 출력. 실제 재노출 트리거(버튼/링크)로 전환. Charter Alt#4.
- **즐겨찾기 목록 뷰** — favorite POST·toast만 있고 회수 화면 없음. `GET /api/v1/applications?filter=favorite`(기존) 소비. Charter Alt#2.

### 2-A-1. 피드 정보구조(IA) 결정 — 피로 최소화 (메인세션 판단 2026-06-10)
> 사용자 위임 결정("무엇을 보여주고 무엇을 숨길지를 네가 판단"). 본 절이 피드 IA의 SSOT. 페르소나=공고 과부하 신입 → *오늘의 결정에 필요한 것만* 위계적으로. 형식화는 ADR-110 권장(architect).
- **세로 순서(위→아래)**: ① 커버리지 **compact strip**(1줄 상태 + 탭하면 펼침; 상시 노출 유지=Fail#3, 단 큰 패널이 콘텐츠와 경쟁하지 않게) → ② 직군 탭(조건부) → ③ GreetingCard(오늘 프레임) → ④ **마감 임박 섹션**(긴급 우선, 상위 3~5 캡) → ⑤ **오늘의 추천**(deep 랭킹, 상위 N=5~7 prominent + "더 보기" 커서) → ⑥ **CoarseSection**(최하단, *접힌* 보조 진입 "N개 펼치기", 배지 0).
  - *순서 근거(repair-plan)*: 현 컴포넌트 중첩(`page`[Coverage→Tabs→FeedView] · `FeedView`[Greeting→FeedList])을 따라 GreetingCard 이동 없이 확보. 마감 임박 섹션은 **items를 소유한 `FeedList` 내부**에서 렌더(FeedView는 items 미소유 — T-090 메모).
- **피로 최소화 규칙(횡단)**: (a) **점진적 노출** — 근거(EvidenceBlock)·coarse·커버리지 상세는 기본 접힘, 의도 시 펼침. (b) **오늘의 추천 캡** — 전량 덤프 금지, 상위 N + 더보기. (c) **카드당 primary 액션 1개**(지원하기), 보조(스킵/즐겨찾기)는 시각 약화(DESIGN §9). (d) **정직한 빈/저조 상태 일급** — 가짜 완전성·가짜 점수 금지. (e) **숨길 것**: coarse 유사도 수치·null 메타·비grounding 정보. (f) **정렬=긴급→fit**: 마감 임박 → 추천(랭킹) → coarse.
- 본 IA는 F-028이 구현. DESIGN §7-3(Feed 패턴)의 구체화이며 시각 토큰은 기존 DESIGN 준수.

### 2-B. 핵심 온보딩 플로우 강화 + 버그 스윕
- **골든패스 = 로그인 → /resume 입력 → 제출 → 피드 분석결과**를 끊김 없이 매끄럽게(전환·피드백·이동 타이밍).
- **신규 사용자 진입 = 바로 resume 작성(사용자 결정 2026-06-10)** — 회원가입/최초 로그인 후 이력서가 없으면 피드 인라인 온보딩 대신 **/resume로 직행**. 작성·제출 후 피드로. (현재는 피드에서 `<Onboarding/>` 인라인 — 전환 동선 약함.) → F-031 T-097.
- **기존/예상 버그 제거 스윕**: 업로드 실패·채점 실패·세션 만료·교차출처 쿠키([[web-fetch-credentials-include]])·`localStorage('podo_active_resume_id')` 단일활성 모델의 엣지(이력서 교체/재채점)·`window.location.assign` 강제이동 UX 등 골든패스 위 실제 동작을 점검·수정.
- 결과는 `docs/40-validation/QA_FINDINGS.md` M7 헤더에 누적, 수정은 task로.

### 2-C. resume 입력 재설계 (두 입력 모드 — 사용자 결정 2026-06-10)
> ✅ 결정: **구조화 데이터 모델 미도입.** 폼은 작성 보조 scaffold일 뿐, 출력은 마크다운 → **기존 단일 blob 흐름 그대로**. 알고리즘·스키마 변경 0 (§2-H).
- **현 문제** — `ResumeUpload.tsx`가 단일 textarea + 날 파일 input("너무 구림"). 진입도 주소창뿐(§2-D에서 해결).
- **모드 1 — 파일 업로드** — `.txt`/`.md` 업로드 → **기존 흐름 동일**(마스킹 → `Resume.content` 저장 → 채점). UI만 개선, 동작 무변경.
- **모드 2 — 직접 작성 폼** — 항목별 입력란(**소개 · 경력 · 학력 · 자격증/수상 · 기술스택** + 확장 여지)을 **작성 보조**로 제공. 제출 시 **표준 마크다운 헤딩**(`## 소개`/`## 경력`/`## 학력`/`## 자격증`/`## 기술스택`)으로 조립 → 마크다운 텍스트로 **모드 1과 동일한 기존 `POST /api/v1/resumes` 흐름**(이미 있는 `{text}` 경로 재사용)에 태움. 별도 섹션 테이블·구조화 영속 없음.
- **채점 트리거 = 이력서 신규/수정 시에만(사용자 결정 2026-06-10)** — 이력서가 *새로 추가되거나 수정될 때만* 백엔드 채점 요청. 피드 재진입·단순 탐색은 재채점 안 함(현재도 feed/meta read는 미트리거 — 보존). 편집=새 이력서 버전 생성 → 1회 채점 → 활성 교체. 동일 이력서 중복 채점 방지. → F-030 T-096.
- **편집** — 마이페이지(§2-D)에서 재진입해 다시 작성/교체(단일 활성 이력서 교체).
- **"md로 저장" 구현 해석** — 시스템은 바이너리 미저장(S3 미사용, schema 주석) → 마크다운 **content blob 저장**으로 구현(기존과 동일). 업로드·직접작성 모두 마스킹본만 영속(M3). 빈 항목은 헤딩 생략.
- **예상 변경 범위** — 거의 순수 프론트(`ResumeUpload` 재설계 + 폼→마크다운 조립). API는 `{text}` 경로 그대로(라벨 `format: md` 정도). **schema·worker·프롬프트 무변경.**

### 2-D. 마이페이지 + 전역 네비게이션
- **마이페이지(계정 허브)** — 현재 /resume 진입 경로가 주소창 직접 입력뿐. 로그인 사용자용 허브에서 **이력서 보기/수정(→/resume) · 즐겨찾기 · 지원기록 · 로그아웃** 진입.
- **전역 네비** — `AppHeader`에 메뉴/엔트리 추가(피드↔마이페이지↔resume 편집 왕복). 단일 컬럼·모바일 우선 유지(DESIGN §4).

### 2-E. 부가 편의
- **지원 기록/트래킹 뷰** — persona 핵심 pain("지원 기록 스프레드시트 수기 관리") 대체. `GET /api/v1/applications?filter=applied`(기존) — **순수 프론트**.
- **온보딩 강화** — 첫 진입(이력서 없음) 전환 동선 보강(백엔드 불필요).

### 2-F. 로딩 UI/UX 전면 정비 (cross-cutting)
- **모든 로딩 지점**에 일관된 로딩 UI(skeleton/indeterminate)·낙관적 UI·전환 피드백. DESIGN §7-4 8-상태 + §8-1(Lottie 로딩) 준수, **가짜 점수 절대 미표시**(GS-2). 대상: 피드 meta/리스트/커서, 업로드·마스킹·채점 대기, 세션 체크(AuthGate), 즐겨찾기/지원기록 뷰, 마이페이지.

### 2-G. 모션/폴리시 마감
- **Lottie '도착' 에셋** — PodoLottie에 실제 `.lottie` 연결(현 정적 PNG fallback), reduced-motion 정적 대체·성능 예산(≤50KB·동시≤2) 준수(DESIGN §8-1).
- **Toast 시스템화** — JobCardActions 인라인 toast → 재사용 Toast 패턴(DESIGN §7-2).
- **데스크톱 반응형 마감** — 단일 중앙 컬럼 유지(DESIGN §4) 전제 폭/여백 정돈.

### 2-H. resume ↔ 스코어링 결합 (조사 + 결정, 2026-06-10)
> SSOT=`docs/20-system/SCORING_PIPELINE_SPEC.md`. **결정: 구조화 데이터 모델 미도입 → 결합 0.**
- **현 저장**: `Resume.content` = 마스킹 단일 blob. 워커가 blob에서 evidence 추출 + **결정적 헤딩 파싱**(`evidence-summary.ts`·`parse_resume.py`가 `## Skills/기술스택`·`## 경력/Experience` 헤딩 기준). `compute_fit`·`domain_alignment`·매칭·BT·임베딩은 **resume 구조 무관**.
- **§2-C 직접작성 폼이 표준 헤딩 마크다운을 조립**해 기존 흐름에 태우므로 — 추출이 기존 헤딩 파싱으로 **그대로** 동작. **추출 프롬프트·캐시버전·골든페어·spec 값 전부 무변경.** GS-1/GS-2 보존. (오히려 표준 헤딩이라 추출이 더 깔끔.)
- **(참고, 비범위)** 섹션을 별도 영속하거나 section-aware 추출로 가는 길은 캐시 무효화 + 골든페어 재검증([[m1-port-audit-findings]]) + spec 갱신 유발 → §4 비범위. 측정으로 필요 입증 시 후속.
- **불변식**: 업로드 파일·직접작성 텍스트 모두 **마스킹 후에만 저장**(raw 미저장, M3) · 사용자 입력 원문 보존(재작성 0).

## 3. 포함되는 기능 (F-028 ~ F-033, 잠정)
> feature 초안 — task 분해(T-090+)는 `/plan-workitem M7`에서 확정. 번호는 M6(F-027/T-089) 다음. **F-033(하더닝)은 나머지에 의존해 마지막 wave 권장.**
- **F-028 (feed-section-completion)** — 마감 임박 섹션 + CoarseSection 마운트 + 최근7일 재노출(§2-A 코어).
- **F-029 (account-and-navigation)** — 마이페이지 허브 + 전역 네비 + 즐겨찾기 뷰 + 지원기록 뷰(§2-A C4·§2-D·§2-E 지원기록). resume 편집 진입 포함. **뷰는 API 기존=순수 프론트.**
- **F-030 (resume-input-redesign)** — resume 페이지 재설계: 모드1 파일 업로드(UI 개선) + 모드2 직접 작성 폼(항목 scaffold → 마크다운 조립) + 편집 재진입(§2-C). **구조화 영속/알고리즘 무변경 — 기존 단일 blob 흐름. 거의 순수 프론트.**
- **F-031 (onboarding-and-loading-ux)** — 온보딩 강화 + 전 로딩 지점 로딩 UI/UX 정비(§2-E 온보딩·§2-F).
- **F-032 (motion-and-polish)** — Lottie 도착 에셋 + Toast 시스템화 + 데스크톱 반응형(§2-G).
- **F-033 (core-flow-hardening)** — 골든패스(로그인→resume→제출→피드) 버그 스윕 + UX 매끄러움 통합 점검(§2-B). 다른 feature 통합 후 마지막.

## 3-1. 실행 wave (task `## 9 의존성` 파생 스냅샷)
> task `## 9`가 SSOT, 본 wave는 파생. 같은 wave 내 병렬 가능. ⚠️ **write_set 충돌 클러스터(repair-plan 회수): T-090·T-091·T-092·T-097이 `FeedList.tsx`·`app/page.tsx`·`FeedView.tsx`를 서로 겹쳐 씀**(T-090=FeedList, T-091=page, T-092=FeedView+FeedList, T-097=page+FeedView) → 같은 worktree 동시 implement 비권장(순차). T-099는 lockfile 변경 없음(의존성 기설치) → 단독 wave 불필요.
- **Wave 1**(병렬): `T-090`(마감섹션+피드 IA 순서+커버리지 compact) · `T-093`(마이페이지+네비) · `T-094`(활동 뷰) · `T-095`(resume 2-모드 재설계) · `T-097`(신규→/resume+온보딩) · `T-099`(Lottie) · `T-100`(Toast) · `T-101`(데스크톱 반응형). 선행 없음.
- **Wave 2**(병렬): `T-091`(CoarseSection collapsed 마운트, `[T-090]`) · `T-092`(최근7일 재노출, `[T-090]`) · `T-096`(resume 편집+채점 트리거 lifecycle, `[T-095]`).
- **Wave 3**: `T-098`(전 로딩 지점 UI/UX 정비, `[T-090,T-093,T-094,T-095]` — surface 존재 후).
- **Wave 4**(단독): `T-102`(골든패스 버그 스윕, `[전 task]` — 통합 후 마지막).
> 임계 경로: T-095 → T-096 → T-098 → T-102. F-032(T-099/100/101)는 독립 — 어느 wave든 끼울 수 있음.

## 4. 제외되는 기능
- **구조화 resume 데이터 모델(섹션 별도 영속)·section-aware 추출 프롬프트 재작성·섹션별 임베딩** — 캐시 무효화+골든페어 재검증 유발. 비범위. 직접작성 폼은 마크다운 content blob으로만 영속(§2-C·§2-H).
- **다중 이력서 관리(여러 버전 보관·전환)** — 단일 활성 이력서(`podo_active_resume_id`) 유지. 편집=교체. 다중 관리는 후속.
- **resume 원문 파일(.md/.txt) 바이너리 영속·다운로드** — S3 미사용 아키텍처 유지. content blob만. 파일 보관/내보내기 원하면 별도 결정.
- **알림 기능 전부(인앱·이메일·푸시)** — 사용자 결정 이연. Charter Happy#1·Fail#1(🔴) 완화는 알림 마일스톤.
- **공고 검색·정렬** — feed API 확장 필요, persona 명시 pain 아님 → 후속.
- **shadcn/ui 정착 리팩토링** — 큰 작업, YAGNI상 별도 마일스톤(토큰 `var()`는 이미 준수).
- 새 스코어링 알고리즘/값/가중치 — M5에서 완성. M7은 입력 UX·UI/UX만.
- 새 페르소나/협업 — Charter §5.

## 5. 완료 기준 (graduation checklist, 잠정)
- [ ] 모든 task status: done
- [ ] **핵심 플로우 E2E** — 로그인→resume 입력(파일 업로드 + 직접작성 폼)→제출→피드 분석결과가 끊김 없이 동작 · 마이페이지/네비로 resume 편집 재진입 가능.
- [ ] **알고리즘 불변식 보존** — resume 입력 재설계 후에도 추출/채점 흐름·캐시버전 **무변경**(구조화 영속 없음) · GS-1 재채점 변동 0 · GS-2 hallucinated ≤2% · raw PII 미저장(업로드·직접작성 모두 마스킹본만) · 업로드 파일 verbatim.
- [ ] **thesis 보호 회귀** — CoarseSection fit 점수/밴드 0개(ADR-108) · 가짜 점수 미표시 · 커버리지 상시 노출.
- [ ] **로딩/상태 완전성** — 모든 로딩 지점에 로딩 UI · 신규 컴포넌트 §7-4 8-상태(empty/loading/error) · 모든 모션 reduced-motion 분기(Lottie 정적 대체 포함).
- [ ] **DESIGN.md 준수** — raw hex 0(토큰만) · brand 그라데이션 3곳 fence 유지.
- [ ] **버그 스윕 종결** — 골든패스 위 QA_FINDINGS(M7) P0 0건 · 식별 버그 수정 또는 명시 이연.
- [ ] AC 100% / P0 0.

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§3.1 핵심 시나리오 happy/alt/fail, §8 흐름1·2·3)
- Design: [DESIGN](../../20-system/DESIGN.md) (§7-1 ResumeUpload, §7-2 DeadlineRow·Toast, §7-3 Feed 섹션·CoarseSection·EmptyState, §7-4 8-상태, §8/§8-1 모션·Lottie)
- 스코어링 계약: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§3-2 Resume 모델, §6-1 추출형 evidence, §7-1 resume_extract·skills 헤딩 파싱) — **resume 재설계가 이 계약을 안 건드림을 확인한 근거(§2-H)**
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 소유권·단일 writer, §7-1·§7-4 피드 가상화)
- 선행 마일스톤: [M5-coverage-and-algorithm](M5-coverage-and-algorithm.md) (F-021 CoarseSection) · [M6-deployment](M6-deployment.md)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md)(D3 — CoarseSection fit 점수 금지) · [ADR-105](../../90-decisions/project/ADR-105-pii-masking-policy.md)(PII 마스킹·미영속)

## 7. 열린 질문 (잠정)
- ✅ **[결정 2026-06-10] resume 재설계 = 구조화 데이터 모델 미도입.** 두 입력 모드(파일 업로드 / 직접작성 폼→마크다운 조립)만, 출력은 기존 단일 blob 흐름. 알고리즘·스키마 무변경(§2-C·§2-H).
- **[최우선·데이터갭] 마감 임박 섹션의 `closing_at` 데이터** — 크롤러 미수집(feed.service.ts:125)이라 섹션이 빈 상태로만 동작. 결정 필요: (a) M7에 *스코프드 크롤러 task* 추가(closing_at을 이미 노출하는 어댑터부터) vs (b) UI만 만들고 closing_at 수집은 별도 크롤러 마일스톤 이연. **권장(b)** — M7=UI/UX 경계 보존 + 섹션은 정직한 빈 상태. (a)면 F-028에 크롤러 task 추가.
- **[ADR 권장] 피드 IA(§2-A-1) 결정을 ADR-110으로 형식화?** — 메인세션이 결정했으나 "중요한 UX 결정"이라 architect ADR로 박을지(WORKFLOW §6). 권장: F-028 착수 전 ADR-110 신설.
- 마이페이지·즐겨찾기·지원기록을 **별 라우트**(`/me`·`/favorites`·`/applications`) vs **마이페이지 탭 통합** 중 무엇으로? (F-029 분해 시·단일성/동선 기준)
- 채점 트리거(T-096): 이력서 "수정"의 정의 = 항상 새 resume row 생성(append-only) vs 동일 row 갱신? (현 스키마는 content immutable blob → append-only 권장)
- 직접작성 폼 항목 셋(소개/경력/학력/자격증/기술스택…)의 **고정 목록 vs 사용자 추가 가능** 여부.
- 마감 임박 섹션 노출 임계(D-day ≤ N)와 추천 대비 정렬 우선순위.
- 최근7일 재노출 = 별 섹션 vs EmptyState 인라인 액션.
- Lottie `.lottie` 에셋 조달(제작 vs LottieFiles) — 미조달 시 정적 fallback 유지(차단 아님).
- (이연) 알림 기능은 별도 후속 마일스톤.

## 8. 회고 (stabilize 자동 채움)
- 목표 달성도: <정량/정성 1줄>
- scope creep 사례: <있으면 1줄, 없으면 "없음">
- 비목표(charter §5) 위반 사례: <있으면 1줄>
- 핵심 학습 3개 이내
