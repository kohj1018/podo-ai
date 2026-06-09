import { vi } from 'vitest'

// dotLottie 플레이어는 canvas/WASM 의존 → jsdom에서 로드 불가(WASM init 실패가 unhandled error로 누수).
// T-099가 GreetingCard에 src를 연결해 모션 경로를 켜면서 GreetingCard 렌더 테스트 전반이 영향받으므로
// 테스트 환경에서는 dotLottie를 경량 스텁으로 대체한다. 실 모션 재생은 브라우저/e2e에서 검증.
vi.mock('@lottiefiles/dotlottie-react', () => ({
  DotLottieReact: () => null,
}))
