import { describe, expect, it } from 'vitest'

// F-005/T-018 §3-5: Vitest placeholder smoke. 실로직 테스트는 F-010(T-028/T-029)에서.
describe('web smoke', () => {
  it('placeholder smoke test passes', () => {
    expect(1 + 1).toBe(2)
  })
})
