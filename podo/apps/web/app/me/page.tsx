import type { CSSProperties } from 'react'
import { AuthGate } from '../../components/AuthGate'
import { LogoutButton } from '../../components/LogoutButton'

// /me — 계정 허브(T-093, F-029). 주소창으로만 가던 진입점을 모은다(이력서 수정·즐겨찾기·지원기록·로그아웃).
// 서버 컴포넌트 셸 + AuthGate(client) 보호. 단일 중앙 컬럼(maxWidth 430, DESIGN §4).
const hubLink: CSSProperties = {
  display: 'block',
  padding: '14px 16px',
  borderRadius: '16px',
  border: '1px solid var(--line)',
  background: 'var(--surface)',
  color: 'var(--ink)',
  textDecoration: 'none',
  fontWeight: 600,
  boxShadow: 'var(--shadow-soft)',
}

export default function MyPage() {
  return (
    <AuthGate>
      <main style={{ maxWidth: '430px', margin: '0 auto', padding: '32px 16px 72px' }}>
        <h1
          style={{
            fontSize: '16px',
            fontWeight: 900,
            color: 'var(--ink)',
            letterSpacing: '-0.03em',
            marginBottom: '24px',
          }}
        >
          마이페이지
        </h1>
        <nav
          aria-label="계정 메뉴"
          style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}
        >
          <a href="/resume" data-testid="link-resume-edit" style={hubLink}>
            이력서 수정
          </a>
          <a href="/favorites" data-testid="link-favorites" style={hubLink}>
            즐겨찾기
          </a>
          <a href="/applications" data-testid="link-applications" style={hubLink}>
            지원 기록
          </a>
        </nav>
        <div style={{ marginTop: '20px' }}>
          <LogoutButton />
        </div>
      </main>
    </AuthGate>
  )
}
