"""worker/config.py — 결정론 핀 상수 + env 로딩.

캐시 키에 영향을 주는 값(SCHEMA_VERSION, OPENAI_MODEL, PROMPT_VERSION, LLM_SEED)은
여기서만 관리한다. 시간·랜덤·환경 의존 값은 캐시 키에 혼입하지 않는다 (ARCH §3-1).

env 로딩은 레포 루트의 .env를 결정적으로 읽는다. bare load_dotenv()는 CWD 기준으로
위로 탐색하므로 레포 밖에서 실행하면 .env를 못 찾아 OPENAI_API_KEY가 비게 된다.
폴리글랏 모노레포에서 Python 백엔드(uv 워크스페이스: ai/* + crawler)의 단일 env 소스는
레포 루트 .env다. 웹(podo/)은 프레임워크 관례대로 자기 디렉터리의 .env를 따로 둔다
(백엔드 시크릿을 프론트 번들에 노출하지 않기 위한 분리).
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from core.models import Resume


def _load_root_env() -> None:
    """config.py 위치에서 위로 올라가 레포 루트의 .env를 로드한다 (CWD 무관).

    레포 루트는 루트 전용 마커(.git/uv.lock/pnpm-lock.yaml/.env.example)로 식별한다.
    실 .env가 없으면 no-op(실제 환경변수/기본값 사용). 마커를 못 찾으면 기본 탐색 폴백.
    실제 환경변수가 .env보다 우선한다(load_dotenv override=False).
    배포 시 표준 주입 경로.
    """
    markers = (".git", "uv.lock", "pnpm-lock.yaml", ".env.example")
    for parent in Path(__file__).resolve().parents:
        if any((parent / m).exists() for m in markers):
            load_dotenv(parent / ".env")
            return
    load_dotenv()  # 폴백: 마커 미발견 시 기본 CWD 탐색


_load_root_env()

# 캐시 키 핀 — 변경 시 기존 캐시 자동 무효화 (SPEC §8-2)
SCHEMA_VERSION: str = os.environ.get("SCHEMA_VERSION", "v1")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
PROMPT_VERSION: str = os.environ.get("PROMPT_VERSION", "v1")

# 재현성 힌트 — 캐시가 주 메커니즘, seed는 보조 (SPEC §8-1)
LLM_SEED: int = int(os.environ.get("LLM_SEED", "7"))

# OpenAI API key — 시스템 경계에서만 사용
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

# 공고별 LLM 단계(구조화·매칭·검증) 병렬도 — 채점 지연의 주 레버(직렬 → 병렬 I/O).
# 공고 독립·콘텐츠 캐시라 병렬화해도 결과 결정적(GS-1). rate-limit 고려 보수적 기본.
SCORING_MAX_WORKERS: int = int(os.environ.get("SCORING_MAX_WORKERS", "8"))


# 합성 seed 이력서 (SPEC §9-4 — M2는 실 PII 비범위, config 주입 합성만).
# raw_text 안의 문장이 evidence 추출형 검증의 haystack이 된다.
_DEFAULT_SEED_TEXT = (
    "프론트엔드 개발자 이력서 (합성 seed — SPEC §9-4).\n"
    "React 18 프로젝트에서 3년간 프론트엔드 개발을 수행했다.\n"
    "TypeScript와 Next.js 기반 SPA 설계 및 상태관리 경험이 있다.\n"
    "백엔드와 협업해 REST API를 연동한 경험이 다수 있다."
)


def load_seed_resume() -> Resume:
    """합성 seed 이력서를 로드한다 (SPEC §9-4).

    `SEED_RESUME_JSON`(파일 경로)이 있으면 그 JSON을, 없으면 기본 합성 이력서를 쓴다.
    JSON 형식: {"raw_text": str, "primary_domains": [str], "secondary_domains": [str]}.
    """
    path = os.environ.get("SEED_RESUME_JSON")
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return Resume(
            raw_text=data["raw_text"],
            primary_domains=data["primary_domains"],
            secondary_domains=data.get("secondary_domains", []),
        )
    return Resume(
        raw_text=_DEFAULT_SEED_TEXT,
        primary_domains=["frontend"],
        secondary_domains=["backend"],
    )
