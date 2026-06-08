# T-084-gha-deploy-workflows

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
GitHub Actions `deploy-api`·`deploy-worker` 워크플로를 실가동한다. T-019가 skeleton(no-op)으로 만든 파일을 실 AWS 호스팅 배포 로직으로 채운다. **pre-deploy 게이트 = `schema-contract`(배포 URL 불요)** green일 때만 배포 진행. **post-deploy `e2e-smoke`는 T-086이 소유**(실 URL 필요 — 순환 차단: deploy는 schema-contract만 선행). api·worker = AWS 호스팅(**M6 기본: Terraform + ECS/Fargate** — SQS 상시 consumer 정합. 변경 시 AWS 호스팅 ADR + §3/verifier 갱신). [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(D-DEPLOY) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)(SQS consumer 상시).

## 2. 작업 범위
- `.github/workflows/deploy-api.yml` 실가동: main 머지 → schema-contract·e2e-smoke 게이트 → api(NestJS) AWS 호스팅 배포(이미지 빌드+push, 서비스 업데이트).
- `.github/workflows/deploy-worker.yml` 실가동: main 머지 → 게이트 → worker(Python consumer) AWS 호스팅 배포. **단일 worker 인스턴스 시작**(다중화는 F-027/F-027 후속(미분해)).
- `schema-contract`·`e2e-smoke` 게이트 step이 deploy job의 선행 조건으로 연결.
- AWS 배포 자격증명(OIDC 또는 IAM key)은 GitHub Secrets에서 주입(커밋 금지).
- 배포 실패 시 자동 롤백 step 또는 명확한 실패 알림.

## 3. 구현 항목
1. `.github/workflows/deploy-api.yml` — 현재: no-op skeleton(T-019) → 변경: `on: push: branches: [main]` + `permissions: { id-token: write, contents: read }`(OIDC) + `jobs.gate`(schema-contract `needs`) + `jobs.deploy`: **`aws-actions/configure-aws-credentials@v6`**(role-to-assume OIDC) → `aws-actions/amazon-ecr-login` → 도커 빌드/push → `aws-actions/amazon-ecs-render-task-definition`(이미지 태그 주입) → `aws-actions/amazon-ecs-deploy-task-definition@v2`. → 확인: `actionlint .github/workflows/deploy-api.yml` exit 0. (AC-1)
2. `.github/workflows/deploy-worker.yml` — 현재: no-op skeleton → 변경: 위와 동일 패턴, worker Python 이미지 빌드 + 단일 ECS task/service 배포(상시 SQS consumer) → 확인: `actionlint` exit 0. (AC-1)
3. GitHub Secrets 설정 문서화(사용자 수행) — `AWS_ROLE_ARN`(OIDC 권장)·`ECR_REGISTRY`·`ECS_CLUSTER`·`ECS_SERVICE_API`·`ECS_SERVICE_WORKER`를 저장소 Secrets에 등록. → 확인: workflow에 `${{ secrets.AWS_ROLE_ARN }}` 참조 존재 + 실값 미커밋. (AC-2)
4. `.github/workflows/deploy-api.yml` rollback step — 현재: 없음 → 변경: `if: failure()` 조건 step에서 이전 task definition revision으로 ECS update-service(또는 동등) → 확인: step이 workflow 파일에 존재. (AC-1)
5. **pre-deploy 게이트 배선** — deploy-api/worker job의 `needs`에 **schema-contract**(URL 불요) green을 선행 조건으로 둔다. **post-deploy `e2e-smoke.yml`는 본 task가 소유하지 않음**(T-086 소유 — 실 URL 대상). → 확인: deploy job에 schema-contract gate `needs` 존재 + e2e-smoke.yml 미소유. (AC-3)

## 4. 제외 항목
- crawler 배포 — crawler = GitHub Actions cron(T-085), AWS 서비스 아님.
- web 배포 — F-026/T-087(Vercel, 사용자 직접).
- 다중 worker 인스턴스·오토스케일 — F-027/F-027 후속(미분해).
- blue-green vs rolling 전략 확정 — 열린 질문(단순성 우선 rolling 가정).

## 4-1. 변경 예정 파일/경로
- `.github/workflows/deploy-api.yml` (skeleton → 실 배포 로직, T-084 완료)
- `.github/workflows/deploy-worker.yml` (skeleton → 실 배포 로직, T-084 완료)
- `docs/30-workitems/tasks/T-084-gha-deploy-workflows.md` (이 파일)
- (`e2e-smoke.yml`는 T-086 소유 — 본 task 미변경)

## 5. 완료 조건
main 머지 시 schema-contract·e2e-smoke gate가 green인 조건에서 api·worker가 AWS에 자동 배포되고, 실패 시 롤백 step이 실행된다.

## 6. Acceptance Criteria
- AC-1 [Given] `.github/workflows/deploy-api.yml`·`deploy-worker.yml` [When] `actionlint` [Then] 두 파일 모두 유효하고, `needs: [gate]` 또는 동등한 게이트 선행 조건과 `if: failure()` 롤백 step을 각각 포함한다.
- AC-2 [Given] workflow 파일 전체 [When] `git grep -r "AWS_ACCESS_KEY_ID\|AWS_SECRET_ACCESS_KEY" -- .github/` [Then] 실값이 하드코딩된 행이 0개다(secrets 참조만 허용).
- AC-3 [Given] deploy-api/worker workflow [When] inspection [Then] deploy job의 `needs`에 schema-contract gate(pre-deploy, URL 불요)가 있고 게이트 실패 시 배포가 진행되지 않으며, 본 task가 `e2e-smoke.yml`을 변경/소유하지 않는다(post-deploy smoke=T-086).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `actionlint .github/workflows/deploy-api.yml .github/workflows/deploy-worker.yml` exit 0; `grep -l "if: failure()" .github/workflows/deploy-api.yml` → 파일명 출력
- AC-2 → `git grep -rn "AKIA\|aws_secret" -- .github/` exit 0 (매칭 0)
- AC-3 → `actionlint` + `grep -L "e2e-smoke" .github/workflows/deploy-api.yml` 및 deploy job `needs: [schema-contract]` 존재 확인(inspection)

## 6-2. TDD opt-out
- 사유: GHA workflow는 실 AWS 환경 없이 단위 테스트 불가 — actionlint + 시크릿 grep + 배포 후 e2e-smoke로 대체.
- Follow-up task: T-086(e2e-smoke 전용 task)가 실 배포 환경 최종 검증.

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-025-service-deploy-pipelines](../features/F-025-service-deploy-pipelines.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-3 cron·워커, §6)
- Architecture-Iface: [ARCH ## 7-3 백엔드/워커](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)

## 8. 메모
- 호스팅 방식(ECS/Fargate vs Lambda vs EC2) 미확정 — 사용자 결정 후 §3의 ECS 명령을 실제 방식으로 교체. Lambda는 SQS 상시 consumer 모델에 적합(event source mapping), ECS는 장기 실행 프로세스에 적합.
- OIDC(GitHub→AWS AssumeRole) 권장(long-lived key 회피). **`aws-actions/configure-aws-credentials@v6`**(2026-06 현행 — *v4 아님*) + job `permissions: id-token: write`. ECR=`amazon-ecr-login`, 배포=`amazon-ecs-render-task-definition`→`amazon-ecs-deploy-task-definition@v2`. AWS 계정에 **IAM OIDC identity provider(`token.actions.githubusercontent.com`) + repo/branch sub-claim 제한 AssumeRole 역할**을 사전 생성(T-082 IaC, 사용자 수행).
- worker는 단일 인스턴스(F-025 범위). 다중화는 F-027 후속(미분해)(F-027) 이후.
- repair-workitem 2026-06-09 P1 ci-gate: Adopt — inline `gate` job이 빈 DB에서 `pytest test_schema_contract.py` 실행(migrate 누락) → node/pnpm setup + `prisma migrate deploy` step 추가(deploy-api/worker.yml, schema-contract.yml 패턴 정합). T-086 검증 중 발견.

## 9. 의존성
- depends_on: [T-082, T-083]   # RDS·SQS·IAM이 존재해야 배포 대상 있음
- write_set: [".github/workflows/deploy-api.yml", ".github/workflows/deploy-worker.yml"]
- assumptions: ["T-082/T-083 IaC가 apply됨", "ECR 저장소 존재", "ECS 클러스터/서비스 정의 존재 또는 이 task에서 생성", "GitHub Secrets에 AWS_ROLE_ARN 등 등록됨(사용자 수행)"]
- verifier: "actionlint .github/workflows/deploy-api.yml .github/workflows/deploy-worker.yml"
