'use client'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// 로그아웃 — api 세션 무효화 후 /login으로. credentials:'include'로 세션 쿠키 전송(T-042 CORS).
export function LogoutButton() {
  async function logout() {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
    window.location.assign('/login')
  }

  return (
    <button
      type="button"
      aria-label="로그아웃"
      onClick={() => void logout()}
      style={{
        background: 'transparent',
        color: 'var(--muted)',
        border: '1px solid var(--line-strong)',
        borderRadius: '12px',
        padding: '6px 12px',
        cursor: 'pointer',
      }}
    >
      로그아웃
    </button>
  )
}
