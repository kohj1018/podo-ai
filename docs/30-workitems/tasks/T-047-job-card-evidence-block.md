# T-047-job-card-evidence-block

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
**JobCard**(공고 카드)와 **EvidenceBlock**(근거 펼침)을 완성한다. 적합도 5단계 PassBand 배지·FitScoreRing(arc fenced 그라데이션)·JD 인용 grounding span·이력서↔JD 매핑(✓ ok / △ gap)·마감 D-day·PendingState(보류 공고)·신규/마감 diff 표식을 포함. DESIGN.md §7-4 8-상태 중 JobCard 레벨 상태 처리. T-046(8-상태 기반) 선행.

## 2. 작업 범위
- `JobCard` 컴포넌트: 출처(토스/당근) + 직무·회사 + FitScoreRing(arc=fenced gradient §2-4) + PassBand 5단계(band-1~5 토큰 색+텍스트 라벨) + 마감 D-day(DeadlineRow) + 신규/마감 diff 표식(`NEW` / 마감 badge) + 클릭 시 EvidenceBlock 토글.
- `FitScoreRing`: arc SVG, fenced 그라데이션(§2-4 허용 3곳 = 로고·**fit 링 arc**·인사 strip 중 "링 arc" 1곳). band별 색 토큰 사용(raw hex 0). ring indeterminate = 채점 중 상태(T-046 연결). **보류(held) 공고 = ring 없음(PendingState dashed 카드).**
- `PassBand`: 5단계 한글 라벨("매우 적합"~"낮음") + 토큰 색 + 텍스트 라벨 동반(색만으로 의미 전달 금지).
- `EvidenceBlock`: JD 인용 그라운딩 span(강조) + 이력서↔JD 매핑 리스트(`✓ 충족 / △ 부족`) + `aria-expanded` + 키보드 toggle.
- `PendingState`: held 공고용 — dashed 카드 + "포도가 아직 이 공고를 분석하지 못했어요" + 원문 링크.
- `DeadlineRow`: D-day 숫자 + D-1 긴급 강조(토큰 색, raw hex 금지).
- DESIGN.md §7 JobCard·FitScoreRing·PassBand·EvidenceBlock·PendingState·DeadlineRow 인벤토리 등록.

## 3. 구현 항목
1. `podo/apps/web/components/PassBand.tsx` (신규) — `band: 1|2|3|4|5`, `label: string` props. 배경=`var(--band-{n})` 토큰, 텍스트=`var(--band-{n}-ink)`. raw hex 0. `aria-label="적합도: {label}"`. → 확인: AC-1 토큰 색. (AC-1)
2. `podo/apps/web/components/FitScoreRing.tsx` (신규) — SVG arc. `band: 1|2|5|null`. band별 stroke = `var(--band-{n})`. fenced gradient는 §2-4 3곳 규칙 준수(링은 허용 1곳). indeterminate(채점 중) = CSS animation + `aria-label="분석 중"`. held = 링 미표시. `prefers-reduced-motion: reduce` → animation 중단(T-049 연계). → 확인: AC-1 fenced gradient, raw hex 0. (AC-1)
3. `podo/apps/web/components/EvidenceBlock.tsx` (신규) — `defaultExpanded=false`. toggle 버튼 `aria-expanded={isOpen}` + `aria-controls` + 키보드 Enter/Space. JD 인용: `<mark>` + `var(--accent-subtle)` 배경(토큰). 매핑 리스트: `✓`/`△` + 텍스트(색만 단독 금지). → 확인: AC-2 토글 + aria-expanded. (AC-2)
4. `podo/apps/web/components/DeadlineRow.tsx` (신규) — `daysLeft: number`. D-1 이하: `var(--danger)` 색 + "마감 D-1 긴급" 텍스트. D-7 이하: `var(--warning)`. 색만 단독 금지(텍스트 동반). → 확인: D-1 긴급 렌더. (AC-1)
5. `podo/apps/web/components/PendingState.tsx` (신규) — dashed border + 포도 PNG + "포도가 아직 이 공고를 분석하지 못했어요" + `<a href={url}>원문 보기</a>`. → 확인: AC-3 가짜 점수 없음. (AC-3)
6. `podo/apps/web/components/JobCard.tsx` — 현재: 단순 존재 여부 불명 → 변경(또는 신규): PassBand + FitScoreRing + DeadlineRow + diff badge + EvidenceBlock 토글 통합. held 공고 → PendingState 렌더. 카드 `role=article aria-label="{회사} {직무}"`. → 확인: AC-1~3 통합. (AC-1, AC-2, AC-3)
7. `docs/20-system/DESIGN.md` §7 — **6개 컴포넌트(FitScoreRing·PassBand·JobCard·EvidenceBlock·DeadlineRow·PendingState)는 이미 §7-2/§7-3에 등록됨** → 신규 등록 불요, read-only 참조만(write_set에서 DESIGN.md 제거 — scope 축소). → 확인: 항목 존재 확인.
8. `podo/apps/web/test/job_card.spec.tsx` (신규) — AC-1(PassBand 토큰 색 + ring fenced gradient), AC-2(EvidenceBlock 토글 + aria-expanded), AC-3(held 공고 PendingState, 가짜 점수 없음). → 확인: `pnpm --filter web test` green. (AC-1, AC-2, AC-3)

## 4. 제외 항목
- lottie arrival 모션(T-048). · 접근성 심화 단언(T-049). · 지원/스킵 버튼(T-051). · 커서 페이지네이션. · 신규 스코어링·출력계약 변경(동결).

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/PassBand.tsx` (수정 — aria-label 추가)
- `podo/apps/web/components/FitScoreRing.tsx` (수정 — aria-label + indeterminate, fenced gradient 유지)
- `podo/apps/web/components/EvidenceBlock.tsx` (수정 — 자체 토글 button + aria-expanded/aria-controls + 매핑 ✓충족/△부족)
- `podo/apps/web/components/DeadlineRow.tsx` (신규)
- `podo/apps/web/components/PendingState.tsx` (신규)
- `podo/apps/web/components/JobCard.tsx` (수정 — held→PendingState, DeadlineRow, diff badge(NEW/마감), EvidenceBlock 통합)
- `podo/apps/web/test/job_card.spec.tsx` (신규)
- `podo/apps/web/test/evidence_coverage.spec.tsx` (수정 — held 테스트가 held-badge→PendingState, T-047 ripple)
- (read-only) `docs/20-system/DESIGN.md` §7 — 6개 컴포넌트 이미 등록(§3 item7 — 신규 등록 불요)

## 5. 완료 조건
JobCard가 적합도 배지·ring·근거 펼침·마감·신규 표식·보류 상태를 올바르게 렌더한다. held 공고에 가짜 점수가 없다. EvidenceBlock이 키보드로 토글된다. 색에 raw hex가 없다.

## 6. Acceptance Criteria
- AC-1 [Given] fit_level=5 공고 JobCard [When] 렌더 [Then] PassBand가 "매우 적합" 텍스트 라벨과 `var(--band-5)` 토큰 색을 표시하고 FitScoreRing arc에 raw hex가 없다.
- AC-2 [Given] JobCard EvidenceBlock(닫힘) [When] 키보드 Enter [Then] EvidenceBlock이 펼쳐지고 `aria-expanded=true`가 되며 JD 인용 span과 이력서↔JD 매핑 리스트가 렌더된다.
- AC-3 [Given] held 공고(fit_level=null) [When] JobCard 렌더 [Then] PendingState(dashed 카드 + 원문 링크)가 표시되고 어떤 숫자 점수도 렌더되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/job_card.spec.tsx::test_AC_1_pass_band_token_color_no_hex_ring_fenced_gradient
- AC-2 → vitest::podo/apps/web/test/job_card.spec.tsx::test_AC_2_evidence_block_keyboard_toggle_aria_expanded
- AC-3 → vitest::podo/apps/web/test/job_card.spec.tsx::test_AC_3_held_job_pending_state_no_fake_score

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-018-companion-feed-experience](../features/F-018-companion-feed-experience.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors), [## 2-4 Fenced Gradient](../../20-system/DESIGN.md)
- ADR: [ADR-027](../../90-decisions/boilerplate/ADR-027-interface-decision-allocation.md) · [ADR-049](../../90-decisions/boilerplate/ADR-049-concept-mockup-first-design.md)

## 8. 메모
- fenced 그라데이션 3곳(DESIGN §2-4): **로고 "ai" 워드마크 · fit 점수 링 arc · 인사 strip 상단 5px** 만. **전면/카드 배경 그라데이션 금지**(원칙 2). 본 task의 유일한 gradient 사용처 = FitScoreRing arc(3곳 중 1곳). 그 외 컴포넌트(JobCard·PassBand 등)엔 gradient 금지.
- PendingState는 LLM miss(fit_level=null, status='held') 공고에만. 채점 중(scoring)은 T-046 skeleton.
- EvidenceBlock 데이터: `ranking_runs.result` JSONB pass-through. web은 표시만(출력계약 동결 — 새 필드 추가 X).
- 색만으로 의미 전달 금지(DESIGN §1): PassBand·DeadlineRow·매핑 항상 텍스트 라벨 동반.
- 구현 결정(implement) — **PassBand 라벨 = DESIGN canonical "매우 높음"**: AC-1 문구 "매우 적합"은 서술이고 DESIGN §2-1(line 65 주석 band-5="매우 높음") + 기존 feed.spec이 "적합도 매우 높음" → 문서 권위(DESIGN > task) + 회귀 보존 위해 "매우 높음" 유지. AC-1 테스트는 실제 라벨 "매우 높음" + var(--band-5-ink) 토큰을 단언(AC 의도=상위 밴드 토큰·라벨 표시 충족).
- 구현 결정(implement) — **EvidenceBlock 자체 토글**(§3 item3): JobCard의 별도 토글 제거, EvidenceBlock이 button('근거 보기'/'근거 접기')+aria-expanded+aria-controls 소유. 네이티브 button=키보드(Enter/Space) 접근 가능 → 테스트는 button 활성(click=활성 프록시)+aria-expanded 토글 단언(user-event 미설치). 기존 evidence_coverage AC-1('근거 보기' click→인용)은 그대로 통과.
- 구현 결정(implement) — **held→PendingState**(AC-3): JobCard held 분기를 inline held-badge에서 PendingState(dashed+원문 링크)로 교체. FitScoreRing/PassBand 미렌더(숫자 점수 0). evidence_coverage held 테스트를 PendingState 단언으로 갱신(ripple). FitScoreRing은 fenced gradient(var(--brand-gradient)) 유지(raw hex 0) — SVG arc 전면 재작성은 YAGNI(AC-1 no-hex+fenced 충족).
- 검증(implement): web vitest job_card 3 pass + 기존 web 27 회귀 0 · `pnpm validate` green.

## 9. 의존성
- depends_on: [T-046]
- read_set: ["docs/20-system/DESIGN.md", "podo/apps/web/components/FeedList.tsx", "podo/apps/web/app/globals.css"]
- write_set: ["podo/apps/web/components/PassBand.tsx", "podo/apps/web/components/FitScoreRing.tsx", "podo/apps/web/components/EvidenceBlock.tsx", "podo/apps/web/components/DeadlineRow.tsx", "podo/apps/web/components/PendingState.tsx", "podo/apps/web/components/JobCard.tsx", "podo/apps/web/test/job_card.spec.tsx"]
- assumptions: ["T-046 8-상태 피드 기반 존재", "DESIGN §2 토큰(--band-1~5·--danger·--warning 등) globals.css 정의됨", "T-028 RTL 인프라 존재"]
- verifier: "pnpm --filter @podo/web test"
