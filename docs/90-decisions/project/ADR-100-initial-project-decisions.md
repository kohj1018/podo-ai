# ADR-100: 초기 프로젝트 결정 (채용공고 수집 + fit/합격가능성 SaaS)

> scope: project
> area: product

## Status
accepted

## 배경
> evidence label (ADR-022): 본 ADR의 근거는 대부분 **[가설]** — DISCOVERY.md `## 12` 전 항목 미검증(인터뷰·정량 측정 전, repair-discovery 2026-06-04 라운드). 외부실증·관측 증거 없음. 가정이 검증/반증되면 본 ADR을 amend 또는 supersede한다.

`/bootstrap-project`가 [DISCOVERY.md](../../10-charter/DISCOVERY.md)를 charter/architecture로 변환하는 과정에서, 되돌리기 어렵거나 대안이 갈리는 초기 결정 3가지를 기록한다. 일상 구현 결정은 ADR 대상이 아니다(_ADR_GUIDE).

본 제품의 지배적 제약은 **"틀린 점수 > 근거 없는 점수"** thesis(DISCOVERY I-1)이며, 이것이 아래 세 결정의 공통 동인이다. 스택은 미정이라 스택 선택 ADR은 본 ADR에 포함하지 않는다 — `/bootstrap-stack`이 `project/ADR-101-stack-selection.md`로 별도 생성.

## 결정

### D1. 신뢰 게이트(일관성·정확도)를 모든 기능에 우선하는 단일 출시 게이트로 둔다
GS-1(test-retest 재현성)·GS-2(근거 사실성)를 **출시 차단 게이트**로, GS-3(상대 랭킹 타당도)를 출시 후 측정으로 분류한다. 기능 추가보다 게이트 달성이 우선한다.

### D2. 4-layer Clean Architecture를 채택하지 않는다 — 단일 layer + 모듈 단위 의존성 규칙
모듈을 Collector/Scorer/Feed 3개로 논리 분리하되, Domain/UseCase/Adapter/Framework 4계층은 도입하지 않는다. 모듈 간 통신은 *데이터 저장 경유 단방향*(`Collector→Scorer→Feed`)으로 제한하고, Scorer의 **결정론 캐시 경계**와 **JD grounding 경계** 두 규칙만 명시적으로 못 박는다 (ARCHITECTURE_OVERVIEW `## 3-1`).

### D3. 점수 결정론을 캐시 + 버전 핀으로 구조적으로 보증한다
GS-1을 만족하기 위해 스코어링은 (이력서 정규화본·JD 정규화본·모델 ID·프롬프트 버전·파라미터)로 구성한 **명시적·직렬화 가능 캐시 키**를 쓰고, cache miss 시에만 LLM을 temperature=0/seed 고정으로 호출한다. 캐시 키에 시간·랜덤·환경 의존 값을 섞지 않는다.

## 근거

**D1 근거 / 대안:**
- 채택 이유: 창업자가 "흔들리는·틀린 점수"를 *치명 fail*로 명시(DISCOVERY §6 Fail #5, §9). 재현 불가능하면 정확도 논의가 무의미하므로 게이트가 다른 모든 기능의 선행 조건.
- 대안 A — 기능 폭(다채널 커버리지·자소서 첨삭)을 먼저 넓힌다: 기각. 신뢰 미확보 상태의 기능 확장은 "안 도는 앱" 인상을 키워 핵심 약속을 먼저 배신.
- 대안 B — 절대 합격확률 % 캘리브레이션을 게이트로: 기각. 출시 전 실데이터 없음 → 과약속 위험(DISCOVERY §8). 상대 랭킹 + 5단계 밴드로 대체.

**D2 근거 / 대안 (ADR-006 self-check):**
- self-check 결과: 단일 개발자 MVP, 스택 미정 → 4-layer는 정당화되지 않음. ADR-006 우선순위(단순성 1 → Clean Code 2 → Clean Architecture 3)에 따라 단일 layer 채택.
- 그럼에도 모듈을 3개로 *분리*하고 의존성 규칙을 *두 개만* 둔 이유: Scorer의 결정론·grounding 경계는 단순 코드 위생이 아니라 GS-1·GS-2 게이트의 *구조적 전제*다. 이 경계가 무너지면 게이트가 무너지므로, premature abstraction이 아니라 게이트 보호 장치다.
- 대안 A — 전부 단일 모듈(경계 규칙 없음): 기각. Feed가 점수를 즉석 재계산하는 경로가 생기면 캐시 우회로 GS-1이 조용히 깨짐.
- 대안 B — 4-layer Clean Architecture 전면 도입: 기각. MVP 규모 대비 과도(ADR-006). 게이트 보호에 필요한 건 계층 4개가 아니라 경계 규칙 2개.

**D3 근거 / 대안:**
- 채택 이유: LLM은 본질적으로 비결정적이라(A-12) 캐시 없이 GS-1(변동 0)을 만족할 수 없다. 캐시 hit이 결정론을 보장하고, 버전 핀이 "모델/프롬프트가 바뀌면 캐시도 무효"를 명시화.
- 대안 A — temperature=0만으로 결정론 기대: 기각. temperature=0도 제공자/하드웨어/버전에 따라 미세 변동 가능 → 캐시가 유일한 강보증.
- 대안 B — 점수를 매 요청 실시간 계산: 기각. 비결정 + 비용 + 지연. 피드 진입마다 순위가 흔들려 신뢰 즉사.

## 결과
- 모든 후속 plan/feature는 "게이트에 기여하는가"로 우선순위를 매긴다 (F4·F5·F6·F7이 MVP 핵심인 이유).
- 모듈 경계 위반(특히 Feed→Scorer 직접 호출, 캐시 키에 비결정 입력 혼입)은 코드 리뷰·`/validate-workitem` 1순위 점검 항목.
- `/bootstrap-stack`은 스택 선택 시 GS-1(결정론 캐시 저장소)·A-1(크롤링 방식)을 선택 기준으로 삼아야 한다 — 잘못된 스택이 게이트 달성을 어렵게 함.
- 본 ADR의 가정이 검증되면(A-3 τ 측정, A-1 fetch 로그, A-6 인터뷰) 결과에 따라 amend/supersede.

## 후속 작업
- `/bootstrap-stack` — 스택 확정 + `project/ADR-101-stack-selection.md` 생성 (GS-1·A-1 기준 반영).
- A-3/A-1/A-6 선검증 (DISCOVERY §12 다음 행동) — 결과를 DISCOVERY §14 Evidence Log에 적재 후 본 ADR 재평가.
- `/plan-workitem M1` — 게이트 우선순위로 feature/task 분해.

<!-- 관련: DISCOVERY.md §6·§9·§10 / PROJECT_CHARTER.md §4·§6·§9 / ARCHITECTURE_OVERVIEW.md §3-1·§8.
     정책 근거: ADR-006(단순성·아키텍처), ADR-022(evidence label), ADR-035(DISCOVERY=SSOT). -->
