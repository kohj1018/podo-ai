'use client'

import { LogoutButton } from './LogoutButton'
import { useSession } from './SessionProvider'

// 상단 헤더 — 로그인 상태에서만 노출(로고 + 로그아웃). /login 등 비로그인 화면엔 미표시.
// 교차 도메인이라 세션은 client에서 판별(useSession) — SSR 쿠키로 못 봄.
export function AppHeader() {
  const status = useSession()
  if (status !== 'authed') {
    return null
  }
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 16px',
        maxWidth: '430px',
        margin: '0 auto',
      }}
    >
      <a
        href="/"
        aria-label="피드 홈"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontWeight: 700,
          color: 'inherit',
          textDecoration: 'none',
        }}
      >
        <img src="/podo-mascot.png" alt="" width={24} height={24} style={{ display: 'block' }} />
        <span>
          포도{' '}
          <span
            style={{
              background: 'var(--brand-gradient)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent',
            }}
          >
            ai
          </span>
        </span>
      </a>
      {/* 전역 네비(T-093) — 마이페이지 진입 + 로그아웃. 링크 시맨틱·키보드 도달. */}
      <nav aria-label="주요 메뉴" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <a
          href="/me"
          data-testid="nav-mypage"
          style={{ color: 'var(--grape-700)', textDecoration: 'none', fontWeight: 600 }}
        >
          마이페이지
        </a>
        <LogoutButton />
      </nav>
    </header>
  )
}
