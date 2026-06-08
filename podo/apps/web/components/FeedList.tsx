'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrivalList } from './ArrivalList'
import { type FeedItem, JobCard } from './JobCard'

interface FeedPage {
  items: FeedItem[]
  nextCursor: number | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// 단일 피드 — GET /api/v1/feed를 rank_position 커서로 무한 스크롤(중복제거 append).
// error/empty 상태를 일급으로 노출(REV-M2-UI-001 — 실패를 빈 목록으로 삼키지 않음).
// domain(직군 탭, T-067): 'all'/undefined면 전체, 그 외는 ?domain=으로 role_family 필터.
export function FeedList({ domain }: { domain?: string }) {
  const [items, setItems] = useState<FeedItem[]>([])
  const [cursor, setCursor] = useState<number | null>(-1) // 렌더용. -1=첫 페이지, null=끝
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false) // 첫 로드 완료 — empty 판별용
  const [error, setError] = useState(false)
  const cursorRef = useRef<number | null>(-1)
  const loadingRef = useRef(false)
  const domainRef = useRef<string | undefined>(domain) // loadMore stable 유지용

  // cursorRef·domainRef로 stable(deps []) — useEffect([loadMore])가 1회만 실행.
  const loadMore = useCallback(async () => {
    if (cursorRef.current === null || loadingRef.current) return
    loadingRef.current = true
    setLoading(true)
    setError(false)
    try {
      const d = domainRef.current
      const domainParam = d && d !== 'all' ? `&domain=${encodeURIComponent(d)}` : ''
      // credentials:'include' — 보호 라우트(SessionGuard) 쿠키 전송(교차출처 :3000→:3001).
      const res = await fetch(`${API_BASE}/api/v1/feed?cursor=${cursorRef.current}${domainParam}`, {
        credentials: 'include',
      })
      if (!res.ok) throw new Error(`feed ${res.status}`)
      const page = (await res.json()) as FeedPage
      setItems((prev) => {
        const seen = new Set(prev.map((i) => i.posting.id))
        const fresh = page.items.filter((i) => !seen.has(i.posting.id)) // 중복제거
        return [...prev, ...fresh]
      })
      cursorRef.current = page.nextCursor
      setCursor(page.nextCursor)
      setLoaded(true)
    } catch {
      setError(true) // 실패를 삼키지 않음(REV-M2-UI-001)
    } finally {
      loadingRef.current = false
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadMore()
  }, [loadMore])

  // T-067: domain(직군 탭) 변경 → 피드 리셋 + 재요청. 첫 렌더는 위 effect가 담당(중복 fetch 방지).
  const firstRender = useRef(true)
  useEffect(() => {
    domainRef.current = domain
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    setItems([])
    cursorRef.current = -1
    setCursor(-1)
    setLoaded(false)
    void loadMore()
  }, [domain, loadMore])

  return (
    <main style={{ maxWidth: '430px', margin: '0 auto', padding: '4px 16px 72px' }}>
      {/* 신규 공고 arrival 모션(stagger) + reduced-motion 분기는 ArrivalList가 담당(T-048). */}
      <ArrivalList
        items={items}
        keyOf={(item) => `${item.rank_position}-${item.posting.id}`}
        renderItem={(item) => (
          <JobCard
            item={item}
            // 지원/스킵 처리완료 → 피드에서 정리(F-019), 실패 시 롤백 복원.
            onProcessed={(jobId) => setItems((prev) => prev.filter((i) => i.posting.id !== jobId))}
            onRestore={() => void 0}
          />
        )}
      />

      {error ? (
        <div
          data-testid="feed-error"
          className="mt-4 text-sm"
          style={{ color: 'var(--band-1-ink)' }}
        >
          ⚠ 피드를 불러오지 못했습니다.{' '}
          <button type="button" onClick={() => void loadMore()} className="underline">
            다시 시도
          </button>
        </div>
      ) : loaded && items.length === 0 ? (
        <p data-testid="feed-empty" className="mt-4 text-sm" style={{ color: 'var(--faint)' }}>
          표시할 공고가 없습니다.
        </p>
      ) : cursor !== null ? (
        <button
          type="button"
          onClick={() => void loadMore()}
          disabled={loading}
          className="mt-4 w-full rounded-xl border py-2"
        >
          {loading ? '불러오는 중…' : '더 보기'}
        </button>
      ) : null}
    </main>
  )
}
