import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import type { ReactNode } from 'react'
import { LogoutButton } from '../components/LogoutButton'
import './globals.css'

export const metadata: Metadata = {
  title: 'podo',
  description: 'podo feed',
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  // 세션 있을 때만 헤더 로그아웃 노출(/login 등 비로그인 화면엔 미표시).
  // Next 15: cookies()는 async — await 필수(T-089 dep bump).
  const loggedIn = (await cookies()).has('connect.sid')
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
        {loggedIn && (
          <header
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 16px',
              maxWidth: '430px',
              margin: '0 auto',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}>
              <img
                src="/podo-mascot.png"
                alt=""
                width={24}
                height={24}
                style={{ display: 'block' }}
              />
              <span>
                포도{' '}
                <span
                  style={{
                    background: 'var(--brand-gradient)',
                    WebkitBackgroundClip: 'text',
                    backgroundClip: 'text',
                    color: 'transparent',
                  }}
                >
                  ai
                </span>
              </span>
            </span>
            <LogoutButton />
          </header>
        )}
        {children}
      </body>
    </html>
  )
}
