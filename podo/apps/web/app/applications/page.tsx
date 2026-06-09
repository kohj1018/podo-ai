import { ActivityList } from '../../components/ActivityList'
import { AuthGate } from '../../components/AuthGate'

// /applications — 지원 기록 뷰(T-094, F-029). persona pain(수기 스프레드시트) 대체. AuthGate 보호.
export default function ApplicationsPage() {
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
          지원 기록
        </h1>
        <ActivityList filter="applied" />
      </main>
    </AuthGate>
  )
}
