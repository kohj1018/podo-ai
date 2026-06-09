import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { AppHeader } from '../components/AppHeader'
import { SessionProvider } from '../components/SessionProvider'
import './globals.css'

export const metadata: Metadata = {
  title: 'podo',
  description: 'podo feed',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  // 세션은 client에서 판별(SessionProvider→/auth/me) — web(Vercel)↔api 교차 도메인이라
  // SSR이 api 세션 쿠키를 못 본다. 헤더(로그아웃)는 AppHeader가 로그인 시에만 노출.
  return (
    <html lang="ko">
      <head>
        {/* Pretendard 단일 family(DESIGN §3) — CDN variable 폰트. */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css"
        />
      </head>
      <body>
        <SessionProvider>
          {/* 단일 중앙 컬럼 셸(T-101) — 데스크톱에서도 멀티컬럼 없이 중앙 정렬 유지. */}
          <div className="app-shell">
            <AppHeader />
            {children}
          </div>
        </SessionProvider>
      </body>
    </html>
  )
}
