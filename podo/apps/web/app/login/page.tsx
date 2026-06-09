import { LoginButtons } from '../../components/LoginButtons'
import { RedirectIfAuthed } from '../../components/RedirectIfAuthed'

// /login — 비로그인 진입점. 이미 로그인 상태면 RedirectIfAuthed(client)가 피드로 보냄.
// 교차 도메인이라 SSR 쿠키로는 로그인 여부를 못 봐서 판별은 client에서 한다(SessionProvider).
// 포도 동반자 톤 + DESIGN §2 토큰. OAuth 실패 시 ?error= 로 재시도 안내(LoginButtons).
// Next 15: searchParams는 async — await 필수(T-089 dep bump).
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>
}) {
  const { error } = await searchParams
  return (
    <main style={{ maxWidth: '430px', margin: '0 auto', padding: '48px 24px' }}>
      <RedirectIfAuthed />
      <h1 style={{ color: 'var(--ink)', marginBottom: '8px' }}>포도와 함께 시작해요</h1>
      <p style={{ color: 'var(--muted)', marginBottom: '32px' }}>오늘의 맞춤 공고를 골라드릴게요</p>
      <LoginButtons error={error} />
    </main>
  )
}
