// PendingState (DESIGN §7-2) — held(LLM miss) 공고. 가짜 점수 대신 정직한 보류 + 원문 링크.
// dashed 카드 + 포도 + "틀린 점수보다 정직"(원칙 4 / GS-2). 숫자 점수/밴드 절대 없음. raw hex 0.
import { PodoMascot } from './PodoMascot'

export function PendingState({ url }: { url?: string }) {
  return (
    <div
      data-testid="pending-state"
      className="rounded-2xl p-4"
      style={{ border: '1px dashed var(--line-strong)', color: 'var(--ink)' }}
    >
      <PodoMascot size={28} />{' '}
      <span style={{ color: 'var(--faint)' }}>포도가 아직 이 공고를 분석하지 못했어요</span>
      {url ? (
        <p className="mt-1 text-sm">
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--grape-700)' }}
          >
            원문 보기
          </a>
        </p>
      ) : null}
    </div>
  )
}
