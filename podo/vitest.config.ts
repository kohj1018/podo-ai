import { defineConfig } from 'vitest/config'

// 워크스페이스 마커 config (verify.mjs 의 podo/vitest.config 존재 검사용).
// 실제 테스트는 apps/* 각자의 vitest.config.ts 로 `pnpm --filter "./podo/**" exec vitest run` 시 실행된다.
export default defineConfig({
  test: {
    passWithNoTests: true,
  },
})
