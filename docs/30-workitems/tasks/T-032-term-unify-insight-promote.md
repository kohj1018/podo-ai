# T-032-term-unify-insight-promote

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
M1→M2 누적 문서 부채 중 (1) 용어 divergence "합격가능성 밴드" → "적합도 5단계" 통일과 (2) DISCOVERY §15 Insight I-1/2/3 status promote를 회수한다. 용어 divergence는 validate·stabilize·plan 라운드에서 false-positive를 만들고, Insight promote 누락은 `/discover-product --update` SSOT 경로를 막는다(F-012 §2). **정합만 — 제품 전략·기능 범위 재정의 금지.**

## 2. 작업 범위
- `docs/10-charter/DISCOVERY.md`(SSOT)·`docs/10-charter/PROJECT_CHARTER.md`·`docs/20-system/DESIGN.md`·`docs/30-workitems/**`에서 "합격가능성 밴드" 표현을 "적합도 5단계"(짧은 형태 "적합도")로 치환.
- DISCOVERY §15 Insight Backlog: I-1 `open→done`, I-2/I-3 `open→planned` + `linked feature` 채움.
- 치환 경로는 DISCOVERY=SSOT(ADR-035): DISCOVERY는 `/discover-product --update`로, Charter snapshot은 `/bootstrap-project --apply`로 sync. DESIGN/workitem은 직접 편집.

## 3. 구현 항목
1. 현행 분포 확인 — 현재: `grep -rn "합격가능성" docs/`가 15개 파일 53건(DISCOVERY 12·Charter 6·DESIGN 8 등) → 변경: 치환 대상(정책/제품 표현)과 보존 대상(비목표 문맥의 "합격확률/합격가능성을 % 로 제시 안 함", `band-*` 토큰명) 분류. → 확인: 분류 목록을 본 task §8에 1줄 기록. (AC-1)
2. `docs/10-charter/DISCOVERY.md` — 현재: "합격가능성 밴드" 표현 다수 → 변경: `/discover-product --update`로 "적합도 5단계"로 치환(SSOT 우선). → 확인: `grep -n "합격가능성 밴드" docs/10-charter/DISCOVERY.md` = 0. (AC-1)
3. `docs/10-charter/PROJECT_CHARTER.md` — 현재: DISCOVERY와 동일 divergence → 변경: `/bootstrap-project --apply`로 snapshot sync(직접 편집 가능). → 확인: `grep -n "합격가능성 밴드" docs/10-charter/PROJECT_CHARTER.md` = 0. (AC-1)
4. `docs/20-system/DESIGN.md` + `docs/30-workitems/**` — 현재: "합격가능성 밴드" 잔존(T-028 메모: "DESIGN 용어 reconcile은 후속") → 변경: 직접 편집 치환. M2/M3 milestone·F-001 등 workitem 포함. → 확인: `grep -rn "합격가능성 밴드" docs/20-system/DESIGN.md docs/30-workitems/` = 0. (AC-1)
5. `docs/10-charter/DISCOVERY.md` §15 Insight Backlog — 현재: I-1/I-2/I-3 `status: open` → 변경: I-1 `status: done`(M2가 스코어링 입력 신뢰 구현), I-2/I-3 `status: planned` + 각 행 `linked feature`에 대응 F-NNN(예: I-1→F-013/F-014) 기입. `/discover-product --update` 경유. → 확인: §15 표에서 I-1=done·I-2/I-3=planned + linked feature 비어있지 않음. (AC-2)

## 4. 제외 항목
- 제품 전략·기능 범위 재정의(F-012 §5). · 새 ADR 신설. · UI 컴포넌트/스코어링 코드 변경. · `band-*` 토큰명·"밴드(band)" 기술용어 치환(T-033 token sync는 별도). · ADR-100/README/IMPROVEMENT_GUIDE/discovery-reviews의 과거 표현(이력 보존 — 본 AC scope 밖).

## 4-1. 변경 예정 파일/경로
- `docs/10-charter/DISCOVERY.md` — §15 Insight I-1 open→done, I-2/I-3 open→planned + linked feature(AC-2). (AC-1 bigram은 부재 — 변경 없음.)
- `docs/10-charter/PROJECT_CHARTER.md` — §8 "합격가능성 밴드"→"적합도 5단계"(AC-1).
- `docs/20-system/DESIGN.md` — 디자인 원칙 1·3 + §8 "합격가능성 밴드"→"적합도/적합도 5단계"(AC-1, band-* 토큰명 보존).
- `docs/30-workitems/features/F-001-core-value.md` — §1·§3·§4 "합격가능성 밴드"→"적합도 5단계"(AC-1).

## 5. 완료 조건
DISCOVERY/Charter/DESIGN/workitem에서 "합격가능성 밴드" 표현이 사라지고 "적합도 5단계"로 통일되며, DISCOVERY §15 Insight I-1/2/3가 promote(done/planned+linked)된다.

## 6. Acceptance Criteria
- AC-1 [Given] DISCOVERY/Charter/DESIGN/workitem에 "합격가능성 밴드" 표현 [When] SSOT 경로(`/discover-product --update`→`/bootstrap-project --apply`) + 직접 편집으로 치환 [Then] `grep -rn "합격가능성 밴드" docs/10-charter/DISCOVERY.md docs/10-charter/PROJECT_CHARTER.md docs/20-system/DESIGN.md docs/30-workitems/` = 0건이고, 의미 맥락상 부적절한 단순치환(비목표 "합격확률 %" 문맥)은 발생하지 않는다.
- AC-2 [Given] DISCOVERY §15 Insight Backlog의 I-1/I-2/I-3가 `status: open` [When] promote [Then] I-1 `status: done`, I-2·I-3 `status: planned`이고 세 행 모두 `linked feature`가 채워진다(빈 값 0).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → grep 검증: `grep -rn "합격가능성 밴드" docs/10-charter/DISCOVERY.md docs/10-charter/PROJECT_CHARTER.md docs/20-system/DESIGN.md docs/30-workitems/` exit 1(매치 0)
- AC-2 → 문서 필드 점검: DISCOVERY.md §15 표에서 I-1=done·I-2/I-3=planned + linked feature 비어있지 않음(수기 또는 yaml/표 파서)

## 6-2. TDD opt-out
- 사유: 선언적 문서 정합 — RGR 코드 사이클이 아니라 grep 0건·status 필드 존재가 결정적 측정 단위(AC-1/AC-2가 곧 oracle). 회귀는 cross-stabilize term grep이 상시 가드.
- Follow-up task: 해당 없음(문서 reconcile task — 코드 재구현 대상 아님).

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Feature: [F-012-doc-reconcile](../features/F-012-doc-reconcile.md)
- ADR: [ADR-035](../../90-decisions/boilerplate/ADR-035-continuous-discovery.md) (DISCOVERY=SSOT reconcile 경로)

## 8. 메모
- 해석 확정: AC-1 치환 대상 = "합격가능성 밴드"(정책/제품 표현). 보존 = (a) Charter §5 비목표의 "합격확률/합격가능성 % 비제시" 문맥, (b) `band-*`/"밴드(band)" 기술용어(토큰명) — M3 milestone §7 "적합도 5단계로 통일" 권장 기본값 채택(짧은 형태 "적합도").
- DISCOVERY=SSOT: DISCOVERY 직접 편집보다 `/discover-product --update` 경유 권장(Charter는 `/bootstrap-project --apply` snapshot sync — 자동 sync 안 됨, ADR-035).

## 9. 의존성
- depends_on: []   # M3 첫 작업, scaffold 의존 0, 즉시 착수
- read_set: ["docs/10-charter/DISCOVERY.md", "docs/10-charter/PROJECT_CHARTER.md", "docs/20-system/DESIGN.md"]
- write_set: ["docs/10-charter/DISCOVERY.md", "docs/10-charter/PROJECT_CHARTER.md", "docs/20-system/DESIGN.md", "docs/30-workitems/**"]
- verifier: "grep -rL \"합격가능성 밴드\" docs/10-charter/DISCOVERY.md"
- # T-033이 DESIGN.md를 read(token 이름) — write_set 교집합 없음(T-033은 globals.css/worker write), 병렬 가능하나 DESIGN.md 동시 편집 주의
