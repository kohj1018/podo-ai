# 디자인 (UI)

> 모드: Reference + How-to (UI 시각 결정의 SSOT)

## 0. Status
draft

<!-- 본 문서는 UI 프로젝트의 시각 결정 SSOT.
     baseline에는 placeholder로 존재한다 (presence: conditional, STRUCTURE.md 참조).
     - UI 프로젝트: /bootstrap-design이 R0~R6 라운드로 본 파일을 채운다 (ADR-049).
     - 비-UI 프로젝트(API 서버 / CLI 도구 등): fork 직후 본 파일을 삭제한다. -->

## 1. Overview

podo ai(포도 ai)의 Feed UI 시각 SSOT. 포도(="포지션 도착!") 마스코트가 매일 아침 *적합한 자리를 골라 배달해 주는 동반자*로 느껴지는 귀엽고 친근한 경험을 목표로 한다. 동시에 제품 thesis("틀린 점수가 근거 없는 점수보다 치명적")를 시각에서 배신하지 않는다.

근거·레퍼런스·시안 선택 이유: [디자인 리서치](DESIGN_RESEARCH.md).
- **what to borrow**: Toss(복잡한 데이터를 친근+신뢰되게, 숫자 가독성·단일 accent) · Duolingo(마스코트를 제품 동반자로) · Linear(상태/라벨 시스템의 정밀함).
- **what to avoid**: generic violet-gradient SaaS 슬롭(마스코트가 보라라 가장 위험) · over-gamified 유치함(점수 신뢰 훼손) · 잡코리아식 고밀도 코퍼릿 클러터.
- **선택 concept: C — "포도 친구"(Podo Buddy)** (A·B 탈락). 크림+핑크 blush 베이스, 포도 그라데이션을 brand 3곳에만 fence, 마스코트 우선.

### 디자인 원칙 (5)
1. **따뜻한 chrome, 엄격한 data** — 마스코트·카피·형태·모션이 친근함을 전담한다. 점수·적합도·근거는 장식 없이 정확·정직하게. 귀여움이 *판단 데이터*를 장식하지 않는다.
2. **포도 보라는 brand 신호로만** — 포도 그라데이션은 로고·fit 링·인사 strip 등 *정해진 brand 순간*에만 contained. 전면/카드 배경 그라데이션 금지(슬롭 차단).
3. **랭킹과 근거를 한 시선에** — fit 점수 · 적합도 5단계 · 근거를 카드 한 장에서 즉시 위계적으로. 스캔 → 펼침 → 결정.
4. **정직한 보류/빈 상태를 일급으로** — 보류·미수집·신규없음을 깨진 화면이 아니라 podo가 안내하는 *설계된 상태*로. 커버리지 패널 상시 노출("거짓 완전성" 차단, Fail #3).
5. **모션은 '도착'의 의미만** — 새 공고 도착·매칭 확정 같은 의미 전달에만. bounce/elastic/confetti 장식 금지(귀엽되 유치하지 않게).

<a id="design-2-colors"></a>
## 2. Colors
> 3-tier 토큰(W3C DTCG): primitive → semantic → component. 구현은 raw hex 직접 사용 금지, 토큰만 참조(§9). Tailwind/shadcn CSS 변수로 매핑.

### 2-1. Primitive (raw)
```yaml
# grape (brand) — 포도 보라→핑크 과일색
grape-700: "#6F2BC0"
grape-600: "#8B3DD4"     # brand base
grape-500: "#A45BE0"
grape-100: "#F1E6FB"
grape-050: "#F8F2FD"
grape-magenta: "#C950C0" # 그라데이션 midstop 전용
# pink (blush 보조 — 마스코트 볼터치 echo)
pink-600: "#C43B6B"      # 핑크 텍스트 (AA on white)
pink-500: "#F5709F"
pink-400: "#FAA9C5"
pink-100: "#FCE3EC"
pink-050: "#FFF7FB"
# leaf (마스코트 잎 — '살아있음/수집중' 절제된 brand nod)
leaf-500: "#74B82C"
# warm neutrals (크림 베이스)
paper:         "#FFFBF6"
paper-2:       "#FFF7FB"
surface:       "#FFFFFF"
surface-blush: "#FEF0F5"
line:          "#F6E4EC"
line-strong:   "#EDD0DC"
ink:   "#2B2433"         # primary text
muted: "#6C6475"         # secondary text (≥4.5:1 on white)
faint: "#8A8090"         # 장식/큰 라벨 전용 (<4.5 — body 금지)
# 합격가능성 5-band — FILL (meter·dot·chip bg; 항상 텍스트 라벨 동반)
band-1-fill: "#D6566A"   # 매우 낮음
band-2-fill: "#E0913F"   # 낮음
band-3-fill: "#C9B26B"   # 보통
band-4-fill: "#54A98C"   # 높음
band-5-fill: "#2E9D6B"   # 매우 높음
# 합격가능성 5-band — INK (텍스트로 쓸 때, AA ≥4.5:1 on white)
band-1-ink: "#C32F41"
band-2-ink: "#8A5A12"
band-3-ink: "#7E6A1C"
band-4-ink: "#2C7D5D"
band-5-ink: "#1C7A49"
```

### 2-2. Semantic
```yaml
color.bg.canvas:        grape? -> paper          # 페이지 배경(크림)
color.bg.canvas-alt:    paper-2                  # blush 변주
color.bg.surface:       surface                  # 카드·패널
color.bg.surface-pending: paper-2                # 보류/빈 상태 surface
color.bg.blush:         surface-blush            # 따뜻한 강조 컨테이너(마감 임박 wrap)
color.border.default:   line
color.border.strong:    line-strong
color.text.primary:     ink
color.text.secondary:   muted
color.text.faint:       faint                    # 장식 전용
color.text.on-accent:   "#FFFFFF"
color.accent:           grape-600                # primary brand action
color.accent-strong:    grape-700                # hover/pressed
color.accent-soft:      grape-100                # accent bg tint
color.pink:             pink-600                 # 따뜻한 텍스트 accent(D-day·마감)
color.pink-soft:        pink-100
color.success:          band-5-fill              # = leaf 계열 의미
color.warning:          band-2-fill
color.danger:           band-1-fill
color.info:             grape-600
color.passband.{1..5}.fill / .ink                # 합격가능성 신호(위 band-*)
color.coverage.on-bg:     "#EAF6F0"             # coverage 패널 켜짐 배경(globals.css --coverage-on-bg)
color.coverage.on-border: "#CDEBDC"             # coverage 패널 켜짐 테두리(globals.css --coverage-on-border)
```

### 2-3. Component
```yaml
button.primary.bg:        color.accent
button.primary.bg-hover:  color.accent-strong
button.primary.text:      color.text.on-accent
button.ghost.bg:          color.bg.surface
button.ghost.border:      color.border.strong
button.ghost.text:        color.text.secondary
tab.active.bg:            color.text.primary      # ink 탭(중립 강조 — 색 절약)
tab.active.text:          color.text.on-accent
tab.idle.bg:              color.bg.surface
tab.idle.text:            color.text.secondary
card.bg:                  color.bg.surface
card.border:              color.border.default
card.shadow:              elevation.card
fitring.track:            grape-050
fitring.arc:              brand.gradient          # ← FENCED brand spot
chip.source.bg:           paper
chip.num.new:             { bg: grape-050, text: grape-700 }
chip.num.due:             { bg: pink-100,  text: pink-600 }
podostamp:                { bg: pink-100,  text: pink-600 }
coverage.on:              { bg: "#EAF6F0", text: band-5-ink, border: "#CDEBDC" }
coverage.off:             { bg: paper,     text: faint }
```

### 2-4. Brand gradient (FENCED)
```yaml
brand.gradient: "linear-gradient(135deg, #8B3DD4 0%, #C950C0 50%, #F5709F 100%)"
# FENCED — 정확히 3곳에서만: (1) 로고 "ai" 워드마크, (2) fit 점수 링 arc, (3) 인사 strip 상단 5px accent.
# 그 외 어디에도(전면 배경·카드·heading·버튼) 금지. 위반 = #1 AI 슬롭 시그니처(§9, 원칙 2).
```

### 2-5. 접근성 (대비)
- 본문/정보성 텍스트는 `ink`(≈13:1) 또는 `muted`(≈5:1)만. `faint`(<4.5)는 장식·큰 라벨 전용.
- band 색을 *텍스트*로 쓸 땐 `band-*-ink`(AA), *fill*(meter/dot) 색을 작은 텍스트로 쓰지 않는다.
- 핑크 텍스트는 `pink-600`(#C43B6B, AA)만. `pink-400/500`은 fill 전용.
- 의미를 색만으로 전달 금지 — 밴드·매핑은 항상 텍스트 라벨(+✓/△ 아이콘) 동반(§9).

## 3. Typography
> Pretendard 단일 family(한국어 우선·숫자 가독성). Inter/Roboto/Arial 디폴트 회피(§9).

```yaml
font.family.base: 'Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
font.family.mono: '"JetBrains Mono", "D2Coding", ui-monospace, monospace'  # 코드·식별자·수치 전용(장식 금지)

# size scale (modular ~1.2, base 14)
font.size.xs:   12px   # meta·footnote·chip
font.size.sm:   13px   # 보조 본문·근거·커버리지
font.size.base: 14px   # 본문·탭·버튼·밴드 라벨
font.size.lg:   16px   # 카드 직무명(role)·보류 role·섹션 heading
font.size.xl:   18px   # 인사 headline
font.size.2xl:  21px   # fit 점수 숫자
font.size.3xl:  26px   # 큰 빈/온보딩 hero (예약)
# 로고 워드마크: 20px / black

# weight pair
font.weight.regular:   400
font.weight.medium:    500
font.weight.semibold:  600
font.weight.bold:      700
font.weight.extrabold: 800
font.weight.black:     900   # heading·role·fit 숫자·brand (친근 display feel)

# line-height
line.tight:   1.2   # heading·fit 숫자
line.snug:    1.4
line.normal:  1.5   # 본문
line.relaxed: 1.6   # 보류 메시지

# letter-spacing
tracking.tight: -0.03em  # heading·role·brand
tracking.snug:  -0.01em
tracking.normal: 0
```
- 위계는 size+weight+color 중 2축 이상으로(§9). heading은 black(900) + tracking.tight로 둥근 친근 display 톤.

## 4. Layout
> 4 단위 base spacing. 모바일-우선 단일 컬럼(앱 피드). 단일 피드 가상화 = ARCH §7-4.

```yaml
space.1: 4    # 2xs
space.2: 8    # xs
space.3: 12   # sm
space.4: 16   # md
space.5: 20   # lg
space.6: 24   # xl
space.7: 28   # 2xl
space.8: 32   # 3xl
```
- **컨테이너:** 단일 컬럼 max-width **430px**(앱 피드), 가운데 정렬. 페이지 패딩 좌우 16 / 상 32 / 하 72(하단 안전영역).
- **카드 패딩:** feature 카드 20, chrome 패널(커버리지·인사) 16~18.
- **수직 리듬:** 섹션 간 22~28, 카드 간 16, 카드 내부 그룹 12~16.
- **정렬:** 본문 좌측 정렬 기본(§9 center-align 금지). 피드는 1열 카드 + 섹션 헤더 구분 — 획일적 3-card grid 금지(§9).
- **반응형:** 데스크톱 web도 단일 중앙 컬럼 유지(멀티컬럼 미사용 — 단일 피드 §7-4). 가로 확장은 컬럼 폭 소폭 증가만.

## 5. Elevation & Depth
> border가 1차 구분, shadow는 절제된 온기(핑크-tinted). nested card 금지(§9).

```yaml
radius.sm:   8     # mk 배지·dday
radius.md:   12    # 근거 quote·보류 메시지 inner
radius.lg:   16    # 버튼·탭
radius.xl:   24    # 카드·인사·커버리지·마감 wrap (시그니처 둥근 형태)
radius.pill: 999   # chip·meter segment·dot·cov-item

elevation.0:    "none"                                                          # 보류/빈 상태(flat + dashed border)
elevation.card: "0 2px 12px rgba(180,80,140,.07), 0 1px 3px rgba(43,36,51,.05)" # 카드 resting
elevation.lift: "0 6px 20px rgba(180,80,140,.13), 0 2px 6px rgba(43,36,51,.07)" # hover/active/인사
border.width:   "1.5px"   # 친근한 soft-chunky border (hairline 아님)
```

## 6. Shapes
- **카드:** 24px radius — 둥근 포도를 echo하는 시그니처 부드러움.
- **버튼·탭:** 16px. **chip·segment·dot:** pill(999). **마감 row:** ~18.
- **fit 링:** 정원(circle), arc = brand.gradient(fenced).
- **마스코트:** 원본 PNG(유기적 형태). 점수/데이터 영역엔 마스코트 형태 침범 금지(원칙 1).
- **보류/빈 컨테이너:** dashed 1.5px border — "의도된 placeholder(고장 아님)"로 읽히게.

<a id="design-7-components"></a>
## 7. Components
> primitives → composites → patterns. 시작점(스택 = Next.js+Tailwind): **shadcn/ui (Radix + CSS 변수)**. shadcn CSS 변수를 §2~§5 토큰에 매핑해 사용. 각 컴포넌트는 아래 8-상태 매트릭스를 정의(특히 empty/loading/error 누락 금지, §9).

### 7-1. Primitives
- **Button** — `primary`(grape 채움) / `ghost`(surface+border). 한 화면 primary CTA 1개(§9).
- **Chip/Tag** — `source`(출처: 토스/당근) · `count`(신규/마감 수, new=grape·due=pink) · `coverage`(on/off).
- **Tab** — 직군 분리(백엔드/데이터). active=ink 채움.
- **Text/Heading** — display(900) / heading(900) / body(400-500) / label(700) / meta(faint).
- **Icon** — lucide 계열 + 절제된 이모지(🍇⏰🔍📡); 16/20px. icon-tile-above-heading 반복 지양(§9).

### 7-2. Composites
- **FitScoreRing** — 0~100 + 라벨(높음/보통/낮음). arc = brand.gradient(fenced). 점수 숫자는 ink(장식 금지).
- **PassBand (합격가능성 5-step meter)** — level 1~5, 라벨 텍스트 + 채워진 segment. 색만 의존 금지(라벨 필수).
- **PodoStamp (반응)** — "podo 강추!" 등. *높음 이상* 티어에만, *카드 chrome*에만(점수 자체엔 금지, 원칙 1).
- **JobCard** — source/role/co/meta + FitScoreRing + PassBand + (collapsed toggle | expanded EvidenceBlock) + actions.
- **EvidenceBlock** — JD 인용(grounding span 강조) + 매핑 행(✓ ok / △ gap) + 액션. 근거 없으면 보류로 전이.
- **DeadlineRow** — D-day + role + mini fit. D-1 긴급 강조.
- **GreetingCard (podo 말풍선)** — podo(68px) + headline + count chip + 그라데이션 strip(fenced).
- **CoveragePanel** — on/off 채널 chip + 마지막 수집 시각. 상시 노출.
- **Toast** — "지원 기록됨" / "신규 도착" arrival 알림(최소).

### 7-3. Patterns
- **Feed** — 탭 + 섹션(마감 임박 / 오늘의 추천) + 리스트 가상화(커서 페이지네이션, ARCH §7-1·§7-4).
- **EmptyState** — "오늘은 신규가 적어요"(podo + 최근 7일 미처리 재노출). 일급.
- **PendingState (보류)** — 일급. podo(56px) + dashed 카드 + 정직한 메시지 + 원문 링크("틀린 점수보다 정직"). 가짜 점수 금지.
- **ErrorState** — 수집 실패/커버리지 degraded. 숨기지 않고 노출(Fail #3 차단). podo가 "아침 배달이 늦어요" 톤이되 사실 명확.
- **LoadingState** — skeleton 카드(shimmer) + ring indeterminate. *가짜 점수 절대 표시 금지*.

### 7-4. 상태 매트릭스 (8-상태 강제)
| 컴포넌트 | default | hover | active/pressed | focus | disabled | loading | error | empty |
|---|---|---|---|---|---|---|---|---|
| **Button.primary** | grape 채움 | accent-strong | accent-strong+scale .98 | 2px grape outline+offset | opacity .45, not-allowed | 라벨→spinner, 폭 유지 | 인라인 메시지+ghost로 폴백 | n/a |
| **Button.ghost** | surface+border | border/text→grape | scale .98 | 2px grape outline | opacity .45 | spinner | — | n/a |
| **Tab** | idle(muted) | border/text→grape | — | 2px grape outline | opacity .45 | count→· | — | "0건" 회색 라벨 |
| **JobCard** | resting(elevation.card) | lift+translateY-2 | translateY 0 press | 2px grape outline | — | skeleton(아래) | 카드 내 ErrorState | 섹션 EmptyState |
| **FitScoreRing** | arc=점수%, 숫자 | — | — | — | — | track pulse, 숫자 "··" | "—" + 사유 툴팁 | "이력서 먼저" 안내 |
| **PassBand** | level segments+라벨 | — | — | — | 전 segment 회색 | shimmer segments | — | "보류" 라벨+빈 segment |
| **EvidenceBlock** | quote+매핑 | — | — | quote 포커스 | — | line skeleton | "근거 확인 실패"→보류 | "근거 없음"→보류 |
| **CoveragePanel** | on/off chip | — | — | — | — | "확인 중…" | "수집 실패" 경고(danger) | n/a (항상 표시) |
| **GreetingCard** | podo+카운트 | — | — | — | — | "둘러보는 중…" | "아침 수집 실패" | "오늘은 적음" |

- skeleton: surface 위 line→line-strong shimmer, radius 동일, 텍스트 자리 막대. 모션은 §8 + reduced-motion 분기.

<a id="design-8-motion"></a>
## 8. Motion
> 모션은 '도착(포지션 도착!)'의 의미 전달 전용. 장식 모션 금지(§9). Material 3 가이드 정렬.

```yaml
ease.standard: "cubic-bezier(.2,.7,.3,1)"   # 진입·일반
ease.exit:     "cubic-bezier(.4,0,1,1)"
duration.micro:    120ms   # hover·tap·chip·탭 전환 피드백
duration.entrance: 200ms   # 카드/섹션 settle, arrival slide
duration.routing:  240ms   # 탭 스위치·페이지 전환
```
- **시그니처 'arrival' 모션:** 신규 공고 카드 = fade + `translateY(8px→0)`, stagger 40ms, ≤200ms — "포지션 도착" 의미. 매칭 확정 시 fit 링 arc 1회 draw(200ms, 루프 없음).
- **금지:** bounce/elastic/spring-overshoot, confetti, 무한·장식 루프, parallax (§9).
- **`prefers-reduced-motion: reduce`** (모든 모션 필수 분기): transform/translate/arc-draw 제거, opacity fade(≤120ms)만 또는 무모션. stagger 제거.

<a id="design-9-donts"></a>
## 9. Do's and Don'ts
> explicit prohibition (LLM 정확도 단일 최대 기여). 위반은 리뷰에서 1순위 차단.

**[기존 규율]**
- 색 5색 이내(+합격가능성 5-band) / **raw hex 금지 — §2 토큰만 참조**
- Pretendard 사용 / Inter·Roboto·Arial 디폴트 금지
- 3-column icon grid 디폴트 금지
- hierarchy는 size+weight+color 중 2축 이상
- 한 화면 primary CTA 2개 이상 금지
- 모든 motion에 `prefers-reduced-motion` 분기
- 모든 컴포넌트에 §7-4 의 8-상태 매트릭스 정의 (특히 empty/loading/error 누락 빈번)

**[anti-slop]**
- **포도/violet gradient는 §2-4 brand 3곳(로고 ai / fit 링 arc / 인사 strip 5px)에만. 전면·카드 배경 그라데이션 절대 금지** — 마스코트가 보라라 가장 빠지기 쉬운 슬롭(원칙 2).
- 카드 안의 카드(nested cards) 금지 — spacing·divider로 구분
- heading gradient text 금지 (예외: 로고 "ai" 워드마크 1곳, brand)
- glassmorphism·neon glow 디폴트 금지
- 전(全) 섹션 center-align 금지 — 본문 좌측 정렬
- 동일 형태 3-card row 무한 반복 지양 (피드는 1열 카드 + 섹션 구분)
- icon-tile-above-heading 패턴 반복 지양
- monospace를 "기술적 느낌" 장식용으로 남용 금지 (코드·식별자·수치에만)
- bounce/elastic/confetti 모션 금지 (모션은 '도착' 의미 전달 전용)
- sparkline 등 데이터 시각요소를 장식으로 사용 금지

**[podo ai 고유 — thesis 보호]**
- **귀여움이 판단 데이터를 장식하지 않게**: 점수·밴드·근거 텍스트에 마스코트/그라데이션/이모지 장식 금지. PodoStamp 반응은 *카드 chrome*에만, 점수 자체엔 X (원칙 1).
- **가짜 점수 금지**: LLM miss/근거 부족 시 숫자 대신 **보류 상태**(PendingState, 원칙 4 / GS-2). over-gamified 톤으로 점수 신뢰를 깎지 않는다.
- **커버리지 상시 노출**: "전부 수집" 인상 금지 — CoveragePanel 항상 표시(Fail #3 차단).
- **색만으로 의미 전달 금지**: 적합도·매핑은 항상 텍스트 라벨(+✓/△) 동반. band 색을 텍스트로 쓸 땐 `band-*-ink`(AA).
