# M6-deployment

## 0. Status
draft

> **잠정 초안.** M5 졸업 후 `/plan-workitem M6` 진입 전에 갱신·확정한다. **사용자가 웹/콘솔에서 직접 수행해야 하는 부분(Vercel 배포·AWS 콘솔·시크릿 주입·도메인)은 사용자가 진행**(사용자 판단 2026-06-07).

## 1. 목적
M4(멀티유저 MVP)·M5(커버리지·알고리즘 강화)가 로컬 docker compose(LocalStack로 AWS 대역)에서 완성된 제품을, **최초 설계한 아키텍처대로 실제 배포 환경에 올려 동작**시킨다 — api/worker/crawler는 AWS, 프론트는 Vercel, 크롤러·CI/CD는 GitHub Actions. [ARCH §3-2](../../20-system/ARCHITECTURE_OVERVIEW.md)가 "*나중에*"로 둔 인프라 실물 이전(LocalStack → AWS, 가정 A-INFRA)을 닫고, **매일 오전 크롤 cron 실가동**을 켠다. 결정론(GS-1)·grounding(GS-2)·데이터 격리·PII 불변식은 배포 환경에서도 보존된다.

> **알림 *기능*(이메일/푸시)은 M6 비범위 — 나중.** M6은 **매일 오전 크롤링 cron job만** 구현한다(신규/마감 diff 자동 갱신). "신규 N건 도착"을 사용자에게 *발송*하는 이메일/푸시 채널 자체는 후속 마일스톤. (사용자 판단 2026-06-07.) Charter §8 흐름1의 알림 약속·Fail #1(알림 미수신=치명) 완화는 알림 기능 도입 시점으로 이연.

## 2. 범위 (잠정)
- **인프라 실물 이전 (A-INFRA)** — Postgres+pgvector → **AWS RDS**(또는 관리형 PG+pgvector), **LocalStack SQS → 실제 AWS SQS**, 시크릿 관리(`OPENAI_API_KEY`·`DATABASE_URL` 등 `.env`→시크릿 매니저). **S3는 미사용**(바이너리 저장 없음 + 공유 LLM 캐시 = Postgres, F-027) — 바이너리 저장 도입 시 재검토.
- **호스팅** — api/worker/crawler를 AWS에(ECS/Fargate vs Lambda vs EC2 — ADR로 확정). 프론트는 **Vercel(사용자 직접 배포)**. web→api 도메인·CORS·환경변수(`NEXT_PUBLIC_API_BASE_URL`) 실값 결선.
- **CI/CD + cron 실가동** — GitHub Actions `deploy-api`·`deploy-worker`·`crawl-jobs`·`schema-contract`·`e2e-smoke` 실가동. **`crawl-jobs` 매일 오전 cron**으로 신규/마감 diff 자동 갱신(M4가 UI만 준비한 그 트리거를 실제로 켬). *알림 발송 기능은 비범위(§1).*
- **공개 환경 PII/보안** — raw PII는 여전히 미영속(마스킹본 only)이되, 공개 노출에 맞춰 **at-rest 암호화·간접 재식별 방어 경계(M3에서 M4로, M4에서 여기로 이연)·접근통제 재점검·보안 헤더/레이트리밋**. 의존성 보안 부채(`next`≥15.5.16 + NestJS bump — M2부터 이연) 청산.
- **운영성** — 크롤 실패율·캡차율·채점 큐 지연 로깅/알람, 캐시 무효화(모델/프롬프트 버전 변경) 추적.
- **공유 LLM 캐시 이전** — 디스크 `.cache/llm`(로컬·단일프로세스)을 **Postgres/S3 공유 저장소**로 이전(ARCH §7-3 "동일 키로 JSONB 어댑터 교체"). 멀티 worker 인스턴스에서 재현성·캐시 적중을 보존(워커 트리거 큐화 ADR-106과 같은 이유).

## 3. 포함되는 기능 (F-024 ~ F-027, 잠정)
> feature 초안 작성됨(메인세션 plan 대행, task 분해 X). 배포 세부는 M6 진입 시 확정.
- **F-024 (aws-infra-provisioning)** — RDS(Postgres+pgvector)·AWS SQS·시크릿·네트워킹 + IaC(`infra/aws/`).
- **F-025 (service-deploy-pipelines)** — api/worker/crawler 호스팅 + GHA deploy + **매일 오전 크롤 cron 실가동**(알림 발송 X).
- **F-026 (web-deploy-wiring)** — Vercel web 배포(사용자 직접) + 도메인/CORS/OAuth redirect.
- **F-027 (shared-cache-and-hardening)** — 디스크 LLM 캐시→Postgres/S3 공유 어댑터 + 공개 보안(암호화·간접 재식별·시크릿·dep bump).

## 3-1. 실행 wave (task `depends_on` 파생 — repair-plan round 2 재산출, 2026-06-07)
> task `## 9 depends_on`이 SSOT, 본 wave는 그 파생 스냅샷. 같은 wave 내 task는 병렬 가능. (repair-plan M6 round 2의 의존성 변경 — T-084/T-086 e2e-smoke 순환 해소·T-088 deps T-085→T-084 — 반영.)
- **Wave 1**: `T-082`(RDS+pgvector·SQS·Secrets 프로비저닝) — 선두, 선행 없음.
- **Wave 2**: `T-083`(IaC 네트워킹·IAM) — `[T-082]`.
- **Wave 3**(병렬): `T-084`(api·worker AWS 배포 workflow + pre-deploy schema-contract gate) · `T-085`(crawl-jobs 매일 오전 cron 실가동) — 둘 다 `[T-082, T-083]`.
- **Wave 4**(병렬): `T-087`(Vercel web 결선·CORS·OAuth redirect, `[T-084]`) · `T-088`(Postgres 공유 LLM 캐시 어댑터, `[T-082, T-084]`).
- **Wave 5**(병렬): `T-086`(배포 환경 E2E smoke·격리 — e2e-smoke.yml 소유, `[T-084, T-087]`) · `T-089`(공개 보안 하드닝: PII 암호화·간접 재식별·dep bump·헤더, `[T-082, T-088]`).
>
> 임계 경로: T-082 → T-083 → T-084 → T-087 → T-086 (5 wave). F-025(배포 T-084/085/086) → F-027(캐시·하드닝 T-088/089) 일방향 순서 보존(T-084 Wave3 ≺ T-088 Wave4). **사용자 직접 수행 단계**(AWS 콘솔·Vercel·시크릿·OAuth redirect 등록)는 각 task 내 명시 — wave는 그 위 검증(스모크·actionlint·schema-contract)만 자동.

## 4. 제외되는 기능 (잠정)
- 새 제품 기능 — M4/M5에서 완성. M6은 *배포·운영*만.
- 새 페르소나/협업 — Charter §5 / DISCOVERY §13.

## 5. 완료 기준 (graduation checklist, 잠정)
- [ ] 모든 task status: done
- [ ] **배포 환경 E2E** — 실제 배포 URL에서 회원가입 → 이력서 업로드 → 채점 → 피드 렌더가 멀티유저로 동작.
- [ ] **cron 실가동** — `crawl-jobs`가 매일 오전 자동 수집 + diff 갱신, 커버리지 패널에 마지막 성공 시각 반영.
- [ ] **게이트/격리/PII 보존** — 배포 환경에서 GS-1 변동 0 · GS-2 ≤2% · 사용자 간 데이터 격리 · raw PII 미영속.
- [ ] **보안 baseline** — dep audit(next/NestJS) clean · 시크릿 미커밋 · 기본 접근통제/레이트리밋.
- [ ] AC 100% / P0 0.

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§7 제약 — 배포·인증·푸시, §8 흐름1 알림)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 A-INFRA, §6 외부 연동·푸시 채널, §7-3 cron·캐시 어댑터, §7-4 Vercel)
- 선행 마일스톤: [M4-product-mvp](M4-product-mvp.md) · [M5-coverage-and-algorithm](M5-coverage-and-algorithm.md)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(배포/스케줄러) · ADR(가칭, AWS 호스팅 방식) · ADR(가칭, 공유 LLM 캐시 어댑터) — `/plan-workitem M6`에서 신설

## 7. 열린 질문 (잠정)
- **api/worker 호스팅 = Terraform + ECS/Fargate 기본 가정(M6 task §3·verifier 정합)** — SQS 상시 consumer에 적합, crawler=GHA cron. Lambda/EC2로 변경 시 AWS 호스팅 ADR 신설 + 해당 task §3/verifier 갱신(M6-repair 2026-06-07). 비용·콜드스타트는 ADR에서 비교.
- 간접 재식별 방어를 어디까지(공개 배포 시 직접 식별자 외 학교+회사+기간 조합)?
- (이연) 알림 발송 기능(이메일/푸시)은 별도 후속 마일스톤 — 채널·발송 트리거·SLA("오전 첫 진입 전 반영")는 그때 결정.
- 배포 후 트랙: **A-6 외부 인터뷰**(시장 수요 검증 — 이 plan 전체에서 미검증 잔류) + **GS-3 실데이터 수집**(지원 결과 누적)을 M6 안/직후 별도 트랙으로.

## 8. 회고 (stabilize 자동 채움)
- 목표 달성도: <정량/정성 1줄>
- scope creep 사례: <있으면 1줄, 없으면 "없음">
- 비목표(charter §5) 위반 사례: <있으면 1줄>
- 핵심 학습 3개 이내
