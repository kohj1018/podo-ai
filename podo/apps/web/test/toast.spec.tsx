import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { JobCardActions } from '../components/JobCardActions'
import { Toast } from '../components/Toast'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// QA-M7-003 회귀 — auto-dismiss 후 동일 메시지를 새 key로 다시 set하면 재노출(JobCardActions notify seq 메커니즘).
function Harness({ msg, seq }: { msg: string; seq: number }) {
  return (
    <div>
      <Toast key={seq} message={msg} testId="t" />
    </div>
  )
}

describe('Toast re-show after dismiss (QA-M7-003 repair)', () => {
  it('test_toast_reshows_same_message_on_new_key', () => {
    vi.useFakeTimers()
    const { rerender } = render(<Harness msg="저장 실패" seq={1} />)
    expect(screen.getByTestId('t')).toBeTruthy()

    act(() => {
      vi.advanceTimersByTime(3500)
    })
    expect(screen.queryByTestId('t')).toBeNull() // 자동 dismiss

    // 동일 메시지지만 seq(key) 변경 → 재마운트 → 다시 노출
    rerender(<Harness msg="저장 실패" seq={2} />)
    expect(screen.getByTestId('t')).toBeTruthy()
    vi.useRealTimers()
  })
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
