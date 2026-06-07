'use client'

import { PodoLottie } from './PodoLottie'

// GreetingCard (DESIGN §7) — 포도 인사 + 오늘의 신규/마감 카운트. 동반자 정체성의 진입 인사.
// 마스코트는 chrome(인사)에만 — 점수/근거엔 장식 금지(DESIGN §1 원칙1). raw hex 0(토큰만).
export function GreetingCard({
  newCount,
  expiringCount,
}: {
  newCount: number
  expiringCount: number
}) {
  return (
    <section
      data-testid="greeting-card"
      aria-label="오늘의 요약"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        maxWidth: '430px',
        margin: '0 auto',
        padding: '16px',
        borderRadius: '16px',
        background: 'var(--grape-100)',
        color: 'var(--ink)',
      }}
    >
      {/* 포도 마스코트 — PodoLottie(src 없으면 정적 포스터, lottie 에셋은 후속). 장식(aria-hidden). */}
      <PodoLottie size={48} />
      <div>
        <p style={{ fontWeight: 600, margin: 0 }}>포도가 오늘의 자리를 골라왔어요!</p>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>
          <span data-testid="new-count">신규 {newCount}건</span>
          {' · '}
          <span data-testid="expiring-count">마감 임박 {expiringCount}건</span>
        </p>
      </div>
    </section>
  )
}
