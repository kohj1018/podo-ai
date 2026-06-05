"""T-002 core data contract — SPEC §3 enum·모델 + §4-3 domain_alignment.

상수·모델은 SPEC §3 그대로 이식(검증된 캘리브레이션, 임의 변경 금지).
enum 필드는 clamp(mode="before")로 허용값 밖 입력을 default로 클램프,
리스트 필드는 as_list로 정규화한다 (LLM 오출력 방어).
"""

from collections.abc import Iterable
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# §3-1. enum/분류 — Literal 타입 + 런타임 clamp용 집합(Literal에서 파생)
# ---------------------------------------------------------------------------

EvidenceType = Literal[
    "work_experience", "project", "education", "award", "activity", "skills", "other"
]
Strength = Literal["strong", "medium", "weak"]
ReqType = Literal["critical", "required", "preferred", "optional"]
MatchLevel = Literal["direct", "adjacent", "weak", "missing"]
Confidence = Literal["high", "medium", "low"]
RoleFamily = Literal[
    "frontend",
    "backend",
    "fullstack",
    "android",
    "ios",
    "data",
    "ml_ai",
    "devops_infra",
    "security",
    "product",
    "marketing",
    "design",
    "other",
]
ReqNature = Literal[
    "technical",
    "domain",
    "experience_level",
    "behavioral",
    "language",
    "location",
    "employment",
    "other",
]
ReqOrigin = Literal[
    "explicit_requirement",
    "responsibility_inferred",
    "product_context",
    "company_value",
]
PrereqStatus = Literal[
    "prerequisite", "product_duty", "context", "behavioral_preference"
]
ReqCategory = Literal[
    "state_management",
    "styling",
    "data_fetching",
    "build_tooling",
    "testing",
    "framework",
    "language",
    "other",
]
AltMatchPolicy = Literal["exact_or_same_category", "exact_only"]
DomainAlignmentTier = Literal["strong", "adjacent", "weak", "mismatch"]

EVIDENCE_TYPES: set[str] = set(get_args(EvidenceType))
STRENGTHS: set[str] = set(get_args(Strength))
REQ_TYPES: set[str] = set(get_args(ReqType))
MATCH_LEVELS: set[str] = set(get_args(MatchLevel))
CONFIDENCES: set[str] = set(get_args(Confidence))
ROLE_FAMILIES: set[str] = set(get_args(RoleFamily))
REQ_NATURES: set[str] = set(get_args(ReqNature))
REQ_ORIGINS: set[str] = set(get_args(ReqOrigin))
PREREQ_STATUSES: set[str] = set(get_args(PrereqStatus))
REQ_CATEGORIES: set[str] = set(get_args(ReqCategory))
ALT_MATCH_POLICIES: set[str] = set(get_args(AltMatchPolicy))
DOMAIN_ALIGNMENTS: set[str] = set(get_args(DomainAlignmentTier))

# fit을 의미있게 gate하는 nature (cap을 구동) — REQ_NATURES의 부분집합
CORE_NATURES: set[str] = {"technical", "domain", "experience_level", "language"}

# JD role_family → 그것이 "속하는" 도메인 토큰 (사용자 프로파일 대비 정렬 산출 근거)
ROLE_FAMILY_TO_DOMAINS: dict[str, set[str]] = {
    "frontend": {"frontend", "web"},
    "backend": {"backend"},
    "fullstack": {"fullstack", "frontend", "backend", "web"},
    "android": {"mobile", "android"},
    "ios": {"mobile", "ios"},
    "data": {"data"},
    "ml_ai": {"ml_ai", "ai"},
    "devops_infra": {"devops", "cloud", "infra"},
    "security": {"security"},
    "product": {"product"},
    "marketing": {"marketing"},
    "design": {"design"},
    "other": {"other"},
}

MATCH_SEVERITY: dict[str, int] = {"missing": 0, "weak": 1, "adjacent": 2, "direct": 3}
SEVERITY_TO_LEVEL: dict[int, str] = {v: k for k, v in MATCH_SEVERITY.items()}
CONF_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

FIT_LABELS: dict[int, str] = {
    5: "매우 높음: 강력 추천",
    4: "높음: 추천",
    3: "보통: 검토 가능",
    2: "낮음: 아쉬움",
    1: "매우 낮음: 비추천",
}


# ---------------------------------------------------------------------------
# §3-1. 헬퍼
# ---------------------------------------------------------------------------


def clamp(value: object, allowed: set[str], default: str) -> str:
    """소문자 strip 후 allowed에 없으면 default로 클램프 (LLM 오출력 방어)."""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in allowed:
            return v
    return default


def as_list(v: object) -> list[str]:
    """콤마 분리 문자열 / 리스트 / None → list[str]로 정규화."""
    if v is None:
        return []
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()]


# ---------------------------------------------------------------------------
# §3-2. 모델 (Pydantic v2)
# ---------------------------------------------------------------------------


class EvidenceItem(BaseModel):
    """이력서 evidence 항목. exact_quote는 이력서 verbatim span(추출형의 근원)."""

    evidence_id: str
    title: str
    source_section: str
    exact_quote: str
    normalized_summary: str
    skills: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    evidence_type: EvidenceType = "other"
    strength: Strength = "medium"
    recency: str | None = None

    @field_validator("skills", "domain", mode="before")
    @classmethod
    def _coerce_lists(cls, v: object) -> list[str]:
        return as_list(v)

    @field_validator("evidence_type", mode="before")
    @classmethod
    def _clamp_evidence_type(cls, v: object) -> str:
        return clamp(v, EVIDENCE_TYPES, "other")

    @field_validator("strength", mode="before")
    @classmethod
    def _clamp_strength(cls, v: object) -> str:
        return clamp(v, STRENGTHS, "medium")


class Resume(BaseModel):
    raw_text: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    primary_domains: list[str] = Field(default_factory=list)
    secondary_domains: list[str] = Field(default_factory=list)

    @field_validator("primary_domains", "secondary_domains", mode="before")
    @classmethod
    def _coerce_lists(cls, v: object) -> list[str]:
        return as_list(v)


class Requirement(BaseModel):
    """JD 요구사항. prerequisite_status·nature·category가 cap을 구동."""

    requirement_id: str
    requirement_text: str
    requirement_type: ReqType = "required"
    requirement_nature: ReqNature = "other"
    requirement_origin: ReqOrigin = "explicit_requirement"
    prerequisite_status: PrereqStatus = "prerequisite"
    alternatives: list[str] = Field(default_factory=list)
    requirement_category: ReqCategory = "other"
    alternative_match_policy: AltMatchPolicy = "exact_or_same_category"

    @field_validator("alternatives", mode="before")
    @classmethod
    def _coerce_alternatives(cls, v: object) -> list[str]:
        return as_list(v)

    @field_validator("requirement_type", mode="before")
    @classmethod
    def _clamp_type(cls, v: object) -> str:
        return clamp(v, REQ_TYPES, "required")

    @field_validator("requirement_nature", mode="before")
    @classmethod
    def _clamp_nature(cls, v: object) -> str:
        return clamp(v, REQ_NATURES, "other")

    @field_validator("requirement_origin", mode="before")
    @classmethod
    def _clamp_origin(cls, v: object) -> str:
        return clamp(v, REQ_ORIGINS, "explicit_requirement")

    @field_validator("prerequisite_status", mode="before")
    @classmethod
    def _clamp_prereq(cls, v: object) -> str:
        return clamp(v, PREREQ_STATUSES, "prerequisite")

    @field_validator("requirement_category", mode="before")
    @classmethod
    def _clamp_category(cls, v: object) -> str:
        return clamp(v, REQ_CATEGORIES, "other")

    @field_validator("alternative_match_policy", mode="before")
    @classmethod
    def _clamp_policy(cls, v: object) -> str:
        return clamp(v, ALT_MATCH_POLICIES, "exact_or_same_category")


class JobPosting(BaseModel):
    job_id: str
    company: str
    title: str
    url: str
    role_family: RoleFamily = "other"
    employment_type: str | None = None
    location: str | None = None
    team: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    preferred_requirements: list[Requirement] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    seniority: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    raw_text: str = ""

    @field_validator("role_family", mode="before")
    @classmethod
    def _clamp_role_family(cls, v: object) -> str:
        return clamp(v, ROLE_FAMILIES, "other")

    @field_validator(
        "responsibilities", "hard_constraints", "tech_stack", mode="before"
    )
    @classmethod
    def _coerce_lists(cls, v: object) -> list[str]:
        return as_list(v)

    def all_requirements(self) -> list[Requirement]:
        """requirements + preferred_requirements (순서 보존)."""
        return self.requirements + self.preferred_requirements


class MatchRow(Requirement):
    """Requirement 필드 일체 + 매칭/검증/파이프라인 필드."""

    matched_evidence_ids: list[str] = Field(default_factory=list)
    evidence_quotes: list[str] = Field(default_factory=list)
    evidence_source_sections: list[str] = Field(default_factory=list)
    match_level: MatchLevel = "missing"
    confidence: Confidence = "low"
    explanation: str = ""
    risk_note: str = ""
    extractive_ok: bool | None = None
    downgraded: bool = False
    invalid_match: bool = False
    rematched: bool = False
    verifier_note: str = ""

    @field_validator(
        "matched_evidence_ids",
        "evidence_quotes",
        "evidence_source_sections",
        mode="before",
    )
    @classmethod
    def _coerce_match_lists(cls, v: object) -> list[str]:
        return as_list(v)

    @field_validator("match_level", mode="before")
    @classmethod
    def _clamp_match_level(cls, v: object) -> str:
        return clamp(v, MATCH_LEVELS, "missing")

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, v: object) -> str:
        return clamp(v, CONFIDENCES, "low")


class MatchingTable(BaseModel):
    job_id: str
    company: str = ""
    title: str = ""
    rows: list[MatchRow] = Field(default_factory=list)


class PairwiseResult(BaseModel):
    job_a: str
    job_b: str
    ab_winner: str = "tie"
    ba_winner: str = "tie"
    agreed: bool = False
    outcome: str = "tie"
    confidence: Confidence = "low"
    reason_ab: str = ""
    reason_ba: str = ""

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, v: object) -> str:
        return clamp(v, CONFIDENCES, "low")


class FitResult(BaseModel):
    """최종 출력 계약. fit_level은 1~5 보수적 레벨이며 합격확률/% 아님(Charter §5)."""

    job_id: str
    company: str = ""
    title: str = ""
    url: str = ""
    role_family: RoleFamily = "other"
    domain_alignment: DomainAlignmentTier = "weak"
    domain_alignment_reason: str = ""
    rank: int = 0
    fit_level: int = 1
    fit_label: str = ""
    bt_score: float = 0.0
    listwise_reason: str = ""
    coverage: dict[str, object] = Field(default_factory=dict)
    strong_matches: list[str] = Field(default_factory=list)
    weak_or_missing: list[str] = Field(default_factory=list)
    preferred_gaps: list[str] = Field(default_factory=list)
    product_duties: list[str] = Field(default_factory=list)
    invalid_matches: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)

    @field_validator("role_family", mode="before")
    @classmethod
    def _clamp_role_family(cls, v: object) -> str:
        return clamp(v, ROLE_FAMILIES, "other")

    @field_validator("domain_alignment", mode="before")
    @classmethod
    def _clamp_alignment(cls, v: object) -> str:
        return clamp(v, DOMAIN_ALIGNMENTS, "weak")


# ---------------------------------------------------------------------------
# §4-3. domain_alignment (결정적) — worker(스코어링)·crawler(도메인 선택)가 둘 다 사용
# ---------------------------------------------------------------------------


def domain_alignment(
    role_family: str, primary: Iterable[str], secondary: Iterable[str]
) -> tuple[DomainAlignmentTier, str]:
    """role_family를 사용자 도메인 대비 tier로 분류 (strong/adjacent/weak/mismatch)."""
    primary_set = {d.lower() for d in primary}
    secondary_set = {d.lower() for d in secondary}
    tokens = ROLE_FAMILY_TO_DOMAINS.get(role_family, {role_family})
    if tokens & primary_set:
        return "strong", f"role_family '{role_family}'가 사용자 주력 도메인과 직접 일치"
    if tokens & secondary_set:
        return "adjacent", f"role_family '{role_family}'가 사용자 보조 도메인과 인접"
    if role_family in {"marketing", "design", "product"}:
        return (
            "mismatch",
            f"role_family '{role_family}'는 사용자 엔지니어링 도메인과 불일치",
        )
    return "weak", f"role_family '{role_family}'가 사용자 도메인과 약하게만 관련됨"
