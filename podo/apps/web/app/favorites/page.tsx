import { ActivityList } from '../../components/ActivityList'
import { AuthGate } from '../../components/AuthGate'

// /favorites — 즐겨찾기 목록 뷰(T-094, F-029). AuthGate 보호 + 단일 컬럼.
export default function FavoritesPage() {
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
          즐겨찾기
        </h1>
        <ActivityList filter="favorite" />
      </main>
    </AuthGate>
  )
}
