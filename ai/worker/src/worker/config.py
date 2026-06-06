"""worker/config.py — 결정론 핀 상수 + env 로딩.

캐시 키에 영향을 주는 값(SCHEMA_VERSION, OPENAI_MODEL, PROMPT_VERSION, LLM_SEED)은
여기서만 관리한다. 시간·랜덤·환경 의존 값은 캐시 키에 혼입하지 않는다 (ARCH §3-1).

env 로딩은 레포 루트의 .env를 결정적으로 읽는다. bare load_dotenv()는 CWD 기준으로
위로 탐색하므로 레포 밖에서 실행하면 .env를 못 찾아 OPENAI_API_KEY가 비게 된다.
폴리글랏 모노레포에서 Python 백엔드(uv 워크스페이스: ai/* + crawler)의 단일 env 소스는
레포 루트 .env다. 웹(podo/)은 프레임워크 관례대로 자기 디렉터리의 .env를 따로 둔다
(백엔드 시크릿을 프론트 번들에 노출하지 않기 위한 분리).
"""

import os
from pathlib import Path

from dotenv import load_dotenv


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
