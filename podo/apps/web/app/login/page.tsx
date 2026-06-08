import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { LoginButtons } from '../../components/LoginButtons'

// /login — 비로그인 진입점. 세션 쿠키 있으면 피드로(이미 로그인), 없으면 provider 버튼.
// 포도 동반자 톤 + DESIGN §2 토큰. OAuth 실패 시 ?error= 로 재시도 안내(LoginButtons).
// Next 15: cookies()·searchParams는 async — await 필수(T-089 dep bump).
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>
}) {
  if ((await cookies()).has('connect.sid')) {
    redirect('/')
  }
  const { error } = await searchParams
  return (
    <main style={{ maxWidth: '430px', margin: '0 auto', padding: '48px 24px' }}>
      <h1 style={{ color: 'var(--ink)', marginBottom: '8px' }}>포도와 함께 시작해요</h1>
      <p style={{ color: 'var(--muted)', marginBottom: '32px' }}>오늘의 맞춤 공고를 골라드릴게요</p>
      <LoginButtons error={error} />
    </main>
  )
}
