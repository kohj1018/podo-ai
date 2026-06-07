"""T-066: 이력서 도메인 자동 분류기 (결정적, LLM 호출 0).

EvidenceItem.domain 빈도 집계(1차) + SKILL_DOMAIN_RULES 사전 보강(2차)으로
primary_domains / secondary_domains / confidence를 반환한다.

GS-1 정합: CLASSIFIER_VERSION 핀 — 사전 변경 시 bump + 재분류.
다의어(python/java/typescript/go/sql)·kotlin은 문맥 의존이므로 규칙 제외.
§8 확정본: ROLE_FAMILY_TO_DOMAINS 토큰 재사용, 새 어휘 신설 금지.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from core.models import EvidenceItem

CLASSIFIER_VERSION = "v1"

# 결정적 스킬→직군 규칙 사전 (§2 Step-2 확정본).
# 다의어(python/java/typescript/go/sql)·kotlin 제외.
# 값은 ROLE_FAMILY_TO_DOMAINS 토큰 어휘만 사용(새 어휘 신설 금지 — §8).
SKILL_DOMAIN_RULES: dict[str, str] = {
    # frontend
    "react": "frontend",
    "next.js": "frontend",
    "vue": "frontend",
    "angular": "frontend",
    "svelte": "frontend",
    "tailwind": "frontend",
    "redux": "frontend",
    "webpack": "frontend",
    # backend
    "spring": "backend",
    "django": "backend",
    "fastapi": "backend",
    "flask": "backend",
    "express": "backend",
    "nestjs": "backend",
    "rails": "backend",
    "laravel": "backend",
    "grpc": "backend",
    # data
    "pandas": "data",
    "numpy": "data",
    "spark": "data",
    "airflow": "data",
    "dbt": "data",
    "kafka": "data",
    "hadoop": "data",
    "bigquery": "data",
    "etl": "data",
    # ml_ai
    "pytorch": "ml_ai",
    "tensorflow": "ml_ai",
    "scikit-learn": "ml_ai",
    "hugging face": "ml_ai",
    "llm": "ml_ai",
    "nlp": "ml_ai",
    "mlops": "ml_ai",
    "keras": "ml_ai",
    # mobile: android
    "android": "android",
    "jetpack compose": "android",
    # mobile: ios
    "swift": "ios",
    "swiftui": "ios",
    "uikit": "ios",
    "objective-c": "ios",
    # mobile: cross-platform
    "flutter": "mobile",
    "react native": "mobile",
    # devops
    "docker": "devops",
    "kubernetes": "devops",
    "terraform": "devops",
    "ansible": "devops",
    "ci/cd": "devops",
    "jenkins": "devops",
    "github actions": "devops",
    "prometheus": "devops",
    # cloud
    "aws": "cloud",
    "gcp": "cloud",
    "azure": "cloud",
    # infra
    "nginx": "infra",
    "linux": "infra",
    # security
    "owasp": "security",
    "penetration testing": "security",
    "siem": "security",
    "cryptography": "security",
}

# web → frontend 흡수 (§8: ROLE_FAMILY_TO_DOMAINS에서 web이 frontend 소속).
_DOMAIN_NORMALIZE: dict[str, str] = {"web": "frontend"}


@dataclass(frozen=True)
class DomainResult:
    primary_domains: list[str] = field(default_factory=list)
    secondary_domains: list[str] = field(default_factory=list)
    confidence: str = "low"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DomainResult):
            return NotImplemented
        return (
            sorted(self.primary_domains) == sorted(other.primary_domains)
            and sorted(self.secondary_domains) == sorted(other.secondary_domains)
            and self.confidence == other.confidence
        )

    def __hash__(self) -> int:
        return hash(
            (
                tuple(sorted(self.primary_domains)),
                tuple(sorted(self.secondary_domains)),
                self.confidence,
            )
        )


def _normalize_domain(d: str) -> str:
    """web → frontend 흡수 등 도메인 정규화."""
    return _DOMAIN_NORMALIZE.get(d.lower(), d.lower())


def classify_domains(evidence_items: list[EvidenceItem]) -> DomainResult:
    """evidence_items 에서 primary/secondary 도메인과 confidence를 결정적으로 반환.

    Step 1: EvidenceItem.domain 값 빈도 집계.
    Step 2: 스킬 신호 빈약 시 SKILL_DOMAIN_RULES로 보강.
    결정성: 동일 입력 → 동일 출력 (CLASSIFIER_VERSION 핀).
    """
    domain_counter: Counter[str] = Counter()

    # Step 1: evidence.domain 집계
    for item in evidence_items:
        for d in item.domain:
            normalized = _normalize_domain(d)
            if normalized:
                domain_counter[normalized] += 1

    # Step 2: 스킬 신호 보강 (evidence.domain 빈약 시)
    skill_counter: Counter[str] = Counter()
    for item in evidence_items:
        for skill in item.skills:
            mapped = SKILL_DOMAIN_RULES.get(skill.lower())
            if mapped:
                skill_counter[mapped] += 1

    # domain_counter가 빈약하면 skill_counter로 보강
    if not domain_counter and skill_counter:
        domain_counter = skill_counter
    elif skill_counter:
        # 두 신호를 합산하되 domain 신호가 더 강한 가중치 (2:1)
        combined: Counter[str] = Counter()
        for d, cnt in domain_counter.items():
            combined[d] += cnt * 2
        for d, cnt in skill_counter.items():
            combined[d] += cnt
        domain_counter = combined

    if not domain_counter:
        return DomainResult(
            primary_domains=["unknown"],
            secondary_domains=[],
            confidence="low",
        )

    # 빈도 내림차순 정렬 (결정성: 동점 시 알파벳 순 보조 정렬)
    sorted_domains = sorted(domain_counter.items(), key=lambda x: (-x[1], x[0]))
    top_count = sorted_domains[0][1]

    # primary: 최다 빈도와 동점인 모든 도메인
    primary = [d for d, cnt in sorted_domains if cnt == top_count]

    # secondary: primary 다음 빈도 그룹
    secondary_candidates = [(d, cnt) for d, cnt in sorted_domains if cnt < top_count]
    secondary: list[str] = []
    if secondary_candidates:
        second_count = secondary_candidates[0][1]
        secondary = [d for d, cnt in secondary_candidates if cnt == second_count]

    # confidence 결정
    total_signals = sum(domain_counter.values())
    if total_signals == 0:
        confidence = "low"
    elif len(primary) >= 2:
        # 여러 도메인이 동점 → 혼재 신호
        confidence = "medium"
    elif total_signals >= 3:
        confidence = "high"
    else:
        confidence = "medium"

    return DomainResult(
        primary_domains=primary,
        secondary_domains=secondary,
        confidence=confidence,
    )
