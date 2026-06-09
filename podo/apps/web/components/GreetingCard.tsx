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
        maxWidth: '430px',
        margin: '0 auto',
        borderRadius: '24px',
        overflow: 'hidden',
        background: 'var(--surface)',
        color: 'var(--ink)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      {/* fenced 그라데이션 인사 strip(§2-4 허용 3곳 중 1곳). */}
      <div aria-hidden="true" style={{ height: '5px', background: 'var(--brand-gradient)' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', padding: '16px 18px' }}>
        {/* 포도 마스코트 — '도착' Lottie(T-099). 에셋 미조달/reduced-motion/로드실패 시 정적 마스코트 fallback. */}
        <PodoLottie src="/podo-arrival.lottie" size={52} />
        <div>
          <p style={{ fontWeight: 700, margin: 0, fontSize: '18px' }}>
            포도가 오늘의 자리를 골라왔어요!
          </p>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: '13px' }}>
            <span data-testid="new-count">신규 {newCount}건</span>
            {' · '}
            <span data-testid="expiring-count">마감 임박 {expiringCount}건</span>
          </p>
        </div>
      </div>
    </section>
  )
}
