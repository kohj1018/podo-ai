import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoarseSection } from '../components/CoarseSection'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const TWO = {
  items: [
    { posting: { id: 1, company: 'Toss', title: 'Backend Engineer' }, similarity_rank: 0.9 },
    { posting: { id: 2, company: 'Daangn', title: 'Frontend Engineer' }, similarity_rank: 0.8 },
  ],
  nextCursor: null,
}

// T-091 AC-1 — 피드 하단 접힌 보조 진입, 토글 시 목록. coarse 0이면 미렌더.
describe('CoarseSection collapsed mount (T-091 AC-1)', () => {
  it('test_AC_1_collapsed_mount_and_expand', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => TWO }))

    render(<CoarseSection />)
    await waitFor(() => expect(screen.getByTestId('coarse-section')).toBeTruthy())

    // 기본 접힘 — "N개 · 펼치기" 진입, 목록은 미렌더
    const toggle = screen.getByTestId('coarse-toggle')
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(toggle.textContent).toContain('2개')
    expect(screen.queryByTestId('coarse-item')).toBeNull()

    // 토글 → 목록 노출
    fireEvent.click(toggle)
    expect(screen.getByTestId('coarse-toggle').getAttribute('aria-expanded')).toBe('true')
    expect(screen.getAllByTestId('coarse-item').length).toBe(2)
    expect(screen.getByTestId('coarse-section').textContent).toContain('Toss')
  })

  it('test_empty_coarse_hidden — coarse 0건이면 섹션 미렌더', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [], nextCursor: null }) }),
    )
    render(<CoarseSection />)
    await waitFor(() => expect(screen.queryByTestId('coarse-section')).toBeNull())
  })
})

// T-091 AC-2 — 펼침 항목에 FitScoreRing/PassBand/fit 배지 0개(ADR-108 D3).
describe('CoarseSection no fit badges (T-091 AC-2)', () => {
  it('test_AC_2_no_fit_badges', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => TWO }))

    render(<CoarseSection />)
    await waitFor(() => expect(screen.getByTestId('coarse-section')).toBeTruthy())
    fireEvent.click(screen.getByTestId('coarse-toggle')) // 펼침

    // 깊은 분석 전 — 가짜 점수/밴드 금지
    expect(screen.queryByTestId('fitring')).toBeNull()
    expect(screen.queryByTestId('passband')).toBeNull()
    // 회사·직무만 표시
    const section = screen.getByTestId('coarse-section')
    expect(section.textContent).toContain('Toss')
    expect(section.textContent).toContain('아직 깊이 안 본')
  })
})
