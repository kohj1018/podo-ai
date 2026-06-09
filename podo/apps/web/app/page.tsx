'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { AuthGate } from '../components/AuthGate'
import { CoarseSection } from '../components/CoarseSection'
import { CoveragePanel } from '../components/CoveragePanel'
import { DomainTabBar } from '../components/DomainTabBar'
import { FeedView } from '../components/FeedView'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

interface ResumeDomains {
  primary_domains: string[]
  secondary_domains: string[]
  confidence: string
}

interface FeedMeta {
  has_resume?: boolean
  resume_domains?: ResumeDomains | null
}

// 피드 진입 — CoveragePanel 상시(Fail #3) + 직군 분리 탭(T-067, 자동 분류 결과 기반) + FeedView(F-018).
// 신규 사용자(이력서 없음)는 인라인 온보딩 대신 /resume로 직행(T-097, §2-B). 교차도메인이라 client 가드.
export default function HomePage() {
  const router = useRouter()
  const [domains, setDomains] = useState<string[]>([])
  const [confidence, setConfidence] = useState<string | undefined>(undefined)
  const [active, setActive] = useState('all')
  const [redirecting, setRedirecting] = useState(false)
  const [ready, setReady] = useState(false) // meta 로드 완료 — 결정 전 피드 깜빡임 차단(T-102)

  useEffect(() => {
    let alive = true
    // T-066 영속·T-067 서빙한 resume_domains를 read-only 소비(계약 생산 X).
    fetch(`${API_BASE}/api/v1/feed/meta`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((m: FeedMeta | null) => {
        if (!alive) {
          return
        }
        // 이력서 없음 → /resume 직행(인라인 온보딩 동선 약함). /resume엔 본 판정 없음 → 루프 방지.
        // has_resume 결정 전까지 ready=false로 피드를 그리지 않음(신규 사용자 깜빡임 제거, T-102).
        if (m?.has_resume === false) {
          setRedirecting(true)
          router.replace('/resume')
          return
        }
        if (m?.resume_domains) {
          const rd = m.resume_domains
          setDomains([...(rd.primary_domains ?? []), ...(rd.secondary_domains ?? [])])
          setConfidence(rd.confidence)
        }
        setReady(true)
      })
      .catch(() => {
        if (alive) setReady(true) // meta 실패 시 피드로 진입(FeedView가 자체 에러 처리)
      })
    return () => {
      alive = false
    }
  }, [router])

  return (
    <AuthGate>
      {redirecting ? (
        // 리다이렉트 진행 중 placeholder — 피드 깜빡임 최소(T-097 AC-1).
        <output
          aria-live="polite"
          data-testid="resume-redirect"
          style={{
            display: 'block',
            maxWidth: '430px',
            margin: '0 auto',
            padding: '48px 24px',
            color: 'var(--muted)',
          }}
        >
          이력서를 작성하러 갈게요…
        </output>
      ) : !ready ? (
        // meta 로드 전 — has_resume 결정 전이라 피드 대신 skeleton(신규 사용자 피드 깜빡임 제거, T-102).
        <output
          aria-live="polite"
          aria-busy="true"
          aria-label="불러오는 중"
          data-testid="feed-gate-loading"
          style={{ display: 'block', maxWidth: '430px', margin: '0 auto', padding: '24px 16px' }}
        >
          <div
            className="shimmer"
            style={{ height: '64px', borderRadius: '16px', marginBottom: '12px' }}
          />
          <div className="shimmer" style={{ height: '88px', borderRadius: '16px' }} />
        </output>
      ) : (
        <div className="flex flex-col gap-4 py-4">
          <CoveragePanel />
          {domains.length > 0 ? (
            <DomainTabBar
              domains={domains}
              active={active}
              onChange={setActive}
              confidence={confidence}
            />
          ) : null}
          <FeedView domain={active} />
          {/* 피드 최하단 보조 진입(접힘) — deep 분석 전 공고(T-091, IA §2-A-1 ⑥). coarse 0이면 미렌더. */}
          <CoarseSection />
        </div>
      )}
    </AuthGate>
  )
}
