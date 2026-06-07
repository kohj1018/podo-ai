import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ArrivalList } from '../components/ArrivalList'
import { Onboarding } from '../components/Onboarding'
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

const ITEMS = [{ id: 1 }, { id: 2 }, { id: 3 }]

describe('ArrivalList motion + reduced-motion (AC-1)', () => {
  it('test_AC_1_arrival_motion_and_reduced_motion_branch', () => {
    // 모션 on: fade+translateY(arrival-rise) + stagger(animation-delay)
    stubReducedMotion(false)
    render(
      <ArrivalList items={ITEMS} keyOf={(i) => i.id} renderItem={(i) => <span>item{i.id}</span>} />,
    )
    const items = screen.getAllByTestId('arrival-item')
    expect(items).toHaveLength(3)
    expect(items[0].getAttribute('data-reduced')).toBe('false')
    expect(items[0].getAttribute('style')).toContain('arrival-rise')
    expect(items[1].getAttribute('style')).toContain('animation-delay') // stagger

    cleanup()
    vi.unstubAllGlobals()

    // reduced: transform/stagger 없이 opacity fade(arrival-fade)만
    stubReducedMotion(true)
    render(
      <ArrivalList items={ITEMS} keyOf={(i) => i.id} renderItem={(i) => <span>item{i.id}</span>} />,
    )
    const reducedItems = screen.getAllByTestId('arrival-item')
    expect(reducedItems[0].getAttribute('data-reduced')).toBe('true')
    expect(reducedItems[0].getAttribute('style')).toContain('arrival-fade')
    expect(reducedItems[0].getAttribute('style')).not.toContain('arrival-rise')
    expect(reducedItems[0].getAttribute('style')).not.toContain('animation-delay')
  })
})

describe('PodoLottie reduced-motion / fallback (AC-2)', () => {
  it('test_AC_2_lottie_reduced_motion_static_and_fallback', () => {
    // reduced-motion → autoplay 비활성 + 정적 포스터(무렌더 아님) + aria-hidden
    stubReducedMotion(true)
    render(<PodoLottie src="podo.lottie" />)
    const el = screen.getByTestId('podo-lottie')
    expect(el.getAttribute('data-static')).toBe('true')
    // 정적 포스터 = 마스코트 PNG(무렌더 아님 — 마스코트는 보임)
    expect(within(el).getByTestId('podo-mascot')).toBeTruthy()

    cleanup()
    vi.unstubAllGlobals()

    // src 부재(로드 실패 대용) → CSS fallback 포스터
    stubReducedMotion(false)
    render(<PodoLottie />)
    expect(screen.getByTestId('podo-lottie').getAttribute('data-static')).toBe('true')
  })
})

describe('Onboarding first-entry once (AC-3)', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('test_AC_3_onboarding_first_entry_once', () => {
    // 첫 진입 → 온보딩 안내(포도 + 업로드 링크)
    render(<Onboarding />)
    expect(screen.getByTestId('onboarding')).toBeTruthy()
    expect(screen.getByTestId('onboarding-guide')).toBeTruthy()

    // dismiss → 큰 안내 미표시(최소 링크만)
    fireEvent.click(screen.getByTestId('onboarding-dismiss'))
    expect(screen.queryByTestId('onboarding')).toBeNull()
    expect(screen.getByTestId('onboarding-minimal')).toBeTruthy()

    // 재진입(remount) → 여전히 미표시
    cleanup()
    render(<Onboarding />)
    expect(screen.queryByTestId('onboarding')).toBeNull()
  })
})
