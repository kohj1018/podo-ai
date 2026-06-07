import { cleanup, render, screen } from '@testing-library/react'
import { NextRequest } from 'next/server'
import { afterEach, describe, expect, it } from 'vitest'
import { LoginButtons } from '../components/LoginButtons'
import { middleware } from '../middleware'

afterEach(() => cleanup())

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

describe('middleware 보호 라우트 (AC-3)', () => {
  it('test_AC_3_middleware_redirects_unauthenticated_to_login', () => {
    // 세션 쿠키 없는 요청 → /login 리다이렉트
    const req = new NextRequest('http://localhost:3000/')
    const res = middleware(req)
    expect(res.status).toBe(307) // NextResponse.redirect
    expect(res.headers.get('location')).toContain('/login')
  })

  it('test_AC_3_middleware_allows_authenticated', () => {
    const req = new NextRequest('http://localhost:3000/')
    req.cookies.set('connect.sid', 's:fake.sig')
    const res = middleware(req)
    // 세션 있으면 통과(redirect 아님)
    expect(res.headers.get('location')).toBeNull()
  })
})
