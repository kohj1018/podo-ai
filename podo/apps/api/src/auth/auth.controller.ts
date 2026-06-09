import {
  Body,
  Controller,
  ForbiddenException,
  Get,
  Post,
  Req,
  Res,
  UseGuards,
} from '@nestjs/common'
import { AuthGuard } from '@nestjs/passport'
import { SessionGuard } from './session.guard'

// express 의존 타입 회피 — 컨트롤러가 실제로 쓰는 최소 표면만 선언(feed.spec 패턴 정합).
interface SessionRequest {
  login(user: { id: string }, done: (err?: unknown) => void): void
  logout(done: (err?: unknown) => void): void
}
interface AuthedRequest {
  user?: { id: string }
}
interface JsonResponse {
  status(code: number): { json(body: unknown): void }
  redirect(url: string): void
}

// OAuth 콜백 후 돌아갈 web(Vercel) 도메인 = CORS 허용 origin과 동일 값(단일 var, T-087).
// 프로덕션은 main.ts 부트스트랩이 CORS_ALLOWED_ORIGIN 미설정 시 기동 실패시키므로 여기선 set 보장.
const webRedirectOrigin = (): string => process.env.CORS_ALLOWED_ORIGIN ?? 'http://localhost:3000'

@Controller('auth')
export class AuthController {
  // GitHub OAuth 시작 — AuthGuard가 provider로 redirect(핸들러 본문 도달 안 함).
  @Get('github')
  @UseGuards(AuthGuard('github'))
  githubLogin(): void {}

  // 콜백 — AuthGuard가 전략 validate→세션 직렬화 후, 웹 피드로 redirect.
  @Get('github/callback')
  @UseGuards(AuthGuard('github'))
  githubCallback(@Res() res: JsonResponse): void {
    res.redirect(webRedirectOrigin())
  }

  @Get('google')
  @UseGuards(AuthGuard('google'))
  googleLogin(): void {}

  @Get('google/callback')
  @UseGuards(AuthGuard('google'))
  googleCallback(@Res() res: JsonResponse): void {
    res.redirect(webRedirectOrigin())
  }

  // 현재 세션 인증 상태 — web 클라이언트 가드(AuthGate)용. web(Vercel)↔api 교차 도메인이라
  // SSR이 api 세션 쿠키를 못 봐서, 브라우저가 credentials:'include'로 직접 질의한다.
  // 인증 시 200 { data: { userId } }; 비인증은 SessionGuard가 401(UNAUTHENTICATED).
  @Get('me')
  @UseGuards(SessionGuard)
  me(@Req() req: AuthedRequest): { data: { userId: string } } {
    return { data: { userId: req.user?.id ?? '' } }
  }

  // 로그아웃 — 세션 무효화.
  @Post('logout')
  logout(@Req() req: SessionRequest, @Res() res: JsonResponse): void {
    req.logout(() => {
      res.status(200).json({ data: { ok: true } })
    })
  }

  // 테스트 인증 우회 — NODE_ENV=test 에서만 활성. 프로덕션 빌드 비활성(403).
  // body { userId } 로 세션을 시드 발급(무키 E2E/CI — 실 OAuth redirect 없이 로그인 상태 진입).
  @Post('test-session')
  testSession(
    @Body() body: { userId: string },
    @Req() req: SessionRequest,
    @Res() res: JsonResponse,
  ): void {
    if (process.env.NODE_ENV !== 'test') {
      throw new ForbiddenException({
        code: 'TEST_SESSION_DISABLED',
        message: '테스트 세션 우회는 비활성화되어 있습니다.',
      })
    }
    req.login({ id: body.userId }, (err) => {
      if (err) {
        res.status(500).json({ error: { code: 'SESSION_ERROR', message: '세션 발급 실패.' } })
        return
      }
      res.status(200).json({ data: { userId: body.userId } })
    })
  }
}
