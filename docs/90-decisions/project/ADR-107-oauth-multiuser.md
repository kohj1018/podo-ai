# ADR-107 — OAuth 멀티유저 인증 + Charter 멀티유저 비목표 반전

## Status
accepted

## Context
Charter §5는 멀티유저를 *비목표*("협업 / 멀티유저 — self-proxy 단일 사용자 기준")로 박았고, ARCH §7-1은 인증을 "미정(단일 사용자 MVP) — 외부 노출 전 반드시 결정"으로 두었다. M3 §4는 "M4에서 멀티유저를 다루려면 ADR로 범위 변경 선결"이라 예고했다.

M4는 "실서비스용 핵심 MVP 완성"을 목표로 하며, 이는 본인 이력서·피드·지원기록이 사용자별로 격리되는 멀티유저를 전제한다. 본 ADR이 그 범위 변경과 인증 방식을 확정한다.

## 결정

### D1. Charter §5 "멀티유저 비목표" 반전 (범위 변경)
멀티유저를 **M4 범위로 채택**한다. 단, 반전 범위는 *각자 독립 계정 + 데이터 격리*에 한정한다 — **협업/공유(취업 스터디·코치와 공유) 기능은 여전히 비범위**(Charter §5 "협업" 유지). DISCOVERY/Charter snapshot은 본 ADR 기준으로 sync한다.

### D2. 인증 = OAuth 소셜 로그인 (GitHub + Google)
자체 비밀번호 인증은 도입하지 않는다(비밀번호 저장·복구·유출 부담 0). **provider = GitHub + Google**(개발자 페르소나 "유진" 정합 — GitHub은 사실상 필수, Google은 대중성). 카카오/네이버는 후속.

### D3. 세션 = httpOnly 쿠키 세션
OAuth 인증 후 세션은 **httpOnly 쿠키 세션**으로 유지한다(SSR Next.js 정합, XSS 토큰 탈취면 축소). JWT-in-localStorage는 기각.

### D4. 데이터 격리 = `user_id` + api 인가
`users` 테이블(api 소유, ARCH §3-2) 신설. `resumes`·`ranking_runs`·`recommendations`·지원/즐겨찾기 테이블은 `user_id`로 묶이고, **모든 조회·채점은 인증 사용자 본인 데이터로 범위 제한**한다. 사용자 A가 B의 데이터에 *어떤 경로로도*(직접 id 추측·API 우회) 접근 불가 — **횡단 접근 차단이 멀티유저 안전 게이트**(M4 graduation 필수).

### D5. 테스트/CI 인증 우회 경로
OAuth는 redirect callback이 필요해 무키 E2E/CI에서 그대로 돌리기 어렵다. **테스트 전용 인증 우회(fake provider 또는 시드 세션)** 경로를 둬 무키 자동 게이트(M2/M3 웜캐시 패턴)를 보존한다. 우회 경로는 프로덕션 빌드에서 비활성.

### D6. 계정 PII
계정 식별자(이메일·표시이름·provider account id·아바타 URL) 취급은 **ADR-105 Amendment 1**이 정한다(요지: 마스킹 안 함·`users` 최소 저장·OAuth 토큰 미영속·스코어링 경로 유입 금지).

## 근거
- **OAuth 단순성**: 비밀번호 인증의 저장·해시·복구·유출 대응 비용을 외부 provider에 위임. 신뢰 게이트(GS-1/2)와 직교한 보안 표면을 최소화.
- **persona 정합**: GitHub은 개발자 구직자의 기본 자산, Google은 보편 — 가입 마찰 최소.
- **쿠키 세션**: SSR Next.js에서 자연스럽고 토큰 탈취면이 작다.
- **멀티유저는 실서비스·후속 검증의 전제**: A-6(외부 시장 검증)·GS-3(실 결과 데이터) 모두 사용자별 데이터가 필요(M6 배포 후 트랙).

## 결과
- Charter §5/§2.1·§7 + DISCOVERY 멀티유저 비범위 항목을 snapshot sync(범위 변경 명시).
- `users` 테이블 + 전 user-facing 쿼리에 user 범위 인가 추가.
- ADR-105 Amendment 1(계정 PII) 동반.
- ARCH §7-1 인증 "미정" → "OAuth(GitHub·Google) + httpOnly 쿠키 세션" 확정.

## Surfaces
- [PROJECT_CHARTER §5](../../10-charter/PROJECT_CHARTER.md) (멀티유저 비목표 → 반전 명시) · §2.1·§7.
- [ARCHITECTURE_OVERVIEW §7-1](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (인증 확정) · §7-3(인증).
- [DISCOVERY §8](../../10-charter/DISCOVERY.md) (멀티유저 비범위 항목 — 범위 변경 backref).

## 후속 작업
- **F-016 (oauth-and-multiuser)** 이 본 ADR을 구현한다.
- DISCOVERY/Charter 본문 sync는 `/bootstrap-project --apply` 또는 수동(ADR-035 — DISCOVERY=SSOT).

## 관련 문서
- [M4-product-mvp](../../30-workitems/milestones/M4-product-mvp.md) (§1·§2 멀티유저)
- [ADR-105](ADR-105-pii-masking-policy.md) (Amendment 1 — 계정 PII) · [ADR-106](ADR-106-worker-trigger-boundary.md) (멀티유저 동시 채점 트리거)
- [ADR-101](ADR-101-stack-selection.md) (스택 — 인증 "미정" 해소)
