'use client'

import { useEffect, useState } from 'react'

// Toast (DESIGN §7-2) — 재사용 피드백 토스트. role=status + aria-live=polite(스크린리더 polite 알림).
// 색만 의존 금지 — 텍스트 라벨로 의미 전달. 메시지 set 후 자동 dismiss(기본 3s).
export function Toast({
  message,
  durationMs = 3000,
  testId = 'toast',
}: {
  message: string | null
  durationMs?: number
  testId?: string
}) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!message) {
      setVisible(false)
      return
    }
    setVisible(true)
    const t = setTimeout(() => setVisible(false), durationMs)
    return () => clearTimeout(t)
  }, [message, durationMs])

  if (!message || !visible) {
    return null
  }

  // <output>은 암묵 role=status(biome useSemanticElements 정합) + aria-live=polite 명시.
  return (
    <output data-testid={testId} aria-live="polite" style={{ color: 'var(--muted)' }}>
      {message}
    </output>
  )
}
