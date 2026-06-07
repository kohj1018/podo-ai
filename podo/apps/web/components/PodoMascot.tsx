// PodoMascot — 포도 ai 마스코트 정적 이미지(/podo-mascot.png, public). 동반자 정체성의 얼굴.
// 기본은 장식(alt="" → 접근성 트리 제외). 의미 전달 시 alt 지정.
export function PodoMascot({ size = 48, alt = '' }: { size?: number; alt?: string }) {
  return (
    <img
      src="/podo-mascot.png"
      alt={alt}
      width={size}
      height={size}
      data-testid="podo-mascot"
      style={{
        display: 'block',
        width: `${size}px`,
        height: `${size}px`,
        objectFit: 'contain',
        flexShrink: 0,
      }}
    />
  )
}
