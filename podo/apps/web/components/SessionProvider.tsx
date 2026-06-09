'use client'

import { type ReactNode, createContext, useContext, useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

type SessionStatus = 'loading' | 'authed' | 'guest'

const SessionContext = createContext<SessionStatus>('loading')

// 세션 상태를 api에 직접 질의(/auth/me, credentials:'include')해 전역 제공.
// web(Vercel)↔api 교차 도메인이라 SSR 쿠키로는 판별 불가 — 브라우저만 api 세션 쿠키를 보낸다.
export function SessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>('loading')

  useEffect(() => {
    let alive = true
    fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
      .then((r) => {
        if (alive) {
          setStatus(r.ok ? 'authed' : 'guest')
        }
      })
      .catch(() => {
        if (alive) {
          setStatus('guest')
        }
      })
    return () => {
      alive = false
    }
  }, [])

  return <SessionContext.Provider value={status}>{children}</SessionContext.Provider>
}

export function useSession(): SessionStatus {
  return useContext(SessionContext)
}
