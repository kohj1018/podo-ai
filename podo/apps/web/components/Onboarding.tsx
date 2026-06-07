'use client'

import { useEffect, useState } from 'react'
import { OnboardingGuide } from './OnboardingGuide'

const FLAG = 'podo_onboarding_dismissed'

// Onboarding (DESIGN §8-1/§7) — 첫 진입(세션·이력서 없음) 1회성 안내. dismiss 후 localStorage 플래그로
// 큰 안내 대신 최소 링크만(이력서 없는 사용자는 항상 업로드 경로 필요). F-018 온보딩 흐름(AC-3).
export function Onboarding() {
  const [mounted, setMounted] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    setMounted(true)
    setDismissed(localStorage.getItem(FLAG) === '1')
  }, [])

  if (!mounted) return null // 하이드레이션 플래시 방지(서버=null)

  if (dismissed) {
    return (
      <p
        data-testid="onboarding-minimal"
        style={{ maxWidth: '430px', margin: '0 auto', padding: '16px', color: 'var(--muted)' }}
      >
        이력서를 올리면 시작해요{' '}
        <a href="/resume" style={{ color: 'var(--grape-700)' }}>
          업로드
        </a>
      </p>
    )
  }

  return (
    <div data-testid="onboarding">
      <OnboardingGuide />
      <div style={{ maxWidth: '430px', margin: '0 auto', padding: '0 16px' }}>
        <button
          type="button"
          data-testid="onboarding-dismiss"
          onClick={() => {
            localStorage.setItem(FLAG, '1')
            setDismissed(true)
          }}
          style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}
        >
          닫기
        </button>
      </div>
    </div>
  )
}
