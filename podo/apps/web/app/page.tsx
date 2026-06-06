import { CoveragePanel } from '../components/CoveragePanel'
import { FeedList } from '../components/FeedList'

export default function HomePage() {
  return (
    <div className="flex flex-col gap-4 py-4">
      <CoveragePanel />
      <FeedList />
    </div>
  )
}
