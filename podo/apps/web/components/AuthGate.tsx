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
  // loading + guest(리다이렉트 진행 중) — skeleton(shimmer) placeholder. <output>=암묵 role=status + aria-busy.
  // shimmer는 globals.css에서 reduced-motion 정적 분기(T-098 AC-2). 가짜 점수/preview 미표시.
  return (
    <output
      aria-live="polite"
      aria-busy="true"
      aria-label="불러오는 중"
      data-testid="authgate-loading"
      style={{ display: 'block', maxWidth: '430px', margin: '0 auto', padding: '48px 24px' }}
    >
      <div
        className="shimmer"
        style={{ height: '16px', borderRadius: '8px', marginBottom: '10px' }}
      />
      <div className="shimmer" style={{ height: '16px', borderRadius: '8px', width: '60%' }} />
    </output>
  )
}
