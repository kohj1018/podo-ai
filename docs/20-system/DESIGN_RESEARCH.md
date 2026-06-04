# 디자인 리서치 (레퍼런스 + 시안 선택 근거)

> 모드: Reference (DESIGN.md 시각 방향의 근거 — /bootstrap-design R0/R2 산출)
> SSOT는 DESIGN.md(확정 결정). 본 노트는 *왜 그 방향인가*의 근거 보존.
- 조사일: 2026-06-04

## 0. 핵심 제품 진실 → 디자인 함의 (왜 이 방향인가의 전제)

podo ai의 단일 thesis는 **"틀린 점수가 근거 없는 점수보다 치명적이다"**(Charter §1). 즉 제품이 파는 것은 *신뢰·일관성·근거 사실성*이다. 그런데 요청된 UX는 *귀엽고 친근한 마스코트 경험*이다. 이 둘은 반대 방향으로 당긴다.

- **마스코트(포도, "포지션 도착!")** = 따뜻함·친근함·동반자. 매일 아침 공고를 "배달"해 주는 친구.
- **점수·밴드·근거** = 차갑고 정확해야 신뢰됨. 귀여움이 *판단 데이터*를 장식하면 신뢰가 무너진다.

→ 본 디자인의 해소 원칙: **chrome(껍데기)은 따뜻하게, data(판단)는 엄격하게.** 마스코트·카피·형태·모션이 친근함을 전담하고, 점수·합격가능성 밴드·근거 인용은 장식 없이 정확·정직하게. (DESIGN.md §1 원칙 1로 승격)

특수 제약 — **포도 보라색 ↔ AI 슬롭**: 마스코트가 보라→핑크 그라데이션 포도라서, DESIGN.md §9 Don'ts의 "보라/violet gradient 디폴트 금지"(가장 흔한 AI 슬롭 시그니처)와 정면으로 부딪친다. 해소: 포도색은 *과일 brand color*로서 로고·점수 링·매칭 강조 같은 **정해진 brand 순간에만 contained/flat하게** 쓰고, 전면 그라데이션 배경으로 풀지 않는다. (DESIGN.md §1 원칙 2 + §9 Don'ts 보강)

## 레퍼런스   <!-- R0 -->

### Toss (토스) — https://toss.im (Korean fintech, 모델 지식 기반)
- color signature: near-white 베이스 + Toss Blue 단일 accent + 중립 그레이. 색을 절제하고 legibility로 승부.
- typography pairing: Pretendard 계열 휴머니스트-지오메트릭 sans, 숫자 가독성 최상.
- density: 중-저밀도. "한 화면 한 가지" 안내형. 여백 넉넉.
- motion 톤: 매끄럽고 목적 있는 전환, 확정 순간에만 절제된 spring.
- **what to borrow**: 복잡·민감한 데이터(금융)를 *친근하면서 신뢰되게* 보이는 균형. 숫자 가독성, 단일 accent, 위계 우선.
- **what to avoid**: 토스는 다소 미니멀·기업적 — 우리는 마스코트의 온기를 더 넣어야 한다.

### Linear — https://linear.app (모델 지식 기반)
- color signature: 중립 slate(라이트/다크) + 단일 indigo accent. 그림자보다 얇은 border로 구조.
- typography pairing: Inter 계열, 타이트한 tracking, 라벨·상태 시스템 정교.
- density: 고밀도. 리스트·상태가 빽빽하지만 우아하게 정렬.
- motion 톤: 빠르고 또렷, 거의 즉각. 장식 모션 없음.
- **what to borrow**: 정보 밀도를 우아하게 다루는 법, 상태/라벨 시스템(우리의 5단계 합격가능성 밴드 ≈ status), 정밀함이 주는 *신뢰감*.
- **what to avoid**: 개발툴 특유의 차갑고 austere한 톤 + indigo-on-slate 디폴트 — "귀엽고 친근"과 충돌하고 슬롭 존에 가깝다.

### Duolingo — https://duolingo.com (모델 지식 기반)
- color signature: white 베이스 + Feather Green primary + 밝은 보조색. 두껍고 둥근 형태.
- typography pairing: 둥근 sans(din-rounded 계열), 굵은 weight.
- density: 저밀도, 큰 타깃, 놀이 같은 spacing.
- motion 톤: 통통 튀고 축하하는, 캐릭터 주도.
- **what to borrow**: *마스코트를 제품 경험의 중심 동반자/가이드로* 쓰는 법(Duo ↔ podo). 격려하는 카피, 매칭 순간의 작은 축하, 둥근 친근 형태.
- **what to avoid**: 과도한 게이미피케이션·높은 채도·만화풍. 점수를 게임처럼 보이게 하면 *근거 사실성(GS-2)* 신뢰가 무너진다. 통통 모션 남용 금지.

## 안티-레퍼런스   <!-- R0 -->
- **"generic violet-gradient SaaS hero 같지 말 것"** — 가장 흔한 AI 슬롭 시그니처. 마스코트가 보라 포도라서 *가장 빠지기 쉬운 함정*. 포도색은 brand 순간에만 contained, 전면 그라데이션 배경 금지.
- **"over-gamified·유치한 마스코트 앱 같지 말 것"** — 귀여움이 유치함으로 넘어가 *판단 데이터의 신뢰도*를 깎으면 제품 thesis 붕괴. confetti 남발·elastic bounce·만화 채도 회피. 귀엽되 *믿음직*하게.
- (보조) **"잡코리아/사람인식 고밀도 파란 코퍼릿 리스트 같지 말 것"** — 차별 없는 클러터·낮은 신뢰. 우리는 랭킹·근거 우선의 *차분한* 피드.

## grounding 출처   <!-- R0 -->
- 사용자 제공 마스코트 이미지 [`assets/podo-ai-agent-character.png`](assets/podo-ai-agent-character.png) (1차 grounding — 색·형태·표정 톤의 직접 출처). 웹앱 스캐폴딩(M1) 시 프로덕션 사본은 `podo/apps/web/public/`로 복제.
- 레퍼런스 3종(Toss/Linear/Duolingo)은 디자인 MCP·URL 미연결 → **모델 지식 기반**. (필요 시 사용자 스크린샷/URL로 보강 가능 — ADR-048 기본 의존 추가 X.)

## 시안 옵션   <!-- R2 — concept별 방향·근거 (선택 후 채움) -->
- **concept A — "포근한 피드"(균형형)**: 따뜻한 off-white + 포도 보라 flat primary + 핑크 blush 보조. 중간 밀도, 둥근 친근 카드, 5단계 밴드는 또렷한 segmented meter, fit 점수는 링 배지(높은 매칭에 podo가 빼꼼). 근거: Toss 명료함 × Duolingo 온기, 마스코트 present하되 비지배. — warmth↔rigor 축의 *중앙*.
- **concept B — "또렷한 신뢰"(밀도·신뢰 우선)**: 차분한 중립(paper white + warm gray) + 포도 보라 단일 결정적 accent를 절제. 정렬된 구조·고밀도, 숫자 fit 점수 + status-chip 밴드(Linear lineage), 근거를 항상 한 탭 거리에. 마스코트는 작은 아바타 + 마이크로 모먼트로 절제. 근거: 제품 thesis(신뢰 게이트)를 시각적으로 정면 지원 — cuteness↔credibility 긴장을 *credibility 쪽*으로. — warmth↔rigor 축의 *rigor 끝*.
- **concept C — "포도 친구"(마스코트 우선·warm gradient brand)**: 포도 보라→핑크 그라데이션을 *controlled brand signature*로만(로고·fit 점수 링·얇은 인사 strip — 전면 배경 X) + 크림 + 핑크 blush 필드. podo를 더 큰 가이드/동반자로(말풍선 인사, 매칭 tier별 반응), 넉넉한 여백, 둥근 display heading. 가장 "귀엽고 친근"하되 그라데이션을 brand 순간에 *울타리* 치고 데이터는 엄격 유지. — warmth↔rigor 축의 *warmth 끝*.

## 최종 선택   <!-- R2 -->
- 선택: **concept C — "포도 친구"(Podo Buddy) 단독** (사용자 선택 2026-06-04. A·B 탈락 — "다시 보니 C가 낫다, 전부 C로").
- 선택 정의 (C 전체 채택):
  - 베이스: 크림/핑크 blush 필드(#FFFBF6 / #FFF7FB), 흰 surface + 핑크-tinted border(#F6E4EC).
  - 포도 그라데이션(`135deg, #8B3DD4→#C950C0→#F5709F`)을 **brand 순간 3곳에만 fence**: ① 로고 "ai" 워드마크, ② fit 점수 링 arc, ③ 인사 strip 상단 5px accent. 전면/카드 배경 그라데이션 금지(anti-slop 울타리).
  - 마스코트 우선: podo 인사 68px + 말풍선, 고적합 카드 "podo 강추!" stamp, 섹션 "podo 픽 🍇" peek, 보류 카드 56px podo로 정직한 보류 메시지 전달.
  - 저밀도·여백 큰 둥근 카드(radius 24px), Pretendard 900 heading.
- 근거: 가장 귀엽고 친근한 동반자 톤(요청 UX 핵심)이면서, 그라데이션을 brand 3곳으로 울타리 치고 점수·밴드·근거는 장식 없이 엄격 유지 → 원칙 1("따뜻한 chrome, 엄격한 data")·원칙 2(포도 보라는 brand 신호로만)와 정합.
