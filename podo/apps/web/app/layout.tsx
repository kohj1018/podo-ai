import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import type { ReactNode } from 'react'
import { LogoutButton } from '../components/LogoutButton'
import './globals.css'

export const metadata: Metadata = {
  title: 'podo',
  description: 'podo feed',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  // 세션 있을 때만 헤더 로그아웃 노출(/login 등 비로그인 화면엔 미표시).
  const loggedIn = cookies().has('connect.sid')
  return (
    <html lang="ko">
      <body>
        {loggedIn && (
          <header
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              padding: '12px 24px',
              maxWidth: '430px',
              margin: '0 auto',
            }}
          >
            <LogoutButton />
          </header>
        )}
        {children}
      </body>
    </html>
  )
}
