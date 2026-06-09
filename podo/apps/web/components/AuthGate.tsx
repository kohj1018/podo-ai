'use client'

import { useRouter } from 'next/navigation'
import { type ReactNode, useEffect } from 'react'
import { useSession } from './SessionProvider'

// 보호 라우트 클라이언트 가드 — 세션 미인증이면 /login으로 리다이렉트.
// SSR 미들웨어 대체: web(Vercel)↔api 교차 도메인이라 SSR이 api 세션 쿠키를 못 본다(브라우저만 봄).
export function AuthGate({ children }: { children: ReactNode }) {
  const status = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === 'guest') {
      router.replace('/login')
    }
  }, [status, router])

  if (status === 'authed') {
    return <>{children}</>
  }
  // loading + guest(리다이렉트 진행 중) — 깜빡임 최소 placeholder. <output>=암묵 role=status.
  return (
    <output
      aria-live="polite"
      style={{
        display: 'block',
        maxWidth: '430px',
        margin: '0 auto',
        padding: '48px 24px',
        color: 'var(--muted)',
      }}
    >
      불러오는 중…
    </output>
  )
}
