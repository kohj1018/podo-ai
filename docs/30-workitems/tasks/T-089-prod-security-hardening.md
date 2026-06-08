# T-089-prod-security-hardening

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
공개 배포 환경 보안 baseline을 구현한다 — PII at-rest 암호화 + 간접 재식별 방어 경계(ADR-105 Amend1 M6 이연분) + 의존성 보안 bump + 시크릿/보안 헤더/레이트리밋. F-027 FAC-2·3·4 커버.

## 2. 작업 범위
- **PII at-rest 암호화**: `resumes.content`(마스킹본)·`users` 계정 식별자 저장 보호(RDS 암호화 or 컬럼 암호화). raw PII 미영속·계정 PII 스코어링 경로 미유입(M3/M4 불변식) 배포 환경 보존.
- **간접 재식별 방어 경계**: 직접 식별자 외 학교+회사+기간 조합의 역추적 방어 경계 결정·적용(과마스킹과 GS-2 균형 — evidence 보존). ADR-105 Amend1 M6 이연분.
- **의존성 bump**: `next`≥15.5.16 + NestJS 갱신 후 `pnpm audit --prod` high 0 확인(M2부터 이연 부채). pip-audit clean 유지.
- **시크릿/헤더/레이트리밋**: 시크릿 미커밋(F-024 정합) + 보안 헤더(CSP/HSTS 등) + 기본 레이트리밋.
- **public subnet / NAT 없음 accepted-risk 명문화 (ADR-109 D2/D4)**: NAT 미사용 비용 절감 대가로 api/worker가 public subnet(public IP) — *의식적 비용/보안 트레이드오프*. 보상책을 보안 baseline에 기록: ① SG inbound 최소화(api=ALB source만·worker=ingress 없음), ② RDS private(절대 public 금지), ③ 시크릿=Secrets Manager, ④ 노출면=ALB+api로 한정. 트래픽·민감도 상승 시 NAT+private subnet 또는 VPC endpoint로 승격(후속).

## 3. 구현 항목
1. RDS at-rest 암호화 설정(IaC) + 필요 시 민감 컬럼 암호화. → 확인: 설정 검증 + PII 불변식 scan (AC-1)
2. 간접 재식별 방어 경계 문서·적용(어느 조합까지 마스킹/익명화). → AC-1 포함.
3. `next`≥15.5.16 + NestJS bump + `pnpm audit --prod`. → 확인: audit high 0 (AC-2)
4. 보안 헤더 미들웨어 + 레이트리밋 + 시크릿 미커밋 grep. → 확인: header 응답·grep (AC-3)

## 4. 제외 항목
- 공유 LLM 캐시 어댑터 — T-088 소관.
- 침투 테스트·정식 보안 감사 — MVP baseline 범위 밖.
- WAF·DDoS 고급 방어 — 후속.

## 4-1. 변경 예정 파일/경로
- `infra/aws/main.tf` — RDS `storage_encrypted = true`(PII at-rest 암호화)
- `podo/apps/web/package.json` — `next` ^14.2.0 → ^15.5.16(5개 next high 해소)
- `podo/apps/web/app/layout.tsx`·`app/login/page.tsx` — Next 15 async API 마이그레이션(`await cookies()`·async `searchParams`)
- `podo/apps/web/next-env.d.ts` — next 15 자동 재생성(auto-gen)
- `pnpm-workspace.yaml` — `overrides.multer: ^2.1.1`(multer high×3 정밀 해소, NestJS major bump 회피) + `sharp: false`(ignored-build 에러 해소)
- `podo/apps/api/package.json` — `helmet`·`express-rate-limit` 런타임 + `express`·`@types/express` devDep(security 테스트용)
- `podo/apps/api/src/main.ts` — `helmet()` 보안 헤더 + `express-rate-limit` 레이트리밋
- `podo/apps/api/test/security.spec.ts` (신규) — AC-3 보안 헤더·레이트리밋 테스트(`vitest run security` 매칭)
- `pnpm-lock.yaml` — dep 해소 결과
- `docs/90-decisions/project/ADR-105-pii-masking-policy.md` — Amendment 2(간접 재식별 경계 확정)

## 5. 완료 조건
배포 환경에서 PII at-rest 암호화 + 간접 재식별 경계가 적용되고, dep audit high 0이며, 시크릿 미커밋 + 보안 헤더/레이트리밋 baseline이 충족된다.

## 6. Acceptance Criteria
- AC-1 [Given] 배포 환경 + 마스킹/계정 PII 저장 [When] at-rest 암호화 설정 + 하류 표면 PII scan [Then] RDS 암호화가 활성이고 raw PII 미영속·계정 PII 스코어링 경로 미유입이 유지되며, 간접 재식별 방어 경계가 문서·적용된다.
- AC-2 [Given] `next`≥15.5.16 + NestJS bump [When] `pnpm audit --prod` [Then] high severity 0이고 pip-audit도 clean이다.
- AC-3 [Given] 배포 api [When] 응답 헤더 검사 + `git grep` 시크릿 [Then] 보안 헤더(예: HSTS) + 레이트리밋이 적용되고 시크릿 실값 커밋이 0건이다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `pytest scripts/e2e_account_pii_scan.py`(하류 표면 PII 0) + IaC 암호화 설정 검증
- AC-2 → `pnpm audit --prod`(high 0) + `uvx pip-audit`
- AC-3 → `curl -I <api>/health`(보안 헤더 포함) + `git grep -rn "sk-\|AKIA" -- ':!*.example' ':!docs/'` 매칭 0

## 6-2. TDD opt-out
- 사유: 인프라/의존성 보안 task라 단위 TDD보다 설정 검증·`pnpm audit`·헤더 검사가 Red→Green 기준에 적합(코드 단위 로직 최소).
- Follow-up task: PII 하류 표면 scan은 T-040/T-052의 literal-scan 패턴 재사용(별도 follow-up task 불요).

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-027-shared-cache-and-hardening](../features/F-027-shared-cache-and-hardening.md)
- Architecture: [ARCH §8 보안](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1)(보안 헤더·레이트리밋), [## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1) (간접 재식별→M6) · [ADR-109](../../90-decisions/project/ADR-109-aws-hosting-topology.md)(public subnet/no-NAT accepted-risk)

## 8. 메모
- 의존성 bump는 M2 [Dependency] P1이 M2→M3→M4 이연된 부채 — M6에서 청산.
- 간접 재식별: 과마스킹은 grounding/GS-2 약화 → evidence(학교·회사·기간) 보존과 균형.
- public subnet/no-NAT는 ADR-109 결정 — 본 task가 **accepted-risk로 명문화**(보상: SG·private RDS·Secrets Manager). 침투 노출면은 ALB+api로 한정. 데이터 가치·트래픽 상승 시 재평가.

## 9. 의존성
- depends_on: [T-082, T-088]
- read_set: ["infra/aws/", "podo/apps/api/src/main.ts", "podo/apps/*/package.json"]
- write_set: ["infra/aws/", "podo/apps/api/src/main.ts", "podo/apps/web/package.json", "podo/apps/api/package.json"]
- assumptions: ["T-082 RDS 프로비저닝", "T-088 캐시 어댑터(PII 경로 정합)"]
- verifier: "pnpm audit --prod && pnpm --filter api test security"
