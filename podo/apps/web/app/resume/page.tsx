import { AuthGate } from '../../components/AuthGate'
import { ResumeUpload } from '../../components/ResumeUpload'

// /resume — 서버 컴포넌트 셸 + 클라이언트 업로드 위임(ResumeUpload 'use client').
// AuthGate(client)로 보호 — 비로그인 진입 시 /login(SSR 미들웨어 대체).
export default function ResumePage() {
  return (
    <AuthGate>
      <main
        style={{
          maxWidth: '430px',
          margin: '0 auto',
          padding: '32px 16px 72px',
        }}
      >
        <h1
          style={{
            fontSize: '16px',
            fontWeight: 900,
            color: 'var(--ink)',
            letterSpacing: '-0.03em',
            marginBottom: '24px',
          }}
        >
          이력서 작성
        </h1>
        <ResumeUpload />
      </main>
    </AuthGate>
  )
}
