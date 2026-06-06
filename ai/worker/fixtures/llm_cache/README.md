# worker LLM 웜캐시 (committed fixture)

이 디렉터리는 **무키 fresh-clone E2E**(graduation §5 #3)를 결정적으로 만들기 위한
LLM 응답 웜캐시다. `worker.cache`가 `(model, system, user, schema_version)` sha256 키로
응답을 디스크에 저장하므로, fixture 공고(`crawler/fixtures/seed_jobs.txt`) + seed 이력서로
한 번 채점해 두면 이후 어떤 clone에서도 `OPENAI_API_KEY` 없이 캐시 hit으로 재현된다.

전역 `.cache/llm`(gitignored, 임시 dev 캐시)과 분리하기 위해 `LLM_CACHE_DIR`로 이 경로를
가리킨다 — `scripts/e2e.mjs`가 자동 설정한다.

## 채우는 법 (1회, 키 보유자만)

```bash
# OPENAI_API_KEY를 가진 상태에서 1회 실행 → 이 디렉터리에 캐시 JSON 생성
pnpm e2e:warm
# 생성된 *.json 을 커밋
git add ai/worker/fixtures/llm_cache
```

이후 `pnpm e2e`(무키) 및 CI e2e-smoke가 이 캐시로 외부 호출 0회로 통과한다.

## 무효화

캐시 키 핀(`OPENAI_MODEL` / `PROMPT_VERSION` / `SCHEMA_VERSION`) 또는 fixture JD 텍스트가
바뀌면 키가 달라져 캐시가 stale된다. `pnpm e2e:warm`을 다시 돌려 재생성·재커밋한다.
