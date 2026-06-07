# T-052-multiuser-e2e-rewire

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
M4 done-line(멀티유저 로컬 E2E)을 자동 게이트로 박는다. `scripts/e2e.mjs`를 **OAuth 우회 → 2명 사용자 → 각자 업로드 → 큐(SQS) 경유 채점 → 격리된 피드 → 지원/즐겨찾기**로 재배선하고, **데이터 격리 Pass** + **계정 PII 미유입**(F-016 FAC-6) 검증을 포함한다. M2/M3 E2E 패턴(웜캐시 무키) 정합.

## 2. 작업 범위
- `scripts/e2e.mjs` 재배선: docker compose up(Postgres+pgvector + LocalStack SQS) → migrate → **사용자 A·B 테스트 세션(OAuth 우회, T-042)** → 각자 `.txt` 업로드(마스킹) → `POST /resumes/:id/score`(enqueue) → **큐 드레인 대기**(worker consumer) → 각자 격리 피드에 적합도 배지·근거·커버리지·신규/마감 diff → 지원/즐겨찾기 기록.
- **데이터 격리 assert**: A 세션으로 B의 resume/feed/application 접근 → 차단(403/404).
- **계정 PII assert(F-016 FAC-6)**: 계정 식별자(이메일·표시이름)가 `ranking_runs.result`·`.cache/llm`·앱 로그에 literal scan 0.
- 무키 경로: 마스킹 fixture 이력서 + 웜캐시 + 큐 드레인 → 외부 LLM 0(`pnpm e2e` exit 0).
- CI `e2e-smoke.yml` 갱신(멀티유저·큐 경로).

## 3. 구현 항목
1. `scripts/e2e.mjs` — 2-user OAuth 우회 + 업로드 + enqueue + 큐 드레인 폴링 + 피드/격리/PII assert. → 확인: `pnpm e2e` exit 0 실측 (AC-1, AC-2, AC-3)
2. 큐 드레인 헬퍼(작업 `done`까지 폴링, 타임아웃). → AC-1.
3. `scripts/e2e_account_pii_scan`(또는 기존 PII scan 확장) — 계정 식별자 하류 표면 scan. → AC-3.
4. `.github/workflows/e2e-smoke.yml` — 멀티유저·SQS(LocalStack) 경로 갱신.

## 4. 제외 항목
- 실 배포 환경 E2E — M6(T-086).
- 실 OAuth provider 왕복 — 우회 경로로 대체(redirect는 M6).
- live LLM 채점 — 웜캐시(키 보유 시만 live).

## 4-1. 변경 예정 파일/경로
- `scripts/e2e.mjs` (재배선 — 2-user OAuth 우회 + 큐 enqueue/드레인 + 격리/지원기록/PII assert + worker 호스트 기동)
- `scripts/e2e_account_pii_scan.py` (신규 — 계정 PII 미유입 스캔)
- `scripts/e2e_seed_users.sql` (신규 — 사용자 A·B 시드, prisma db execute)
- `.github/workflows/e2e-smoke.yml` — LocalStack SQS service + 큐 생성 step + SQS/AWS env
- (웜캐시 재생성 불요 — 기존 fixture 웜캐시가 큐 경로에서도 hit, run_scoring 불변)

## 5. 완료 조건
무키 `pnpm e2e`가 2명 OAuth 우회→업로드→큐 채점→격리 피드→지원기록까지 exit 0으로 완주하고, 데이터 격리·계정 PII 미유입이 자동 검증된다.

## 6. Acceptance Criteria
- AC-1 [Given] fresh clone + docker compose(Postgres+pgvector+LocalStack SQS) [When] 무키 `pnpm e2e` [Then] 사용자 A·B가 OAuth 우회 세션으로 각자 업로드→enqueue→큐 드레인→피드 적합도 배지 렌더까지 exit 0으로 완주한다(외부 LLM 0, 웜캐시).
- AC-2 [Given] 사용자 A 세션 [When] B의 resume_id/feed/application 접근 [Then] 403/404로 차단되고 B 데이터가 노출되지 않는다(데이터 격리 Pass).
- AC-3 [Given] E2E 완료 후 [When] 계정 식별자(이메일·표시이름)를 `ranking_runs.result`·`.cache/llm`·앱 로그에서 literal scan [Then] 0건이다(계정 PII 미유입 — F-016 FAC-6, ADR-105 Amend1).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `pnpm e2e` (scripts/e2e.mjs, exit 0 실측 — 멀티유저 업로드→큐→피드)
- AC-2 → scripts/e2e.mjs 내 격리 assert 단계 (A→B 접근 403/404)
- AC-3 → `python scripts/e2e_account_pii_scan.py` (하류 표면 계정 PII 0)

## 6-2. TDD opt-out
- 사유: E2E 오케스트레이션 하니스라 단위 TDD 부적합 — `scripts/e2e.mjs` 무키 exit 0 실측이 Red→Green 기준(미배선=Red, 완주=Green).
- Follow-up task: per-기능 단위 TDD는 T-042~T-051이 커버(본 task는 통합 게이트이므로 별도 follow-up task 불요).

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md) (§5 멀티유저 E2E·데이터 격리 Pass·PII 불변식)
- Feature: [F-016](../features/F-016-oauth-multiuser.md) (FAC-6 계정 PII) · [F-017](../features/F-017-worker-trigger-queue.md) (FAC-5 큐 E2E)
- Architecture-Iface: [ARCH ## 7-1 인증/API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1), [## 7-3 워커 트리거](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md) · [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md) · [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1)
- 선례: M2-E2E-001 / M3-E2E-001(IMPROVEMENT_GUIDE) — 업로드→큐 재배선 동형.

## 8. 메모
- M2/M3와 동형: report-only stabilize가 못 닫는 done-line E2E를 코드 작업으로 자동 게이트화.
- 웜캐시는 *마스킹 fixture* 이력서로만(실 PII 웜캐시 금지 — PII Safety 정합).
- 구현 결정(implement): 사용자 시드 = `prisma db execute --file e2e_seed_users.sql`(cross-env, auth.controller 불변 — test-session은 {userId}만). 세션 쿠키는 Node fetch `getSetCookie()`로 수동 보관(쿠키 jar 없음). worker는 호스트 프로세스(`uv run python -m worker`, e2e가 spawn — M4 컨테이너 아님, T-045 정합). AWS 자격증명은 LocalStack용 더미(SDK/boto3 서명에 존재 필요). api는 NODE_ENV=test로 기동(test-session 우회 활성).
- 구현 결정(implement): A·B가 동일 fixture 업로드 → 동일 마스킹본 → 동일 캐시 키(resume_id만 다른 별 run) → 웜캐시 hit(키 불요). 격리는 resume.user_id(A≠B)로 getFeed 범위·score 소유권·scoring-job 404가 보장.
- **실측 결과(implement)**: `pnpm e2e`(docker compose: Postgres+LocalStack SQS) **exit 0** — 2-user 로그인→업로드(마스킹)→enqueue(202)→큐 드레인(worker SQS consume→ranking_run→done)→각자 격리 피드(scored 6/held 0)→비인증 401·A→B 403/404→지원 applied→피드 정리→PII scan(raw 0·account 0). `pnpm validate` green.

## 9. 의존성
- depends_on: [T-043, T-045, T-051]
- read_set: ["scripts/e2e.mjs", "ai/worker/", "podo/apps/api/src/", "podo/apps/web/"]
- write_set: ["scripts/e2e.mjs", "scripts/e2e_account_pii_scan.py", ".github/workflows/e2e-smoke.yml"]
- assumptions: ["T-042/043(OAuth+우회) · T-044/045(큐) · T-050/051(지원기록) 완료", "마스킹 fixture 웜캐시 사용자 키 1회 생성 가능"]
- verifier: "pnpm e2e"
