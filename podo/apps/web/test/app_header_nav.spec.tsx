import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AppHeader } from '../components/AppHeader'
import { SessionProvider } from '../components/SessionProvider'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// T-093 AC-2 — 인증 시 AppHeader에 마이페이지 진입 네비 노출 + 키보드 도달(anchor).
describe('AppHeader nav (AC-2)', () => {
  it('test_AC_2_nav_visible_authed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: { userId: 'u1' } }) }),
    )
    render(
      <SessionProvider>
        <AppHeader />
      </SessionProvider>,
    )
    await waitFor(() => expect(screen.getByTestId('nav-mypage')).toBeTruthy())
    // /me 링크 + nav 시맨틱(키보드 도달 anchor)
    expect(screen.getByTestId('nav-mypage').getAttribute('href')).toBe('/me')
    expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toBeTruthy()
  })

  it('test_nav_hidden_when_guest', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    render(
      <SessionProvider>
        <AppHeader />
      </SessionProvider>,
    )
    // 비인증 → 헤더 미노출 → 네비 없음
    await waitFor(() => expect(screen.queryByTestId('nav-mypage')).toBeNull())
  })
})
