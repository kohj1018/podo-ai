import { type NextRequest, NextResponse } from 'next/server'

// express-session 기본 쿠키명(T-042 main.ts). 존재 여부로 1차 인증 판단(최종 401은 api).
const SESSION_COOKIE = 'connect.sid'

// 보호 라우트 SSR 가드 — 세션 쿠키 없으면 /login으로 리다이렉트(비로그인 차단).
export function middleware(request: NextRequest): NextResponse {
  if (request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.next()
  }
  const url = request.nextUrl.clone()
  url.pathname = '/login'
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ['/', '/resume', '/feed'],
}
