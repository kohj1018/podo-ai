import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoarseSection } from '../components/CoarseSection'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// T-065 AC-3: coarse 섹션 UI는 FitScoreRing/PassBand 배지 없이 유사도순 공고만 노출(Guardrail 1).
describe('CoarseSection (T-065 AC-3)', () => {
  it('test_AC_3_coarse_no_badge', async () => {
    const page = {
      items: [
        { posting: { id: 1, company: 'Toss', title: 'Backend Engineer' }, similarity_rank: 0.9 },
        { posting: { id: 2, company: 'Daangn', title: 'Frontend Engineer' }, similarity_rank: 0.8 },
      ],
      nextCursor: null,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => page }))

    render(<CoarseSection />)
    await waitFor(() => expect(screen.getByTestId('coarse-section')).toBeTruthy())
    const section = screen.getByTestId('coarse-section')

    // fit 배지 없음 — coarse는 깊은 분석 전(거짓 점수 금지)
    expect(screen.queryByTestId('fitring')).toBeNull()
    expect(screen.queryByTestId('passband')).toBeNull()
    // 공고 노출 + coarse copy
    expect(screen.getAllByTestId('coarse-item').length).toBe(2)
    expect(section.textContent).toContain('Toss')
    expect(section.textContent).toContain('아직 깊이 안 본')
  })

  it('test_empty_coarse_hidden', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [], nextCursor: null }) }),
    )
    render(<CoarseSection />)
    // 빈 coarse → 섹션 미렌더(null)
    await waitFor(() => expect(screen.queryByTestId('coarse-section')).toBeNull())
  })
})
