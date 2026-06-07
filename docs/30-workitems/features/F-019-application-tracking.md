# F-019-application-tracking: 지원/스킵·즐겨찾기 기록 + 처리완료 정리

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
사용자가 피드에서 공고를 **지원/스킵·즐겨찾기**로 처리하고, 처리된 공고는 다음 진입 시 피드에서 정리되어 **"다음 날 누락 0"**(Charter §8 흐름1-7)을 유지하는 user-facing CRUD를 만든다. 지원 시 원본 채널 링크로 이동 또는 지원 체크 기록, 점수 낮아도 관심 공고는 즐겨찾기로 보존(Charter alternate). NestJS 소유 신규 테이블(사용자 격리). Fail #8(지원 기록 저장 실패) 대응.

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want to mark postings as applied/skipped or favorite them, so that processed jobs clear from my feed and I never re-process the same posting the next day(누락 0).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. JobCard에서 "지원하기" → 원본 채널 링크 이동 + 지원 기록(`applied`) 저장.
2. 관심 없으면 "스킵" → `skipped` 기록, 피드에서 정리.
3. 처리 완료 공고는 다음 진입 시 기본 피드에서 빠짐(누락 0 유지).
4. "지원 기록됨" Toast(최소 arrival 톤).
### Alternate path
1. 점수 낮아도 지원하고 싶은 공고 → 즐겨찾기(`favorite`) → 별도 보존, 시스템은 부족 근거 명시하되 막지 않음.
2. 즐겨찾기·재노출 공고를 합쳐 그날의 지원 후보 리스트 확인.
3. 스킵을 되돌리기 → 피드 재노출.
### Fail path
1. 🟡 지원 기록 저장 실패 → 다음 날 같은 공고 재노출(수용 가능 Fail #8, 단 장기 누적 시 치명) → 재시도/에러 표면화.
2. 🔴 타인 공고 처리 기록 위조(다른 user_id) → 인가 차단(F-016).

## 4. 범위
- NestJS: 지원/스킵/즐겨찾기 CRUD 엔드포인트(`/api/v1/...`) + 사용자 격리 테이블(예: `application_events`·`favorites`, api 소유 — ARCH §3-2).
- 처리 상태에 따른 피드 필터(처리완료 정리 — F-018 피드 쿼리와 정합).
- 즐겨찾기 보존·재노출 + 그날 후보 리스트.
- UI 액션(지원/스킵/즐겨찾기 버튼·Toast)은 F-018 JobCard actions에 결선.
- schema-contract test(신규 테이블·`user_id`).

## 5. 비범위
- 무응답/서류결과 피드백 루프 자동화 — Charter §5 비목표(수동/소규모만).
- 자동지원·원클릭 지원 — Charter §5 비목표(원본 채널 링크 이동까지).
- 지원 일정/마감 캘린더 — 비목표.
- GS-3 실데이터 분석(상위군 통과율) — M6 배포 후 트랙(본 feature는 *기록*까지, 분석은 후속).

## 6. 요구사항
- 처리 상태: `applied` / `skipped` / `favorite`(+해제). 사용자 격리(본인 기록만).
- 처리완료 공고는 기본 피드에서 정리(누락 0) — 단, 즐겨찾기·재노출 규칙 명시.
- 지원 = 원본 채널 링크 이동 + 기록(자동지원 아님).
- 저장 실패는 표면화(조용한 실패 금지) — 단 1회 실패는 수용(Fail #8), 재시도.
- 에러 바디·인가는 ARCH §7-1 / F-016 정합.

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 공고를 "지원"으로 처리하면 `applied` 기록이 본인 `user_id`로 저장되고 다음 피드 진입 시 기본 목록에서 정리된다.
- **FAC-2:** "즐겨찾기"한 공고는 점수와 무관하게 보존되어 별도로 다시 확인할 수 있다.
- **FAC-3:** 스킵한 공고는 기본 피드에서 빠지되 되돌리면 재노출된다.
- **FAC-4:** 타 사용자의 처리 기록을 조회/수정할 수 없다(인가 차단, F-016 정합).
- **FAC-5:** schema-contract pytest가 신규 처리/즐겨찾기 테이블 + `user_id`를 검증하고 green이다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-050:AC-1, T-051:AC-1
- FAC-2 → T-050:AC-2
- FAC-3 → T-051:AC-2
- FAC-4 → T-050:AC-3
- FAC-5 → T-050:AC-4

## 8. Non-functional Requirements
- 데이터 격리(본인 기록만) — F-016 인가 정합.
- 저장 실패 가시화(Fail #8) — 조용한 실패 금지.

## 8-1. UX 흐름 품질
- **primary task:** 공고 처리(지원/스킵/즐겨찾기) 1탭.
- **empty 흐름:** 처리할 공고 없음 → "오늘 처리할 공고를 다 봤어요"(포도).
- **loading 흐름:** 기록 저장 중 버튼 일시 disabled(낙관적 업데이트 가능).
- **error 흐름:** 저장 실패 → Toast "기록에 실패했어요. 다시 시도해주세요." + 재시도.
- **accessibility:** 액션 버튼 키보드·label, 상태 변경 announce.
- **copy 톤:** "지원 기록됐어요!"(포도 톤).
- **success metric (HEART):** Retention → 다음 날 재진입 시 재처리(중복) 비율 → "처리완료 누락 0" 근접(실 배포 후 이벤트 로그).

## 9. 엣지 케이스
- 지원 후 마음 변경 → 기록 취소/수정.
- 즐겨찾기한 공고가 마감됨 → 마감 표시하되 보존.
- 동일 공고 중복 처리 시도 → 멱등(1 기록).
- 처리완료 공고가 다음 크롤에서 갱신(유지) → 재노출 안 함(처리 상태 우선).

## 10. 의존성
- 선행: F-016(user 격리·인가), F-018(JobCard 액션 UI·피드 필터).
- 데이터: `recommendations`/공고 + 신규 처리 테이블.

## 11. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 happy 6·7 / alternate 2, Fail #8, §8 흐름1)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)

## 12. 열린 질문
- 처리 상태 모델 = 단일 `application_events`(이벤트 로그) vs 상태 컬럼 — plan(이벤트 로그가 GS-3 후속 분석에 유리).
- 재노출 규칙(스킵 며칠 후 재노출? 즐겨찾기 영구?) — 단순 규칙으로 시작.
- "처리완료 정리"와 신규/마감 diff의 상호작용 — F-018 피드 쿼리와 합의.
