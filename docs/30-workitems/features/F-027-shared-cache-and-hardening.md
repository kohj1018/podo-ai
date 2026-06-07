# F-027-shared-cache-and-hardening: 공유 LLM 캐시 이전 + 공개 환경 보안

## 0. Status
draft

> **잠정 (M6).**

## 0-1. Type
technical-enabler

## 1. 요약
`worker/cache.py`의 `CacheAdapter`(인터페이스 이미 존재) 위에 **Postgres 공유 캐시 어댑터**를 구현해 디스크 캐시를 교체한다(동일 캐시 키 — GS-1 보존, S3 미사용). 동시에 공개 환경 보안 baseline: PII at-rest 암호화·**간접 재식별 방어**(직접 식별자 외 학교+회사+기간 조합, ADR-105 Amend1로 M6 이연분)·시크릿 관리·보안 헤더/레이트리밋·**의존성 bump**(`next`≥15.5.16 + NestJS — M2부터 이연된 부채).

## 2. 기술적 근거 (Technical rationale)
**무엇을:** ① 디스크 LLM 캐시(`.cache/llm`, 로컬·단일프로세스)를 **Postgres 공유 저장소**로 이전(ARCH §7-3 — S3 미사용) — M6에서 worker 다중 인스턴스 시 재현성·캐시 적중이 깨지므로(코드 감사 확인: 디스크 캐시 멀티인스턴스 비공유). ② 공개 노출에 맞춘 보안 하드닝(암호화·간접 재식별·시크릿·의존성 bump).
**서비스하는 결정:** [ARCH §7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)("동일 키로 Postgres JSONB 어댑터 교체") · [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1)(간접 재식별→M6).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. worker 다중 인스턴스가 공유 캐시(Postgres)를 조회 → 동일 입력 동일 결과(GS-1, 인스턴스 무관).
2. 공개 환경에서 PII·시크릿·의존성 보안 baseline 충족.
### Fail path
1. 🔴 공유 캐시 장애 → cache miss로 재계산(가용성 저하이나 정확도 유지).
2. 🔴 의존성 취약점 잔존 → audit 게이트 fail.

## 4. 범위
- `CacheAdapter` **Postgres** 구현(ARCH §7-3 "동일 키로 Postgres JSONB 어댑터 교체" — S3 미사용) + 디스크 캐시 교체(동일 키 — GS-1). *S3는 바이너리 저장(.txt/paste·PDF 제외라 없음)이 생기기 전엔 미도입.*
- PII at-rest 암호화(마스킹본·계정 PII 저장 보호).
- 간접 재식별 방어 경계 결정·적용(ADR-105 Amend1 M6 이연분).
- 시크릿 관리·보안 헤더·레이트리밋.
- 의존성 bump(`next`≥15.5.16 + NestJS) + 재audit clean.

## 5. 비범위
- 새 기능·알고리즘 — M4/M5.
- 캐시 무효화 정책 전면 재설계 — 버전 핀 유지(M5 출력계약 동결).

## 6. 요구사항
- 공유 캐시는 동일 캐시 키(GS-1 보존) — 어댑터 교체만(ARCH §7-3).
- raw PII 미영속(M3 불변식) + 계정 PII 스코어링 경로 미유입(ADR-105 Amend1) 공개 환경에서도 유지.
- dep audit clean(pnpm high 0).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 디스크 캐시가 Postgres 공유 어댑터로 교체되고, 동일 입력이 worker 인스턴스와 무관하게 동일 결과를 반환한다(GS-1 멀티인스턴스).
- **FAC-2:** PII at-rest 암호화 + 간접 재식별 방어 경계가 적용되고 raw/계정 PII 불변식이 공개 환경에서 유지된다.
- **FAC-3:** `next`≥15.5.16 + NestJS bump 후 dep audit가 clean(high 0)이다.
- **FAC-4:** 시크릿 미커밋 + 보안 헤더/레이트리밋 baseline 충족.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-088:AC-1, T-088:AC-2
- FAC-2 → T-089:AC-1
- FAC-3 → T-089:AC-2
- FAC-4 → T-089:AC-3

## 8. Non-functional Requirements
- 신뢰성: 공유 캐시 GS-1 보존. 보안: 암호화·시크릿·audit.
- 가용성: 캐시 장애 시 graceful(재계산 fallback).

## 8-1. UX 흐름 품질
(해당 없음 — 인프라/보안.)

## 9. 엣지 케이스
- 캐시 마이그레이션(디스크→공유) 중 키 호환.
- 간접 재식별 방어가 evidence(학교·회사·기간)를 과마스킹 → GS-2 약화 균형.
- dep bump 호환성 회귀(e2e-smoke 게이트).

## 10. 의존성
- 선행: F-024(Postgres)·F-017(캐시 사용 worker)·**F-025(단일 worker 배포 — 본 feature가 그 위에서 공유 캐시→다중화)**. F-025↔F-027 순환 제거(F-025가 선행, F-027 후행).
- 상위: ARCH §7-3 · ADR-105 Amend1.

## 11. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-3 캐시 어댑터, §8 보안)
- Architecture-Iface: [ARCH ## 7-3 백엔드/캐시](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 12. 열린 질문 (논의 전제)
- 공유 캐시 저장소 = Postgres JSONB vs S3(비용·지연·키 수).
- 간접 재식별 방어 강도(과마스킹 vs GS-2 균형).
- 캐시 무효화/마이그레이션(모델·프롬프트·임베딩 버전 변경 시).
