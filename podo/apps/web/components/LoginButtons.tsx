'use client'

import { useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// GitHub/Google OAuth 시작 버튼 — NestJS api(/auth/:provider)로 이동(T-042 전략이 redirect).
// error prop(서버에서 searchParams로 주입)이 있으면 친절한 재시도 안내(가짜 진입 금지).
// DESIGN §2 토큰만(raw hex 금지) — ResumeUpload의 inline 토큰 버튼 패턴 정합(Button primitive 미존재).
export function LoginButtons({ error }: { error?: string }) {
  const [loading, setLoading] = useState<string | null>(null)

  function start(provider: 'github' | 'google') {
    setLoading(provider)
    window.location.assign(`${API_BASE}/auth/${provider}`)
  }

  return (
    <div>
      {error && (
        <p
          role="alert"
          data-testid="login-error"
          style={{ color: 'var(--band-1-ink)', margin: '0 0 12px' }}
        >
          로그인에 실패했어요. 다시 시도해주세요.
        </p>
      )}
      <button
        type="button"
        aria-label="GitHub으로 시작"
        disabled={loading !== null}
        onClick={() => start('github')}
        style={{
          display: 'block',
          width: '100%',
          marginBottom: '10px',
          padding: '12px',
          background: 'var(--grape-600)',
          color: 'var(--surface)',
          borderRadius: '16px',
          border: 'none',
          cursor: loading ? 'wait' : 'pointer',
        }}
      >
        {loading === 'github' ? '이동 중…' : 'GitHub으로 시작'}
      </button>
      <button
        type="button"
        aria-label="Google로 시작"
        disabled={loading !== null}
        onClick={() => start('google')}
        style={{
          display: 'block',
          width: '100%',
          padding: '12px',
          background: 'var(--surface)',
          color: 'var(--ink)',
          borderRadius: '16px',
          border: '1px solid var(--line-strong)',
          cursor: loading ? 'wait' : 'pointer',
        }}
      >
        {loading === 'google' ? '이동 중…' : 'Google로 시작'}
      </button>
    </div>
  )
}
