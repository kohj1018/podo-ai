'use client'

import { PodoMascot } from './PodoMascot'

// OnboardingGuide (DESIGN §7) — 첫 진입(이력서 없음) 시 포도가 업로드를 안내(F-018 empty 흐름).
// 1회성 코치마크가 아니라 빈 피드 인라인 안내(단순성 — 열린 질문 결정). raw hex 0(토큰만).
export function OnboardingGuide() {
  return (
    <section
      data-testid="onboarding-guide"
      aria-label="시작 안내"
      style={{
        maxWidth: '430px',
        margin: '0 auto',
        padding: '40px 16px',
        color: 'var(--ink)',
      }}
    >
      <PodoMascot size={88} />
      <h2 style={{ margin: '16px 0 4px', fontSize: '21px', fontWeight: 700 }}>
        이력서를 업로드해 포도와 시작해요
      </h2>
      <p style={{ color: 'var(--muted)', marginBottom: '20px' }}>
        이력서를 올리면 포도가 매일 맞는 자리를 골라 배달할게요.
      </p>
      <a
        href="/resume"
        style={{
          display: 'inline-block',
          padding: '12px 22px',
          borderRadius: '16px',
          background: 'var(--grape-600)',
          color: 'var(--surface)',
          fontWeight: 600,
          textDecoration: 'none',
          boxShadow: 'var(--shadow-soft)',
        }}
      >
        이력서 업로드
      </a>
    </section>
  )
}
