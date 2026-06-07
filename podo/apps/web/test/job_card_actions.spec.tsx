import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { JobCardActions } from '../components/JobCardActions'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('JobCardActions 지원하기 (AC-1)', () => {
  it('test_AC_1_apply_opens_link_records_and_clears', async () => {
    const openMock = vi.fn()
    vi.stubGlobal('open', openMock)
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    const onProcessed = vi.fn()

    render(<JobCardActions jobId={7} url="https://toss.test/7" onProcessed={onProcessed} />)
    fireEvent.click(screen.getByTestId('action-apply'))

    // 원본 채널 새 탭 + 낙관적 정리(onProcessed)
    expect(openMock).toHaveBeenCalledWith('https://toss.test/7', '_blank', 'noopener')
    expect(onProcessed).toHaveBeenCalledWith(7)

    // applied 기록 POST + 성공 Toast
    await waitFor(() =>
      expect(screen.getByTestId('action-toast').textContent).toContain('지원 기록됐어요'),
    )
    const [u, init] = fetchMock.mock.calls[0]
    expect(String(u)).toContain('/api/v1/applications')
    expect(JSON.parse((init as { body: string }).body)).toEqual({
      job_posting_id: 7,
      action: 'applied',
    })
  })
})

describe('JobCardActions 스킵/되돌리기 + 에러 (AC-2)', () => {
  it('test_AC_2_skip_unskip_toggle_and_error_toast', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true })
    vi.stubGlobal('fetch', fetchMock)
    const onProcessed = vi.fn()
    const onRestore = vi.fn()

    render(<JobCardActions jobId={7} onProcessed={onProcessed} onRestore={onRestore} />)
    const skipBtn = () => screen.getByTestId('action-skip')
    expect(skipBtn().textContent).toBe('스킵')

    // 스킵 → 정리 + 되돌리기 라벨
    fireEvent.click(skipBtn())
    await waitFor(() => expect(skipBtn().textContent).toBe('되돌리기'))
    expect(onProcessed).toHaveBeenCalledWith(7)
    expect(screen.getByTestId('action-toast').textContent).toContain('스킵했어요')

    // unskip(되돌리기) → 재노출
    fireEvent.click(skipBtn())
    await waitFor(() => expect(skipBtn().textContent).toBe('스킵'))
    expect(onRestore).toHaveBeenCalledWith(7)
  })

  it('test_AC_2_skip_error_toast_and_rollback', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false })) // 서버 오류
    render(<JobCardActions jobId={8} />)

    fireEvent.click(screen.getByTestId('action-skip'))
    // 실패 Toast + 라벨 롤백(스킵 유지)
    await waitFor(() =>
      expect(screen.getByTestId('action-toast').textContent).toContain(
        '기록에 실패했어요. 다시 시도해주세요.',
      ),
    )
    expect(screen.getByTestId('action-skip').textContent).toBe('스킵')
  })
})
