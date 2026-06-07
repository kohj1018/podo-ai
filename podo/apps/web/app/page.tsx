import { CoveragePanel } from '../components/CoveragePanel'
import { FeedView } from '../components/FeedView'

// 피드 진입 — 8-상태 분기는 FeedView(F-018). CoveragePanel은 상시 노출(Fail #3 차단).
export default function HomePage() {
  return (
    <div className="flex flex-col gap-4 py-4">
      <CoveragePanel />
      <FeedView />
    </div>
  )
}
