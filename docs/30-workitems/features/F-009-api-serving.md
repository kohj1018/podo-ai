# F-009-api-serving: NestJS JSONB pass-through 피드·커버리지 서빙

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
NestJS(`podo/apps/api`)가 worker 산출을 피드로 서빙한다 — 정렬·커서 페이지는 worker가 영속한 **`recommendations` scalar projection**(`rank_position`)으로 하고, 각 항목의 근거(`ranking_runs.result`)는 **파싱 없이 opaque pass-through**로 첨부한다. `crawl_runs`에서 커버리지를 서빙한다. ranking·fit·score는 **계산하지 않는다**(§3-2 — worker 저장 결과 조회·서빙만). ARCH §7-1 컨벤션(경로·error envelope·커서 페이지네이션)을 따른다.

## 2. 사용자 가치 (User Story) — Type=technical-enabler 이므로 기술적 근거
- **무엇/왜:** Feed UI(F-010)가 데이터를 받을 백엔드 표면. NestJS는 worker JSONB를 opaque pass-through로 서빙해 폴리글랏 계약면을 0에 수렴(§3-2 규칙3·R6 완화 핵심). DISCOVERY F2·feed 서비스.
- **서비스하는 결정/가정:** ARCH §7-1 API 컨벤션 · §3-2 규칙1(read-only)·규칙3(JSONB pass-through) · ADR-101 D-CONTRACT.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `GET /api/v1/feed?cursor=…` → `recommendations`를 `rank_position` 순으로 커서 페이지 + `job_postings` 조인, 항목별 근거는 `ranking_runs.result`에서 opaque로 첨부.
2. `GET /api/v1/coverage` → `crawl_runs`에서 수집/미수집 채널 + 마지막 성공 시각 반환.
### Fail path
1. 🟡 잘못된 cursor → `{ error: { code, message } }` 단일 형태로 400.
2. 🟡 데이터 없음(아직 미채점) → 빈 목록 + 보류/empty 신호(가짜 점수 X).

## 4. 범위
- NestJS Prisma module(read-only) + `GET /api/v1/feed`(`recommendations` projection을 `rank_position` 정렬·커서 페이지네이션 + `job_postings` 조인; 근거는 `ranking_runs.result` opaque pass-through) + `GET /api/v1/coverage`.
- error envelope(`{ error: { code, message } }`) + `ValidationPipe`(쿼리 검증, controller 진입점 한정).
- 중복 제거(동일 공고 여러 채널 — 응답 단위).

## 5. 비범위
- 인증(미정, ARCH §7-1/§10) — M2 done-line이 로컬이라 비범위.
- ranking/fit/score 계산(worker 소유) · JSONB 내부 파싱·비즈니스 분기(opaque 유지).
- 지원기록 CRUD·알림.

## 6. 요구사항
- 경로 `/api/v1/<resource>` 복수형, error `{ error: { code, message } }` 단일 형태(§7-1).
- **정렬·커서는 `recommendations` scalar 컬럼(`rank_position`/`fit_level`)으로** — opaque JSONB를 파싱하지 않는다(cross-LLM P0 해소).
- `ranking_runs.result`는 응답 DTO에서 `unknown`/opaque — **파싱 금지**(§3-2 규칙3, §7-1 워커 산출물 서빙). 근거는 항목 펼침 시 그대로 실어 보냄.
- 피드는 **커서 기반** 페이지네이션(stable key=`rank_position`, offset 미사용 — §7-1).
- NestJS는 `recommendations`/`ranking_runs`/`job_postings`/`crawl_runs`를 **read-only**(write 금지, §3-2 규칙1).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `GET /api/v1/feed`가 `recommendations.rank_position` 순 공고 목록을 커서 페이지로 반환하고, 각 항목 근거를 `result`에서 opaque로 첨부한다.
- **FAC-2:** 응답이 §7-1 error envelope를 준수하고 `result`를 opaque(파싱 없이) pass-through한다.
- **FAC-3:** `GET /api/v1/coverage`가 수집/미수집 채널 + 마지막 성공 시각을 반환한다.
- **FAC-4:** NestJS는 어떤 worker/crawler 소유 테이블에도 write하지 않는다(read-only).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (recommendations 정렬·커서 + result opaque) → T-026:AC-1
- FAC-2 (envelope·opaque pass-through) → T-026:AC-2
- FAC-3 (coverage 서빙) → T-027:AC-1
- FAC-4 (read-only 경계) → T-026:AC-3, T-027:AC-2

## 8. Non-functional Requirements
- 성능: 저장된 결과 읽기라 LLM 지연과 분리(ARCH §8). 페이지네이션으로 응답 bound.
- 보안: 인증 미도입 — **외부 노출 전 반드시 결정**(§7-1). M2는 로컬이라 허용.

## 8-1. UX 흐름 품질
(해당 없음 — 비-UI 백엔드. 사용자 흐름은 F-010.)

## 9. 엣지 케이스
- 동일 공고 다채널 중복 → 응답 dedup.
- 아직 미채점 공고(`ranking_runs` 없음) → empty/보류 신호.
- cursor 경계(끝 페이지) 처리.

## 10. 의존성
- **선행:** T-018(api scaffold), T-020(스키마 — `recommendations` 포함), T-022(worker가 `ranking_runs`/`recommendations`를 채워야 서빙 의미).
- **블로킹:** F-010(Feed UI가 본 API를 소비).

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 규칙1·3)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (경로·error envelope·JSONB pass-through·커서 페이지네이션)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CONTRACT)

## 12. 열린 질문
- **결정(cross-LLM P0 회수):** 정렬·커서는 `recommendations.rank_position` scalar projection(opaque JSONB 파싱 안 함). 응답 = `recommendations`+`job_postings` 항목 목록 + 각 항목 `result` evidence를 opaque로 첨부.
