# F-029-account-and-navigation

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
로그인 사용자용 **마이페이지(계정 허브)**와 **전역 네비게이션**을 추가하고, 그동안 액션만 있고 회수 화면이 없던 **즐겨찾기·지원기록 목록 뷰**를 붙인다. 현재 /resume 진입이 주소창뿐인 문제를 네비로 해소한다. 두 뷰는 기존 API(`GET /api/v1/applications?filter=`)를 소비하는 **순수 프론트**. 근거: Charter §3.1 Alt#2 + persona pain("지원 기록 스프레드시트 수기 관리").

## 2. 사용자 가치 (User Story)
- As 유진(Charter §2.1), I want 마이페이지에서 이력서·즐겨찾기·지원기록에 도달하고 싶다, so that 매번 주소창을 치지 않는다.
- As 유진, I want 즐겨찾기·지원한 공고를 한곳에서 보고 싶다, so that 스프레드시트 수기 관리를 대체한다.

## 3. 핵심 시나리오 (Feature-level)
- **happy**: 피드 헤더 → 마이페이지 → 즐겨찾기/지원기록 확인 → 이력서 수정 진입(→/resume).
- **alternate**: 즐겨찾기/지원 0건 → 빈 상태 안내(포도 톤) + 피드로 돌아가기.
- **fail**: 목록 fetch 실패 → 에러 상태 노출(빈 목록으로 삼키지 않음, REV-M2-UI-001 정합).

## 4. 범위
- 마이페이지 라우트(허브): 이력서 보기/수정 · 즐겨찾기 · 지원기록 · 로그아웃 진입.
- AppHeader 전역 네비(피드↔마이페이지↔resume 편집), 인증 상태만.
- 즐겨찾기 목록 뷰(`?filter=favorite`) · 지원기록 목록 뷰(`?filter=applied`).

## 5. 비범위
- 다중 이력서 관리(여러 버전 보관·전환) — 단일 활성 유지(M7 §4).
- 지원 상태 편집/스테이지(지원→서류→면접) 트래킹 — 후속.
- 계정 설정/프로필 편집(이메일·아바타) — 후속.

## 6. 요구사항
- 모든 보호 fetch `credentials:'include'`. 본인 데이터만(user_id 범위, ARCH §7-1).
- 라우트 구조(별 라우트 vs /me 탭)는 T-093/094 분해 시 확정(§12).
- 빈/로딩/에러 상태 일급(DESIGN §7-4).

## 7. Feature-level Acceptance Criteria
- FAC-1 로그인 사용자가 네비로 마이페이지·resume 편집·활동 뷰에 도달한다.
- FAC-2 마이페이지가 계정 허브(이력서/즐겨찾기/지원기록/로그아웃 진입)로 동작한다.
- FAC-3 즐겨찾기·지원기록을 실 API 목록으로 회수하며 빈/로딩/에러를 처리한다.

## 7-1. FAC ↔ AC 매핑표
- FAC-1 → T-093:AC-2, T-093:AC-3
- FAC-2 → T-093:AC-1
- FAC-3 → T-094:AC-1, T-094:AC-2, T-094:AC-3

## 8. Non-functional Requirements
- 보안: user_id 범위 인가(타인 데이터 차단). 세션 쿠키 교차출처.
- 접근성: 네비 키보드 도달·aria, 목록 시맨틱.

## 8-1. UX 흐름 품질
- primary task: 마이페이지에서 원하는 surface로 1탭 이동.
- empty/loading/error: 활동 0건=포도 빈 상태, 로딩=skeleton, 실패=에러+재시도.
- accessibility: nav `aria-current`, 목록 role, 포커스 순서.
- copy 톤: "아직 즐겨찾기한 공고가 없어요" 등 포도 톤.
- success metric(HEART-Adoption): resume 편집 재진입률(주소창 의존 제거) — 정성/실데이터.

## 9. 엣지 케이스
- 즐겨찾기/지원 후 unfavorite/unskip된 항목 — 최신 action 기준(applications upsert 1행) 반영.
- 이력서 없는 사용자가 마이페이지 진입 → 이력서 작성 유도(/resume).

## 10. 의존성
- 기존 `GET /api/v1/applications?filter=`(applications.controller.ts:46) · SessionProvider/AppHeader.

## 11. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)(멀티유저 데이터 격리)

## 12. 열린 질문
- 별 라우트(`/me`·`/favorites`·`/applications`) vs 마이페이지 탭 통합?
- 지원기록 뷰의 정렬(최근순)·필터(applied/favorite 동시) 범위.
