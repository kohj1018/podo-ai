# F-024-aws-infra-provisioning: AWS 인프라 프로비저닝 (RDS+pgvector · SQS · 시크릿)

## 0. Status
draft

> **잠정 (M6 — `/plan-workitem M6` 진입 전 확정).** 사용자가 AWS 콘솔/시크릿에서 직접 수행하는 부분 포함.

## 0-1. Type
technical-enabler

## 1. 요약
LocalStack→AWS 이전. **RDS(Postgres+pgvector)**, **AWS SQS**(F-017 엔드포인트만 교체), **시크릿 매니저**(`OPENAI_API_KEY`·`DATABASE_URL`·OAuth secret 등 `.env`→관리형), 네트워킹/보안그룹, IaC(`infra/aws/`). 코드 경로는 M4/M5와 동일(엔드포인트·자격증명만 환경별 주입).

## 2. 기술적 근거 (Technical rationale)
**무엇을:** M4/M5에서 LocalStack이 대역하던 AWS(SQS)와 로컬 docker compose Postgres를 **실제 AWS로 이전**한다 — RDS Postgres+pgvector, 실 SQS, 시크릿 매니저, 네트워킹. 가정 A-INFRA("실물 AWS 이전은 나중에")를 닫는다.
**서비스하는 결정:** ADR(가칭, AWS 호스팅 방식 — M6) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) D-DEPLOY/A-INFRA · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)(SQS 엔드포인트 교체).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. IaC로 RDS+pgvector·SQS·시크릿·네트워킹 프로비저닝(사용자 콘솔 작업 포함).
2. `prisma migrate deploy`로 RDS 스키마 적용(pgvector extension·HNSW 포함).
3. 시크릿 주입 → 서비스가 실 AWS 자원에 연결.
### Fail path
1. 🔴 시크릿 미주입/오류 → 기동 실패(명확한 에러, 시크릿 미커밋).
2. 🔴 RDS pgvector extension 미가용 → 마이그레이션 실패 가시화.

## 4. 범위
- RDS Postgres + pgvector(extension·HNSW는 Prisma migration raw SQL — DDL SSOT).
- AWS SQS(채점 큐, F-017 동일 코드).
- 시크릿 매니저 + 환경별 주입(`.env` 커밋 금지 — AGENTS.md).
- 네트워킹/보안그룹/IAM 최소 권한.
- IaC(`infra/aws/`) + 환경(staging/prod) 구분.

## 5. 비범위
- **S3/오브젝트 스토리지 — 미사용**: `.txt`/paste만(PDF 제외)이라 바이너리 저장 없음 + 공유 LLM 캐시는 **Postgres**(F-027, ARCH §7-3). 바이너리 저장 도입 시에만 bucket/KMS/IAM/FAC 추가.
- 멀티리전·오토스케일·고가용 — MVP 단일 리전 최소.
- 새 기능 — M4/M5 완성분.
- 호스팅 실행 자체 — F-025(본 feature는 자원 프로비저닝).

## 6. 요구사항
- pgvector DDL은 Prisma(ARCH §3-2) — RDS에서도 동일.
- 시크릿 미커밋, 최소 권한 IAM.
- LocalStack→AWS 코드 경로 동일(엔드포인트·자격증명만).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** RDS(Postgres+pgvector)가 프로비저닝되고 `prisma migrate deploy`가 extension·인덱스 포함 green이다.
- **FAC-2:** AWS SQS가 생성되고 F-017 코드가 엔드포인트 교체만으로 enqueue/consume한다.
- **FAC-3:** 시크릿이 매니저에서 주입되고 저장소에 미커밋이다.
- **FAC-4:** IaC(`infra/aws/`)로 환경이 재현 가능하게 정의된다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-082:AC-1, T-082:AC-2
- FAC-2 → T-082:AC-1
- FAC-3 → T-082:AC-3
- FAC-4 → T-083:AC-1, T-083:AC-3

## 8. Non-functional Requirements
- 보안: 최소 권한·시크릿 관리·전송 암호화.
- 비용: MVP 최소 인스턴스. 운영성: 자원 상태 가시화.

## 8-1. UX 흐름 품질
(해당 없음 — 인프라.)

## 9. 엣지 케이스
- pgvector 버전·RDS 파라미터 그룹 호환.
- 마이그레이션 롤백 경로.
- 시크릿 로테이션.

## 10. 의존성
- 상위: ADR(AWS 호스팅 — M6)·ADR-101·ADR-106.
- 후행: F-025(호스팅)·F-027(공유 캐시·보안).

## 11. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 A-INFRA, §6 RDS/SQS)
- Architecture-Iface: [ARCH ## 7-3 백엔드/인프라](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)

## 12. 열린 질문 (논의 전제)
- RDS 인스턴스 크기·pgvector 파라미터.
- IaC 도구(Terraform vs CDK vs SST) — 단순성/사용자 친숙도.
- 환경(staging) 둘지 prod 단일로 시작할지.
