-- T-088: llm_cache (worker 소유 공유 LLM 응답 캐시 — F-027). 디스크 .cache/llm → Postgres JSONB.
-- 동일 cache_key → 동일 response(GS-1 멀티인스턴스 재현성). NestJS 읽기 금지(worker 내부 캐시).
-- DDL=Prisma SSOT(§3-2 규칙2). 캐시 키는 make_key(model·prompt·schema) 해시 — 모델/프롬프트
-- 버전 변경 시 키가 달라져 자연 무효화(model_version·prompt_version은 ops 추적 메타).

-- CreateTable
CREATE TABLE "llm_cache" (
    "cache_key" TEXT NOT NULL,
    "response" JSONB NOT NULL,
    "model_version" TEXT NOT NULL,
    "prompt_version" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "llm_cache_pkey" PRIMARY KEY ("cache_key")
);
