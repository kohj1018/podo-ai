import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { JobCardActions } from '../components/JobCardActions'
import { Toast } from '../components/Toast'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// T-100 AC-1 — 지원/스킵/즐겨찾기 피드백이 공용 Toast(role=status, aria-live=polite)로 동일 동작.
describe('Toast component + JobCardActions feedback (AC-1)', () => {
  it('test_AC_1_toast_feedback_behavior_preserved', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }))

    render(<JobCardActions jobId={5} />)
    fireEvent.click(screen.getByTestId('action-favorite'))

    // 공용 Toast로 동일 메시지(행동 불변) + role=status/aria-live=polite
    await waitFor(() =>
      expect(screen.getByTestId('action-toast').textContent).toContain('즐겨찾기에 담았어요'),
    )
    // 공용 Toast = role=status(output 암묵) + aria-live=polite
    const toast = screen.getByTestId('action-toast')
    expect(screen.getByRole('status')).toBe(toast)
    expect(toast.getAttribute('aria-live')).toBe('polite')
  })

  it('test_toast_renders_message_and_hidden_when_null', () => {
    // 메시지 없으면 미렌더
    const { rerender } = render(<Toast message={null} testId="t" />)
    expect(screen.queryByTestId('t')).toBeNull()

    // 메시지 있으면 role=status 라벨(색만 의존 X — 텍스트 라벨)
    rerender(<Toast message="저장했어요" testId="t" />)
    const el = screen.getByTestId('t')
    expect(screen.getByRole('status')).toBe(el)
    expect(el.getAttribute('aria-live')).toBe('polite')
    expect(el.textContent).toBe('저장했어요')
  })
})
