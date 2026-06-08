# syntax=docker/dockerfile:1
# T-089 배포: worker(Python SQS consumer) 컨테이너. 빌드 컨텍스트 = 리포 루트
#   (worker가 ai/core를 import — uv workspace). deploy-worker.yml이 컨텍스트 '.' 로 빌드.
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# uv 워크스페이스 lock + 멤버 소스. crawler는 같은 워크스페이스라 함께 sync(무해).
COPY pyproject.toml uv.lock ./
COPY ai ./ai
COPY crawler ./crawler
RUN uv sync --frozen --no-dev

# 상시 SQS consumer (인자 없는 `python -m worker` = consume 루프, ADR-106).
# --frozen: 런타임 재동기화 없이 빌드 시 lock 환경 그대로 사용(결정성).
CMD ["uv","run","--no-dev","--frozen","python","-m","worker"]
