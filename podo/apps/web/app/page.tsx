'use client'

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
  resume_domains?: ResumeDomains | null
}

// 피드 진입 — CoveragePanel 상시(Fail #3) + 직군 분리 탭(T-067, 자동 분류 결과 기반) + FeedView(F-018).
export default function HomePage() {
  const [domains, setDomains] = useState<string[]>([])
  const [confidence, setConfidence] = useState<string | undefined>(undefined)
  const [active, setActive] = useState('all')

  useEffect(() => {
    let alive = true
    // T-066 영속·T-067 서빙한 resume_domains를 read-only 소비(계약 생산 X).
    fetch(`${API_BASE}/api/v1/feed/meta`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((m: FeedMeta | null) => {
        if (!alive || !m?.resume_domains) {
          return
        }
        const rd = m.resume_domains
        setDomains([...(rd.primary_domains ?? []), ...(rd.secondary_domains ?? [])])
        setConfidence(rd.confidence)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  return (
    <AuthGate>
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
    </AuthGate>
  )
}
