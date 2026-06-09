import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import MyPage from '../app/me/page'
import { SessionProvider } from '../components/SessionProvider'

// AuthGate가 useRouter 호출 — authed 경로에선 replace 미호출.
const { replace } = vi.hoisted(() => ({ replace: vi.fn() }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  replace.mockClear()
})

function authedFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: { userId: 'u1' } }) }),
  )
}

// T-093 — 마이페이지 허브: 이력서 수정·즐겨찾기·지원기록·로그아웃 진입.
describe('MyPage hub (AC-1, AC-3)', () => {
  it('test_AC_1_hub_links', async () => {
    authedFetch()
    render(
      <SessionProvider>
        <MyPage />
      </SessionProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('link-resume-edit')).toBeTruthy())
    expect(screen.getByTestId('link-favorites')).toBeTruthy()
    expect(screen.getByTestId('link-applications')).toBeTruthy()
    expect(screen.getByLabelText('로그아웃')).toBeTruthy()
  })

  it('test_AC_3_resume_edit_link', async () => {
    authedFetch()
    render(
      <SessionProvider>
        <MyPage />
      </SessionProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('link-resume-edit')).toBeTruthy())
    // "이력서 수정" → /resume
    expect(screen.getByTestId('link-resume-edit').getAttribute('href')).toBe('/resume')
  })
})
