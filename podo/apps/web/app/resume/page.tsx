import { ResumeUpload } from '../../components/ResumeUpload'

// /resume — 서버 컴포넌트 셸 + 클라이언트 업로드 위임(ResumeUpload 'use client').
export default function ResumePage() {
  return (
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
        이력서 업로드
      </h1>
      <ResumeUpload />
    </main>
  )
}
