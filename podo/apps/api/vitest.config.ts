import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['test/**/*.spec.ts'],
    // DB 통합 테스트(skipIf(!hasDb))가 단일 Postgres를 공유하므로 파일 병렬 실행 시
    // 전역 쿼리(getFeed 글로벌 경로 등)가 타 파일 데이터와 경쟁한다 → 파일 직렬화로 격리(T-050).
    fileParallelism: false,
  },
})
