import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GreetingCard } from '../components/GreetingCard'
import { PodoLottie } from '../components/PodoLottie'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function stubReducedMotion(reduce: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({
      matches: reduce,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  )
}

// T-099 AC-1 — src 전달 + 모션 허용 시 '도착' 모션 경로, reduced-motion/로드 실패/에셋 부재 시 정적 마스코트 fallback.
describe('PodoLottie arrival src + fallback (AC-1)', () => {
  it('test_AC_1_src_plays_and_fallback_preserved', () => {
    // (1) src + 모션 허용 → 모션 컨테이너(정적 포스터 아님, aria-hidden 모션 영역)
    stubReducedMotion(false)
    render(<PodoLottie src="/podo-arrival.lottie" />)
    const motion = screen.getByTestId('podo-lottie')
    expect(motion.getAttribute('data-static')).not.toBe('true')
    expect(motion.getAttribute('aria-hidden')).toBe('true')
    cleanup()
    vi.unstubAllGlobals()

    // (2) reduced-motion → src 전달돼도 정적 마스코트 fallback
    stubReducedMotion(true)
    render(<PodoLottie src="/podo-arrival.lottie" />)
    const reduced = screen.getByTestId('podo-lottie')
    expect(reduced.getAttribute('data-static')).toBe('true')
    expect(within(reduced).getByTestId('podo-mascot')).toBeTruthy()
    cleanup()
    vi.unstubAllGlobals()

    // (3) src 부재(에셋 미조달/로드 실패 대용) → 정적 fallback 보존(비차단)
    stubReducedMotion(false)
    render(<PodoLottie />)
    expect(screen.getByTestId('podo-lottie').getAttribute('data-static')).toBe('true')
  })

  it('test_AC_1_greeting_card_passes_src', () => {
    // GreetingCard가 PodoLottie에 src를 전달 → 모션 허용 시 모션 경로(정적 아님)
    stubReducedMotion(false)
    render(<GreetingCard newCount={1} expiringCount={0} />)
    expect(screen.getByTestId('podo-lottie').getAttribute('data-static')).not.toBe('true')
  })
})
