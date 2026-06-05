"""worker/config.py — 결정론 핀 상수 + env 로딩.

캐시 키에 영향을 주는 값(SCHEMA_VERSION, OPENAI_MODEL_ID, PROMPT_VERSION, LLM_SEED)은
여기서만 관리한다. 시간·랜덤·환경 의존 값은 캐시 키에 혼입하지 않는다 (ARCH §3-1).
"""

import os

from dotenv import load_dotenv

load_dotenv()

# 캐시 키 핀 — 변경 시 기존 캐시 자동 무효화 (SPEC §8-2)
SCHEMA_VERSION: str = os.environ.get("SCHEMA_VERSION", "v1")
OPENAI_MODEL_ID: str = os.environ.get("OPENAI_MODEL_ID", "gpt-4o-mini")
PROMPT_VERSION: str = os.environ.get("PROMPT_VERSION", "v1")

# 재현성 힌트 — 캐시가 주 메커니즘, seed는 보조 (SPEC §8-1)
LLM_SEED: int = int(os.environ.get("LLM_SEED", "7"))

# OpenAI API key — 시스템 경계에서만 사용
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
