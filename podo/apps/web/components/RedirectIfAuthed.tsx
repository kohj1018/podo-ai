'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { useSession } from './SessionProvider'

// 이미 로그인된 사용자가 /login에 오면 피드(/)로 돌려보냄 — SSR 쿠키 리다이렉트 대체.
export function RedirectIfAuthed() {
  const status = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === 'authed') {
      router.replace('/')
    }
  }, [status, router])

  return null
}
