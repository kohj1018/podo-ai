import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthGate } from '../components/AuthGate'
import { LoginButtons } from '../components/LoginButtons'
import { SessionProvider } from '../components/SessionProvider'

// next/navigation의 useRouter().replace를 가로채 리다이렉트 호출을 검증(vi.hoisted로 mock 공유).
const { replace } = vi.hoisted(() => ({ replace: vi.fn() }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  replace.mockClear()
})

const HEX = /#[0-9a-fA-F]{3,6}/

describe('LoginButtons (AC-1)', () => {
  it('test_AC_1_login_buttons_render_with_aria_label_no_hex', () => {
    render(<LoginButtons />)

    const github = screen.getByLabelText('GitHub으로 시작')
    const google = screen.getByLabelText('Google로 시작')
    expect(github).toBeTruthy()
    expect(google).toBeTruthy()
    expect(github.textContent).toContain('GitHub으로 시작')
    expect(google.textContent).toContain('Google로 시작')

    // raw hex 없음 — 색은 DESIGN §2 토큰(var(--...))만
    for (const el of [github, google]) {
      expect(el.getAttribute('style') ?? '').not.toMatch(HEX)
    }
  })
})

describe('LoginButtons error (AC-2)', () => {
  it('test_AC_2_error_query_param_shows_retry_message', () => {
    render(<LoginButtons error="access_denied" />)

    expect(screen.getByTestId('login-error').textContent).toContain(
      '로그인에 실패했어요. 다시 시도해주세요.',
    )
    // 재시도 버튼 활성(가짜 진입 금지 — 비활성 아님)
    const github = screen.getByLabelText('GitHub으로 시작') as HTMLButtonElement
    expect(github.disabled).toBe(false)
  })
})

// AC-3 — 보호 라우트 클라이언트 가드(AuthGate). 교차 도메인이라 SSR 미들웨어 대신
// 브라우저가 /auth/me를 직접 질의(credentials:'include')해 인증 여부를 판별한다.
describe('AuthGate 보호 라우트 (AC-3)', () => {
  it('test_AC_3_authgate_redirects_unauthenticated_to_login', async () => {
    // /auth/me 401 → 미인증 → /login 리다이렉트, 보호 내용 미렌더
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))

    render(
      <SessionProvider>
        <AuthGate>
          <div>보호된 내용</div>
        </AuthGate>
      </SessionProvider>,
    )

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'))
    expect(screen.queryByText('보호된 내용')).toBeNull()
  })

  it('test_AC_3_authgate_renders_children_when_authenticated', async () => {
    // /auth/me 200 → 인증 → 보호 내용 렌더, 리다이렉트 없음
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: { userId: 'u1' } }) }),
    )

    render(
      <SessionProvider>
        <AuthGate>
          <div>보호된 내용</div>
        </AuthGate>
      </SessionProvider>,
    )

    await waitFor(() => expect(screen.getByText('보호된 내용')).toBeTruthy())
    expect(replace).not.toHaveBeenCalled()
  })
})
