# Project ADR Index

> 이 디렉터리는 fork된 프로젝트의 자체 결정 ADR을 박는 영역.
> 첫 ADR은 ADR-100부터 시작 (정책: [boilerplate/ADR-000](../boilerplate/ADR-000-boilerplate-decision-policy.md)).

## ADR 목록

`area`=product/design/dev/infra/process/tooling. `superseded`된 ADR은 상태 컬럼에 표기하고 상단 '대체: ADR-NNN' 링크로 supersession 추적(폴더 이동 X). 연 1회 `last-reviewed` 갱신 권장.

| # | 제목 | 상태 | area | last-reviewed | 한 줄 요약 |
|---|------|------|------|---------------|-----------|
| [100](ADR-100-initial-project-decisions.md) | 초기 프로젝트 결정 (수집+fit/합격가능성 SaaS) | accepted | product | 2026-06-04 | 신뢰 게이트 우선(D1) · 4-layer 미채택/모듈 의존성 규칙(D2) · 결정론 캐시로 GS-1 보증(D3) |
| [101](ADR-101-stack-selection.md) | 스택 선택 (폴리글랏 모노레포 — TS web/api + Python worker/crawler) | accepted | infra | 2026-06-04 | 폴리글랏 TS+Python(D-LANG) · turbo는 podo/만/uv workspace 분리(D-MONO) · Prisma SSOT+DDL/DML 분리(D-DB) · 계약 3규칙으로 R6 가드(D-CONTRACT) |
| [102](ADR-102-python-test-layout.md) | Python 테스트 레이아웃 + 검증 설정 컨벤션 | accepted | tooling | 2026-06-05 | co-located 패키지 테스트 + 중앙 foundational(D1) · test 디렉터리 `__init__.py` 없음+importlib(D2) · mypy strict는 test 제외(D3) · ruff E501 test 제외(D4) · 구현 src-layout(D5) |
